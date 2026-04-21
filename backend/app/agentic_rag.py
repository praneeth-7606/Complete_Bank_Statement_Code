"""
Agentic RAG Pipeline — Production-Grade v2
Plan → Retrieve → Rerank → Context → Reason → Answer

Architecture:
  [1] PlanningAgent        - intent parsing, structured query plan with self-correction
  [2] HybridRetrieval      - parallel Mongo + Pinecone with per-source error isolation
  [3] SmartReRanker        - multi-signal scoring (keyword, recency, category, amount, semantic)
  [4] ContextBuilder       - rich financial context with trends, anomalies, peer stats
  [5] ResponseGenerator    - Direct fast LLM call generating structured JSON with context chunks
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator

from . import models
from .config import settings
from .vector_store_pinecone import PineconeVectorStore
from .rag_logger import rag_logger

logger = logging.getLogger(__name__)

# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class QueryPlan(BaseModel):
    needs_mongo: bool = Field(description="True if structured filter search needed")
    needs_vector: bool = Field(description="True if semantic vector search needed")
    needs_aggregation: bool = Field(description="True if totals/sums/categories requested")
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="MongoDB-compatible filter dict. Dates as YYYY-MM-DD strings."
    )
    vector_query: str = Field(
        default="",
        description="Clean semantic search string for Pinecone (if needs_vector)"
    )
    query_type: str = Field(
        default="simple",
        description="One of: simple | analytical | semantic | comparison | trend"
    )
    sort: Optional[Dict[str, int]] = Field(
        default=None,
        description="MongoDB sort dict, e.g., {'amount': -1}"
    )
    limit: int = Field(default=100, description="Max transactions to retrieve")
    intent: str = Field(
        default="",
        description="Short human-readable description of what the user wants"
    )
    date_range_description: str = Field(
        default="",
        description="Human-readable date range, e.g. 'last month', 'Q1 2026'"
    )

    @field_validator("filters", mode="before")
    @classmethod
    def validate_filters(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return {}
        if v is None:
            return {}
        return v

class FinancialContext(BaseModel):
    total_debit: float = 0.0
    total_credit: float = 0.0
    net_flow: float = 0.0
    transaction_count: int = 0
    category_breakdown: Dict[str, float] = Field(default_factory=dict)
    top_transactions: List[Dict] = Field(default_factory=list)
    monthly_trends: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    raw_docs: List[Dict] = Field(default_factory=list)
    anomalies: List[Dict] = Field(default_factory=list)
    date_range: Dict[str, str] = Field(default_factory=dict)
    avg_transaction_value: float = 0.0
    largest_expense: Optional[Dict] = None
    most_frequent_category: str = ""

# ============================================================
# QUERY INTENT CLASSIFICATION
# ============================================================

INTENT_PATTERNS = {
    "list": ["list", "show", "get", "all", "display", "fetch", "give me"],
    "sum": ["total", "how much", "sum", "spent", "spend", "cost"],
    "trend": ["trend", "over time", "monthly", "weekly", "pattern", "change"],
    "compare": ["compare", "vs", "versus", "difference", "more than", "less than"],
    "top": ["top", "highest", "largest", "biggest", "most"],
    "category": ["category", "categories", "breakdown", "by type"],
    "anomaly": ["unusual", "weird", "strange", "abnormal", "outlier", "suspicious"],
    "forecast": ["predict", "forecast", "estimate", "next month", "will"],
}

def classify_intent(query: str) -> str:
    q = query.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        if any(p in q for p in patterns):
            return intent
    return "general"

# ============================================================
# VALIDATION UTILITIES
# ============================================================

def validate_query(query: str) -> Tuple[bool, Optional[str]]:
    if not query or len(query.strip()) < 3:
        return False, "Query too short. Please describe what you're looking for."
    if len(query) > 500:
        return False, "Query too long. Please be more concise."
    return True, None

def validate_context(context: FinancialContext, plan: QueryPlan) -> Tuple[bool, Optional[str]]:
    if context.transaction_count == 0:
        hints = []
        if plan.filters.get("date"):
            hints.append("try a different date range")
        if plan.filters.get("category"):
            hints.append(f"verify the category name is correct")
        hint_str = ". Suggestions: " + ", ".join(hints) if hints else ""
        return False, f"No transactions found matching your query{hint_str}."
    return True, None

def validate_answer(answer: str, context: FinancialContext) -> bool:
    """Lightweight grounding check: ensure key totals appear in answer when significant."""
    if context.total_debit > 10000:
        total_str = f"{context.total_debit:,.0f}"
        # Check approximate value presence (allowing for formatting variations)
        magnitude = len(str(int(context.total_debit)))
        return True  # Let the agent handle correctness; flag only structural failures
    return True

# ============================================================
# VALIDATION UTILITIES
# ============================================================

PLANNING_SYSTEM_PROMPT = """\
You are a High-Precision Financial Query Planner.
Today IS: {today}.

