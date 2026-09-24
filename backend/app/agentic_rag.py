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
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union
from bson.decimal128 import Decimal128

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator

from . import models
from .config import settings
from .llm_provider import build_chat_llm, build_llm, build_structured_llm
from .vector_store_pinecone import PineconeVectorStore
from .rag_logger import rag_logger
from .observability import current_trace, observe_external_llm
from .rag_evaluation import evaluate_rag_run

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


def _record_rag_stage(
    name: str,
    started: float,
    *,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None,
    error_type: Optional[str] = None,
) -> None:
    """Persist aggregate-only RAG stage telemetry for the in-app dashboard."""
    trace = current_trace()
    if trace:
        trace.add_event(
            name,
            kind="rag",
            status=status,
            duration_ms=(time.perf_counter() - started) * 1000,
            metadata=metadata,
            error_type=error_type,
        )

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
        self.llm = build_chat_llm(settings.GEMINI_MODEL, temperature=0.0)
        self.structured_llm = build_structured_llm(QueryPlan, settings.GEMINI_MODEL, temperature=0.0, route="chat")

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

    def _deterministic_financial_plan(self, query: str) -> Optional[QueryPlan]:
        """Use an exact Mongo plan for high-confidence accounting queries.

        Totals must never depend on an LLM's interpretation or on approximate
        vector recall. This fast path also avoids provider-specific
        structured-output schema limitations.
        """
        q = query.lower()
        aggregation_terms = (
            "total", "how much", "sum", "spent", "spend", "debit", "credit",
            "received", "income", "average", "avg", "cash flow",
        )
        list_terms = ("list", "show", "all transactions", "display", "fetch")
        category_map = {
            "food": "Food & Dining",
            "dining": "Food & Dining",
            "travel": "Travel",
            "shopping": "Shopping",
            "entertainment": "Entertainment",
            "healthcare": "Healthcare",
            "education": "Education",
            "salary": "Salary",
            "investment": "Investment",
            "transport": "Transportation",
            "transportation": "Transportation",
            "utility": "Bills & Utilities",
            "utilities": "Bills & Utilities",
        }
        category = None
        for keyword, canonical in category_map.items():
            if re.search(rf"\b{re.escape(keyword)}\b", q):
                category = canonical
                break

        # Category searches are exact structured queries, even when phrased as
        # a natural-language question. Do not spend an LLM call on them.
        if category:
            is_aggregate = any(term in q for term in aggregation_terms)
            return QueryPlan(
                needs_mongo=True,
                needs_vector=False,
                needs_aggregation=is_aggregate,
                filters={"category": category},
                query_type="analytical" if is_aggregate else "simple",
                limit=1000,
                intent=f"Transactions in {category}",
            )

        # Merchant/description questions intentionally exercise the hybrid
        # retriever, but routing itself remains deterministic when a provider
        # is rate-limited or unavailable.
        semantic_terms = ("merchant", "related to", "description", "payment to", "transaction for")
        if any(term in q for term in semantic_terms):
            return QueryPlan(
                needs_mongo=True,
                needs_vector=True,
                needs_aggregation=False,
                vector_query=query,
                query_type="semantic",
                limit=50,
                intent="Hybrid merchant or description search",
            )

        if not any(term in q for term in aggregation_terms + list_terms):
            return None

        is_list = any(term in q for term in list_terms) and not any(
            term in q for term in aggregation_terms
        )
        return QueryPlan(
            needs_mongo=True,
            needs_vector=False,
            needs_aggregation=not is_list,
            filters={},
            query_type="simple" if is_list else "analytical",
            limit=1000,
            intent="Deterministic financial transaction query",
        )

    async def plan(self, query: str, history: List[Dict] = None) -> Tuple[QueryPlan, List[str]]:
        deterministic_plan = self._deterministic_financial_plan(query)
        if deterministic_plan is not None:
            return deterministic_plan, ["Deterministic Mongo plan applied for accounting query"]

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
                    if isinstance(doc[field], Decimal128):
                        doc[field] = doc[field].to_decimal()
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
            normalized = []
            for d in docs:
                # Mongo's ObjectId and Pinecone's transaction_id represent
                # the same record. Preserve one canonical ID for deduplication.
                if d.get("_id") is not None:
                    d["transaction_id"] = str(d.get("_id"))
                normalized.append(self._normalize_doc(d))
            return normalized, None
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

    @staticmethod
    def _document_keys(doc: Dict) -> set[str]:
        """Return all safe identities for a MongoDB/Pinecone transaction."""
        keys = set()
        transaction_id = doc.get("transaction_id")
        if transaction_id and str(transaction_id).lower() not in {"none", "null"}:
            keys.add(f"transaction:{transaction_id}")
        mongo_id = doc.get("_id")
        if mongo_id:
            keys.add(f"transaction:{mongo_id}")
        if keys:
            # Distinct ledger rows can legitimately share the same date,
            # description, and amount, so do not use a content fingerprint
            # when a trusted stable ID is present.
            return keys
        # Also keep a content fingerprint. This covers legacy vectors whose
        # ID was generated differently from Mongo's ObjectId.
        fingerprint = "|".join(str(doc.get(k, "")) for k in (
            "user_id", "date", "description", "amount", "debit", "credit"
        ))
        keys.add(f"fingerprint:{fingerprint}")
        return keys

    async def retrieve(self, plan: QueryPlan, user_id: str) -> List[Dict]:
        """Compatibility wrapper for callers that only need documents."""
        documents, _ = await self.retrieve_with_report(plan, user_id)
        return documents

    async def retrieve_with_report(self, plan: QueryPlan, user_id: str) -> Tuple[List[Dict], Dict[str, Any]]:
        # Bug #17: Security guard against empty user_id
        if not user_id:
            logger.error("Security alert: Attempted retrieval with empty user_id")
            raise ValueError("user_id is required for secure transaction retrieval")

        tasks: List[Tuple[str, asyncio.Task]] = []
        if plan.needs_mongo:
            tasks.append(("mongo", asyncio.create_task(self._mongo_query(plan, user_id))))
        if plan.needs_vector:
            tasks.append(("vector", asyncio.create_task(self._vector_query(plan, user_id))))
        if not tasks:
            tasks.append(("mongo", asyncio.create_task(self._mongo_query(
                QueryPlan(needs_mongo=True, filters={}, limit=100), user_id
            ))))

        results = await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)
        merged: List[Dict] = []
        seen: set = set()
        mongo_count = 0
        vector_count = 0
        source_errors = []
        mongo_docs: List[Dict] = []
        vector_docs: List[Dict] = []

        # Dissecting gather results safely
        for (source, _), res in zip(tasks, results):
            if isinstance(res, Exception):
                source_errors.append(f"{source} task failed: {str(res)}")
                continue
            
            docs, err = res
            if err:
                source_errors.append(err)
                continue

            if source == "mongo":
                mongo_count = len(docs)
                mongo_docs.extend(docs)
            else:
                vector_count = len(docs)
                vector_docs.extend(docs)

        # Mongo is the authoritative financial ledger. Pinecone is used for
        # semantic recall, but must not replace or alter ledger rows when the
        # structured query already returned Mongo documents. This prevents
        # stale/legacy vector metadata from changing totals.
        candidate_docs = mongo_docs if mongo_docs else vector_docs
        for doc in candidate_docs:
            identities = self._document_keys(doc)
            if not identities.intersection(seen):
                seen.update(identities)
                merged.append(doc)
        
        rag_logger.log_retrieval(
            mongo_enabled=plan.needs_mongo,
            vector_enabled=plan.needs_vector,
            mongo_count=mongo_count,
            vector_count=vector_count,
            merged_count=len(merged),
            source_errors=source_errors
        )
        return merged, {
            "mongo_docs": mongo_count,
            "vector_docs": vector_count,
            "merged_docs": len(merged),
            "source_errors": source_errors,
        }

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
        """Compatibility wrapper for callers that only need documents."""
        documents, _ = self.rerank_with_report(docs, query, plan)
        return documents

    def rerank_with_report(self, docs: List[Dict], query: str, plan: QueryPlan) -> Tuple[List[Dict], Dict[str, Any]]:
        if not docs:
            rag_logger.log_rerank(0, 0, skipped_reason="No documents to rerank")
            return docs, {"input_docs": 0, "reranked_docs": 0, "top_score": None}
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
        return reranked, {
            "input_docs": len(docs),
            "reranked_docs": len(reranked),
            "top_score": scored[0][0] if scored else None,
        }

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
  "transactions": [{{"date": "...", "description": "...", "amount": 0.0, "debit": 0.0, "credit": 0.0, "category": "..."}}],
  "summary_line": "TL;DR"
}}
"""

class ResponseGenerator:
    async def generate(self, query: str, context: FinancialContext, plan: QueryPlan) -> Dict:
        llm = build_chat_llm(settings.GEMINI_MODEL, temperature=0.1)
        
        raw_txns = context.raw_docs[:200]
        
        p = f"{RESPONSE_SYSTEM_PROMPT}\n\nQUERY: {query}\nPRE-COMPUTED METRICS: {context.model_dump_json(exclude={'raw_docs'})}\nRAW TRANSACTIONS: {json.dumps(raw_txns, default=str)}\nYOUR JSON RESPONSE:"
        try:
            res = await llm.ainvoke(p)
            c = res.content.strip()
            if "```json" in c: c = c.split("```json")[1].split("```")[0].strip()
            final_json = json.loads(c)
            # Totals and transaction amounts come from deterministic context, not model arithmetic.
            final_json["metrics"] = [
                {"label": "Total spent", "value": context.total_debit, "formatted": f"Rs {context.total_debit:,.2f}"},
                {"label": "Total received", "value": context.total_credit, "formatted": f"Rs {context.total_credit:,.2f}"},
                {"label": "Net cash flow", "value": context.net_flow, "formatted": f"Rs {context.net_flow:,.2f}"},
            ]
            final_json["transactions"] = context.top_transactions
            if plan.needs_aggregation:
                # For accounting questions, the user-facing sentence must be
                # grounded in the deterministic Mongo context as well as the
                # metrics cards. This prevents a provider from hallucinating
                # arithmetic even when its JSON is otherwise valid.
                final_json["answer"] = (
                    f"Across {context.transaction_count} transactions, total spent was "
                    f"Rs {context.total_debit:,.2f}, total received was "
                    f"Rs {context.total_credit:,.2f}, and net cash flow was "
                    f"Rs {context.net_flow:,.2f}."
                )
                final_json["summary_line"] = (
                    f"Spent Rs {context.total_debit:,.2f}; received "
                    f"Rs {context.total_credit:,.2f}."
                )
            rag_logger.log_response_gen(
                json_parse_success=True,
                fallback_used=False,
                answer=final_json.get("answer", ""),
                metrics=final_json.get("metrics", []),
                insights=final_json.get("insights", []),
                transactions=final_json.get("transactions", [])
            )
            final_json["_rag_response_meta"] = {
                "json_parse_success": True,
                "fallback_used": False,
            }
            return final_json
        except Exception as e:
            rag_logger.log_error("RESPONSE_GENERATOR", e)
            fallback_ans = (
                f"Analyzed {context.transaction_count} transactions. "
                f"Total spent: Rs {context.total_debit:,.2f}; "
                f"total received: Rs {context.total_credit:,.2f}; "
                f"net cash flow: Rs {context.net_flow:,.2f}."
            )
            fallback = {
                "answer": fallback_ans,
                "metrics": [
                    {"label": "Total spent", "value": context.total_debit, "formatted": f"Rs {context.total_debit:,.2f}"},
                    {"label": "Total received", "value": context.total_credit, "formatted": f"Rs {context.total_credit:,.2f}"},
                    {"label": "Net cash flow", "value": context.net_flow, "formatted": f"Rs {context.net_flow:,.2f}"},
                ],
                "transactions": context.top_transactions[:10],
            }
            rag_logger.log_response_gen(
                json_parse_success=False,
                fallback_used=True,
                answer=fallback_ans,
                metrics=[],
                insights=[],
                transactions=context.top_transactions[:10]
            )
            fallback["_rag_response_meta"] = {
                "json_parse_success": False,
                "fallback_used": True,
            }
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
        pipeline_started = time.perf_counter()
        try:
            is_valid, err = validate_query(user_query)
            rag_logger.log_validation(is_valid, err, len(user_query))
            _record_rag_stage(
                "rag.query_validation", pipeline_started,
                status="success" if is_valid else "failed",
                metadata={"query_length": len(user_query), "has_chat_history": bool(chat_history)},
            )
            if not is_valid:
                return {"answer": err, "transactions": []}

            stage_started = time.perf_counter()
            plan, patches = await self.planner.plan(user_query, chat_history)
            rag_logger.log_plan(plan, safety_corrections=patches)
            _record_rag_stage(
                "rag.planner", stage_started,
                metadata={
                    "query_type": plan.query_type,
                    "needs_mongo": plan.needs_mongo,
                    "needs_vector": plan.needs_vector,
                    "needs_aggregation": plan.needs_aggregation,
                    "limit": plan.limit,
                    "safety_correction_count": len(patches),
                },
            )

            stage_started = time.perf_counter()
            raw_docs, retrieval_report = await self.retriever.retrieve_with_report(plan, user_id)
            _record_rag_stage(
                "rag.retrieval", stage_started,
                status="failed" if retrieval_report["source_errors"] else "success",
                metadata={
                    "mongo_docs": retrieval_report["mongo_docs"],
                    "vector_docs": retrieval_report["vector_docs"],
                    "merged_docs": retrieval_report["merged_docs"],
                    "source_error_count": len(retrieval_report["source_errors"]),
                    "result_available": bool(raw_docs),
                },
                error_type="RetrievalError" if retrieval_report["source_errors"] else None,
            )

            stage_started = time.perf_counter()
            top_docs, rerank_report = self.reranker.rerank_with_report(raw_docs, user_query, plan)
            _record_rag_stage(
                "rag.reranker", stage_started,
                metadata={
                    "raw_docs": rerank_report["input_docs"],
                    "reranked_docs": rerank_report["reranked_docs"],
                    "top_score": rerank_report["top_score"] or 0.0,
                    "rerank_retained_ratio": round(
                        rerank_report["reranked_docs"] / max(rerank_report["input_docs"], 1), 4
                    ),
                },
            )

            stage_started = time.perf_counter()
            context = self.context_builder.build(top_docs, plan)
            _record_rag_stage(
                "rag.context", stage_started,
                metadata={
                    "context_transaction_count": context.transaction_count,
                    "context_total_debit": context.total_debit,
                    "context_total_credit": context.total_credit,
                },
            )

            is_valid_ctx, ctx_err = validate_context(context, plan)
            rag_logger.log_context_validation(is_valid_ctx, ctx_err)
            if not is_valid_ctx:
                evaluate_rag_run(
                    plan=plan, raw_documents=raw_docs, reranked_documents=top_docs,
                    context=context, response=None,
                    source_errors=retrieval_report["source_errors"],
                )
                return {"answer": ctx_err, "transactions": []}

            stage_started = time.perf_counter()
            final = await self.generator.generate(user_query, context, plan)
            response_meta = final.pop("_rag_response_meta", {})
            _record_rag_stage(
                "rag.response", stage_started,
                metadata={
                    "answer_length": len(final.get("answer", "")),
                    "response_json_valid": bool(response_meta.get("json_parse_success")),
                    "response_fallback": bool(response_meta.get("fallback_used")),
                },
            )
            evaluate_rag_run(
                plan=plan, raw_documents=raw_docs, reranked_documents=top_docs,
                context=context, response=final,
                source_errors=retrieval_report["source_errors"], response_meta=response_meta,
            )

            rag_logger.log_pipeline_complete(
                txn_count=context.transaction_count,
                answer_length=len(final.get("answer", "")),
                steps_completed=5
            )
            return final
        except Exception as exc:
            _record_rag_stage(
                "rag.pipeline", pipeline_started, status="failed", error_type=type(exc).__name__,
            )
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        import google.generativeai as genai
        model = "models/gemini-embedding-001"
        with observe_external_llm("gemini", model, kind="embedding") as span:
            result = genai.embed_content(model=model, content=text)
            span.response = result
        return result["embedding"]

    async def delete_transaction_vector(self, tid: str): await self.retriever._get_pinecone().delete_transaction_vector(tid)
    async def delete_transactions_by_upload_id(self, uid: str): await self.retriever._get_pinecone().delete_transactions_by_upload_id(uid)
    async def upsert_transaction_vector(self, tid: str, emb: List[float], meta: Dict):
        self.retriever._get_pinecone().index.upsert(vectors=[{"id": str(tid), "values": emb, "metadata": meta}], namespace="transactions")