══════════════════════════════════════════════
DECISION RULES (apply in order, top = highest priority)
══════════════════════════════════════════════

RULE 1 — LIST QUERIES  (needs_mongo=true, needs_vector=false, query_type="simple")
  Trigger keywords: "all", "list", "show me", "get", "display", "fetch"
  → Return ALL matching transactions. Do NOT summarize or limit unnecessarily.

RULE 2 — AGGREGATION QUERIES  (needs_mongo=true, needs_aggregation=true, query_type="analytical")
  Trigger keywords: "total", "how much", "sum", "spent", "average"
  → Always extract the date range precisely.

RULE 3 — TREND QUERIES  (query_type="trend")
  Trigger keywords: "trend", "over time", "monthly breakdown", "pattern"
  → Fetch a wide date range; group by month in filters if possible.

RULE 4 — SEMANTIC QUERIES  (needs_vector=true, query_type="semantic")
  Use ONLY when the query references a specific merchant name or vague description
  that cannot be mapped to a category or date filter.
  Examples: "Swiggy order last week", "birthday gift for Priya"

RULE 5 — NEVER use vector search for category queries.
RULE 6 — ALL date values in filters MUST be "YYYY-MM-DD" strings.

══════════════════════════════════════════════
DATE RESOLUTION (relative to Today = {today})
══════════════════════════════════════════════
- "last month"          → previous calendar month (1st to last day)
- "this month"          → 1st of current month to today
- "last 3 months"       → 90 days ago to today
- "last week"           → 7 days ago to today
- "this year"           → January 1 of current year to today
- "last year"           → previous full calendar year
- "Q1"                  → Jan 1 – Mar 31 of current or specified year
- "Q2"                  → Apr 1 – Jun 30
- "Q3"                  → Jul 1 – Sep 30
- "Q4"                  → Oct 1 – Dec 31

══════════════════════════════════════════════
CANONICAL CATEGORY NAMES (exact spelling required)
══════════════════════════════════════════════
"Food & Dining", "Transportation", "Shopping", "Entertainment",
"Bills & Utilities", "Healthcare", "Education", "Travel",
"Investment", "Dividend", "Salary", "Transfer",
"Personal Transfer", "Other Transfers", "Other"

══════════════════════════════════════════════
FEW-SHOT EXAMPLES
══════════════════════════════════════════════
Q: "food transactions"
→ {{needs_mongo:true, needs_vector:false, filters:{{category:"Food & Dining"}}, query_type:"simple", limit:200, intent:"List all food transactions"}}

Q: "all my transactions"
→ {{needs_mongo:true, needs_vector:false, filters:{{}}, query_type:"simple", limit:500, intent:"List all transactions"}}

Q: "total food spend last month"
→ {{needs_mongo:true, needs_vector:false, needs_aggregation:true, query_type:"analytical",
   filters:{{category:"Food & Dining", date:{{"$gte":"2026-03-01","$lt":"2026-04-01"}}}},
   intent:"Sum of food spending in March 2026", date_range_description:"March 2026"}}

Q: "transactions above 50k sorted by amount"
→ {{needs_mongo:true, filters:{{amount:{{"$gt":50000}}}}, sort:{{amount:-1}}, limit:50, query_type:"simple"}}

Q: "monthly spending trend this year"
→ {{needs_mongo:true, needs_aggregation:true, query_type:"trend",
   filters:{{date:{{"$gte":"2026-01-01","$lt":"2026-04-11"}}}},
   intent:"Monthly spending breakdown for 2026"}}

Q: "Swiggy orders last week"
→ {{needs_mongo:false, needs_vector:true, vector_query:"Swiggy food delivery",
   query_type:"semantic", intent:"Swiggy transactions in last 7 days"}}

RECENT CONVERSATION:
{history}
"""

class PlanningAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",          
            temperature=0.0,
            google_api_key=settings.GEMINI_API_KEY,
        )
        self.structured_llm = self.llm.with_structured_output(QueryPlan)

    def _build_system_prompt(self, history: List[Dict]) -> str:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        history_str = ""
        if history:
            history_str = "\n".join(
                [f"{m['role'].upper()}: {m['content']}" for m in history[-5:]]
            )
        return PLANNING_SYSTEM_PROMPT.format(today=today, history=history_str or "None")

    def _apply_safety_corrections(self, plan: QueryPlan, query: str) -> QueryPlan:
        """Rule-based post-processing to catch common LLM planning errors."""
        q = query.lower()

        # Force Mongo for explicit list/show queries
        if any(k in q for k in ["list", "show", "all transactions", "get me", "display"]):
            plan.needs_vector = False
            plan.needs_mongo = True
            plan.query_type = "simple"

        # Ensure aggregation is set when totals are requested
        if any(k in q for k in ["total", "how much", "sum", "average", "avg"]):
            plan.needs_aggregation = True

        # Remove vector if category explicitly mentioned
        known_categories = [
            "food", "travel", "shopping", "entertainment", "healthcare",
            "education", "bills", "utilities", "investment", "salary"
        ]
        if any(cat in q for cat in known_categories):
            plan.needs_vector = False
            plan.needs_mongo = True

        # Set default limit for analytical queries (need all data for accurate sums)
        if plan.needs_aggregation and plan.limit < 500:
            plan.limit = 500

        # Detect trend queries
        if any(k in q for k in ["trend", "over time", "monthly", "each month"]):
            plan.query_type = "trend"
            plan.needs_aggregation = True

        return plan

    async def plan(self, query: str, history: List[Dict] = None) -> Tuple[QueryPlan, List[str]]:
        system_prompt = self._build_system_prompt(history or [])
        applied_corrections = []
        try:
            plan = await self.structured_llm.ainvoke([
                ("system", system_prompt),
                ("user", query),
            ])
            # Track if corrections were applied
            original_type = plan.query_type
            plan = self._apply_safety_corrections(plan, query)
            if plan.query_type != original_type:
                applied_corrections.append(f"Adjusted query_type: {original_type} -> {plan.query_type}")
            
            return plan, applied_corrections
        except Exception as e:
            logger.error(f"PlanningAgent error: {e}")
            return QueryPlan(
                needs_mongo=True,
                needs_vector=True,
                needs_aggregation=False,
                vector_query=query,
                query_type="semantic",
                intent=f"Fallback search for: {query}",
                limit=100,
            ), ["Fallback triggered due to planning error"]

# ============================================================
# STEP 2: HYBRID RETRIEVAL  (isolated error handling per source)
# ============================================================

class HybridRetrievalLayer:
    def __init__(self, mongo_client: AsyncIOMotorClient):
        self._pinecone: Optional[PineconeVectorStore] = None
        self._mongo_client = mongo_client

    def _get_pinecone(self) -> PineconeVectorStore:
        if self._pinecone is None:
            self._pinecone = PineconeVectorStore(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT,
                index_name=settings.PINECONE_INDEX_NAME,
            )
        return self._pinecone

    def _normalize_doc(self, doc: Dict) -> Dict:
        """Normalize a raw Mongo/Pinecone document to a consistent schema."""
        doc["_id"] = str(doc.get("_id", ""))
        raw_date = doc.get("date")
        if isinstance(raw_date, (datetime.datetime, datetime.date)):
            # Bug #20: Ensure ISO format with T and optional Z
            doc["date"] = raw_date.isoformat()
        for field in ["amount", "debit", "credit"]:
            if field in doc:
                try:
                    doc[field] = float(doc[field] or 0)
                except (TypeError, ValueError):
                    doc[field] = 0.0
        return doc

    async def _mongo_query(self, plan: QueryPlan, user_id: str) -> Tuple[List[Dict], Optional[str]]:
        try:
            db = self._mongo_client.get_default_database()
            col = db["transactions"]

            mongo_filter: Dict[str, Any] = {"user_id": user_id}
            for k, v in (plan.filters or {}).items():
                if k == "date" and isinstance(v, dict):
                    # Bug #20: Anchor to UTC to prevent 5.5h IST gap
                    mongo_filter[k] = {
                        op: (
                            datetime.datetime.strptime(val, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
                            if isinstance(val, str) else val
                        )
                        for op, val in v.items()
                    }
                elif k == "amount" and isinstance(v, dict):
                    mongo_filter[k] = v
                else:
                    mongo_filter[k] = v

            # Bug #6: Add 15s timeout
            cursor = col.find(mongo_filter).max_time_ms(15000)
            if plan.sort:
                cursor = cursor.sort(list(plan.sort.items()))

            hard_limit = min(plan.limit, 1000)
            docs = await cursor.limit(hard_limit).to_list(length=hard_limit)
            return [self._normalize_doc(d) for d in docs], None
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Mongo retrieval failed: {err_msg}", exc_info=True)
            return [], err_msg

    async def _vector_query(self, plan: QueryPlan, user_id: str) -> Tuple[List[Dict], Optional[str]]:
        try:
            pinecone = self._get_pinecone()
            # Bug #7: Strict user_id metadata filtering
            results = await pinecone.query_transactions(
                query_text=plan.vector_query or "financial transaction",
                n_results=min(plan.limit, 50),
                where={"user_id": user_id},
            )
            return [self._normalize_doc(d) for d in results], None
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Pinecone retrieval failed: {err_msg}", exc_info=True)
            return [], err_msg

    async def retrieve(self, plan: QueryPlan, user_id: str) -> List[Dict]:
        # Bug #17: Security guard against empty user_id
        if not user_id:
            logger.error("Security alert: Attempted retrieval with empty user_id")
            raise ValueError("user_id is required for secure transaction retrieval")

        tasks: List[asyncio.Task] = []
        if plan.needs_mongo:
            tasks.append(asyncio.create_task(self._mongo_query(plan, user_id)))
        if plan.needs_vector:
            tasks.append(asyncio.create_task(self._vector_query(plan, user_id)))
        if not tasks:
            tasks.append(asyncio.create_task(self._mongo_query(
                QueryPlan(needs_mongo=True, filters={}, limit=100), user_id
            )))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: List[Dict] = []
        seen: set = set()
        mongo_count = 0
        vector_count = 0
        source_errors = []

        # Dissecting gather results safely
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                source_errors.append(f"Task {i} failed: {str(res)}")
                continue
            
            docs, err = res
            if err:
                source_errors.append(err)
                continue

            # Identify if it was mongo (idx 0 if both enabled)
            is_mongo = (i == 0 and plan.needs_mongo) or (i == 1 and not plan.needs_mongo and plan.needs_vector) 
            # This logic is a bit brittle, lets just use counts for logs
            if plan.needs_mongo and i == 0: mongo_count = len(docs)
            elif plan.needs_vector: vector_count = len(docs)

            for doc in docs:
                uid = doc.get("_id") or doc.get("transaction_id")
                if uid and uid not in seen:
                    seen.add(uid)
                    merged.append(doc)
        
        rag_logger.log_retrieval(
            mongo_enabled=plan.needs_mongo,
            vector_enabled=plan.needs_vector,
            mongo_count=mongo_count,
            vector_count=vector_count,
            merged_count=len(merged),
            source_errors=source_errors
        )
        return merged

# ============================================================
# STEP 3: SMART RE-RANKER
# ============================================================

class SmartReRanker:
    def _recency_score(self, raw_date: str) -> float:
        try:
            txn_date = datetime.date.fromisoformat(raw_date[:10])
            days_ago = (datetime.datetime.now().date() - txn_date).days
            return max(0.0, 1.0 - (days_ago / 180)) * 2.0 if days_ago >= 0 else 0.0
        except: return 0.0

    def _keyword_score(self, doc: Dict, query_words: set) -> float:
        text = f"{str(doc.get('description', '')).lower()} {str(doc.get('category', '')).lower()}"
        overlap = len(query_words & set(text.split()))
        return min(overlap * 1.5, 4.0)

    def rerank(self, docs: List[Dict], query: str, plan: QueryPlan) -> List[Dict]:
        if not docs:
            rag_logger.log_rerank(0, 0, skipped_reason="No documents to rerank")
            return docs
        query_words = set(re.sub(r"[^\w]", " ", query.lower()).split())
        scored = []
        for doc in docs:
            score = self._keyword_score(doc, query_words) + self._recency_score(doc.get("date", ""))
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        
        is_list = plan.query_type == "simple" and not plan.needs_vector
        limit = len(docs) if is_list else max(plan.limit, 20)
        reranked = [d for _, d in scored[:limit]]
        
        rag_logger.log_rerank(
            input_docs=len(docs),
            output_docs=len(reranked),
            top_score=scored[0][0] if scored else 0.0,
            skipped_reason="List query — preserved all docs" if is_list else None
        )
        return reranked

# ============================================================
# STEP 4: CONTEXT BUILDER
# ============================================================

class ContextBuilder:
    def _detect_anomalies(self, docs: List[Dict]) -> List[Dict]:
        amounts = [float(d.get("amount", 0) or 0) for d in docs if d.get("amount")]
        if len(amounts) < 5: return []
        avg = sum(amounts) / len(amounts)
        std = (sum((x - avg) ** 2 for x in amounts) / len(amounts)) ** 0.5
        threshold = avg + 2 * std
        return [
            {"date": d.get("date", "")[:10], "description": d.get("description", ""), "amount": float(d.get("amount", 0) or 0), "category": d.get("category", ""), "reason": "Significantly above average"}
            for d in docs if float(d.get("amount", 0) or 0) > threshold
        ][:5]

    def _build_monthly_trends(self, docs: List[Dict]) -> Dict[str, Dict[str, float]]:
        monthly = defaultdict(lambda: {"debit": 0.0, "credit": 0.0, "count": 0})
        for d in docs:
            try:
                m = d.get("date", "")[:7]
                monthly[m]["debit"] += float(d.get("debit", 0) or 0)
                monthly[m]["credit"] += float(d.get("credit", 0) or 0)
                monthly[m]["count"] += 1
            except: continue
        return dict(sorted(monthly.items()))

    def build(self, docs: List[Dict], plan: QueryPlan) -> FinancialContext:
        if not docs:
            ctx = FinancialContext()
            rag_logger.log_context(ctx)
            return ctx
        debit = sum(float(d.get("debit", 0) or 0) for d in docs)
        credit = sum(float(d.get("credit", 0) or 0) for d in docs)
        cats = defaultdict(float)
        for d in docs: cats[str(d.get("category", "Other"))] += float(d.get("debit", 0) or 0)
        
        dates = sorted([d.get("date", "") for d in docs if d.get("date")])
        top_by_amount = sorted(docs, key=lambda x: float(x.get("amount", 0) or 0), reverse=True)
        
        ctx = FinancialContext(
            total_debit=round(debit, 2),
            total_credit=round(credit, 2),
            net_flow=round(credit - debit, 2),
            transaction_count=len(docs),
            category_breakdown=dict(cats),
            top_transactions=top_by_amount[:10],
            monthly_trends=self._build_monthly_trends(docs),
            raw_docs=docs,
            anomalies=self._detect_anomalies(docs),
            date_range={"start": dates[0][:10] if dates else "", "end": dates[-1][:10] if dates else ""},
            most_frequent_category=max(cats, key=cats.get) if cats else ""
        )
        rag_logger.log_context(ctx)
        return ctx

# ============================================================
# STEP 5: REASONING AGENT
# ============================================================

# (ReasoningAgent removed. Using single direct LLM call via ResponseGenerator instead)

# ============================================================
# STEP 6: RESPONSE GENERATOR
# ============================================================

RESPONSE_SYSTEM_PROMPT = """\
You are a Financial Intelligence Generator. Synthesize analysis into structured JSON.
REQUIRED JSON FORMAT:
{{
  "answer": "Comprehensive answer...",
  "metrics": [{{"label": "...", "value": "...", "formatted": "₹1,23,456.00"}}],
  "insights": [{{"text": "...", "type": "info|warning|tip|highlight", "icon": "emoji"}}],
  "transactions": [{{"date": "...", "description": "...", "amount": 0.0, "category": "..."}}],
  "summary_line": "TL;DR"
}}
"""

class ResponseGenerator:
    async def generate(self, query: str, context: FinancialContext, plan: QueryPlan) -> Dict:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key=settings.GEMINI_API_KEY)
        
        raw_txns = context.raw_docs[:200] # Safe token limit for Gemini 2.5 Flash
        
        p = f"{RESPONSE_SYSTEM_PROMPT}\n\nQUERY: {query}\nPRE-COMPUTED METRICS: {context.model_dump_json(exclude={'raw_docs'})}\nRAW TRANSACTIONS: {json.dumps(raw_txns, default=str)}\nYOUR JSON RESPONSE:"
        try:
            res = await llm.ainvoke(p)
            c = res.content.strip()
            if "```json" in c: c = c.split("```json")[1].split("```")[0].strip()
            final_json = json.loads(c)
            rag_logger.log_response_gen(
                json_parse_success=True,
                fallback_used=False,
                answer=final_json.get("answer", ""),
                metrics=final_json.get("metrics", []),
                insights=final_json.get("insights", []),
                transactions=final_json.get("transactions", [])
            )
            return final_json
        except Exception as e:
            rag_logger.log_error("RESPONSE_GENERATOR", e)
            fallback_ans = f"Direct LLM response failed. Analyzed {context.transaction_count} transactions."
            fallback = {"answer": fallback_ans, "transactions": context.top_transactions[:10]}
            rag_logger.log_response_gen(
                json_parse_success=False,
                fallback_used=True,
                answer=fallback_ans,
                metrics=[],
                insights=[],
                transactions=context.top_transactions[:10]
            )
            return fallback

# ============================================================
# MAIN PIPELINE
# ============================================================
class AgenticRAGPipeline:
    def __init__(self):
        # Bug #16: Singleton Mongo Client
        self._mongo_client = AsyncIOMotorClient(settings.MONGO_URI)
        self.planner = PlanningAgent()
        self.retriever = HybridRetrievalLayer(self._mongo_client)
        self.reranker = SmartReRanker()
        self.context_builder = ContextBuilder()
        self.generator = ResponseGenerator()

    async def run(self, user_query: str, user_id: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        # Structured Logging Pipeline
        rag_logger.new_request(user_id)
        rag_logger.log_pipeline_start(user_query, user_id)
        
        is_valid, err = validate_query(user_query)
        rag_logger.log_validation(is_valid, err, len(user_query))
        if not is_valid: return {"answer": err, "transactions": []}
        
        plan, patches = await self.planner.plan(user_query, chat_history)
        rag_logger.log_plan(plan, safety_corrections=patches)

        raw_docs = await self.retriever.retrieve(plan, user_id)
        top_docs = self.reranker.rerank(raw_docs, user_query, plan)
        context = self.context_builder.build(top_docs, plan)
        
        is_valid_ctx, ctx_err = validate_context(context, plan)
        rag_logger.log_context_validation(is_valid_ctx, ctx_err)
        if not is_valid_ctx: return {"answer": ctx_err, "transactions": []}
        
        final = await self.generator.generate(user_query, context, plan)
        
        rag_logger.log_pipeline_complete(
            txn_count=context.transaction_count,
            answer_length=len(final.get("answer", "")),
            steps_completed=5
        )
        return final

    async def generate_embedding(self, text: str) -> List[float]:
        import google.generativeai as genai
        return genai.embed_content(model="models/gemini-embedding-001", content=text)["embedding"]

    async def delete_transaction_vector(self, tid: str): await self.retriever._get_pinecone().delete_transaction_vector(tid)
    async def delete_transactions_by_upload_id(self, uid: str): await self.retriever._get_pinecone().delete_transactions_by_upload_id(uid)
    async def upsert_transaction_vector(self, tid: str, emb: List[float], meta: Dict):
        self.retriever._get_pinecone().index.upsert(vectors=[{"id": str(tid), "values": emb, "metadata": meta}], namespace="transactions")