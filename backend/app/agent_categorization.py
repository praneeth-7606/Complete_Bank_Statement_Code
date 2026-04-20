import json
import asyncio
import logging
import re
import os
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from .config import settings
from . import models

logger = logging.getLogger(__name__)

# --- Telemetry Config ---
LOG_DIR = Path("logs/categorization")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- Structured Output Models ---

class CategorizationResult(BaseModel):
    category: str = Field(description="One of: Food & Dining, Transportation, Shopping, Entertainment, Bills & Utilities, Healthcare, Education, Travel, Investment, Dividend, Salary, Transfer, Personal Transfer, Other Transfers, Other")
    subcategory: str = Field(default="General", description="A specific subcategory for the transaction (e.g., 'Groceries', 'Digital Transfer', 'Medical')")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief explanation for this classification")
    source: str = Field(description="The layer that identified this: rule, pattern, merchant, local_history, llm, or agent")

class BatchCategorization(BaseModel):
    transactions: List[CategorizationResult] = Field(description="Strictly ordered list of classifications matching the input transactions length exactly.")

# Backward compatibility alias
PrimaryCategorization = CategorizationResult

# --- Intelligence Engines ---

class RuleEngine:
    """Deterministic rule matching for high-confidence financial markers."""
    RULES = {
        r"ACHC|DIV": ("Dividend", "Dividends"),
        r"GROWW|ZERODHA|UPSTOX": ("Investment", "Stocks & MF"),
        r"SALARY|PAYROLL": ("Salary", "Primary Income"),
        r"ATM|CASH WDL": ("Other", "Cash Withdrawal"),
        r"LOAN|EMI": ("Bills & Utilities", "Loan Repayment"),
        r"INTEREST|INT": ("Dividend", "Bank Interest")
    }

    @classmethod
    def match(cls, description: str, amount: float = 0, is_credit: bool = False) -> Optional[Dict[str, Any]]:
        desc = description.upper()
        # Specific overrides for Investment vs Dividend direction
        if re.search(r"GROWW|ZERODHA|UPSTOX|INDMONEY", desc):
            if is_credit:
                return {
                    "category": "Dividend",
                    "subcategory": "Investment Withdrawal",
                    "confidence": 0.95,
                    "reasoning": "Credit from investment platform identified as Dividend/Withdrawal",
                    "source": "rule"
                }
            else:
                return {
                    "category": "Investment",
                    "subcategory": "Stocks & MF",
                    "confidence": 0.95,
                    "reasoning": "Debit to investment platform identified as Investment",
                    "source": "rule"
                }

        for pattern, (cat, sub) in cls.RULES.items():
            if re.search(pattern, desc):
                return {
                    "category": cat,
                    "subcategory": sub,
                    "confidence": 0.95,
                    "reasoning": f"Deterministic rule match: {pattern}",
                    "source": "rule"
                }
        return None

class MerchantIntelligence:
    """Regex-based merchant detection system."""
    PATTERNS = {
        r"SWIGGY|ZOMATO|DOMINOS|EATFIT": ("Food & Dining", "Online Ordering"),
        r"AMAZON|FLIPKART|MYNTRA": ("Shopping", "E-commerce"),
        r"UBER|OLA|RAPIDO": ("Transportation", "Ride Hailing"),
        r"NETFLIX|SPOTIFY|PRIME VIDEO": ("Entertainment", "Subscription"),
        r"AIRTEL|JIO|VODAFONE": ("Bills & Utilities", "Telecom"),
        r"IRCTC|INDIGO|MAKEMYTRIP|SRM TRAVELS": ("Travel", "Tickets"),
        r"STARBUCKS|CHAIPOINT|BLUE TOKAI": ("Food & Dining", "Cafe"),
        r"APOLLO|PHARMACY|CLINIC|MEDPLUS|HOSPITAL": ("Healthcare", "Medical")
    }

    @classmethod
    def match(cls, description: str) -> Optional[Dict[str, Any]]:
        desc = description.upper()
        for pattern, (cat, sub) in cls.PATTERNS.items():
            if re.search(pattern, desc):
                return {
                    "category": cat,
                    "subcategory": sub,
                    "confidence": 0.90,
                    "reasoning": f"Merchant pattern match: {pattern}",
                    "source": "merchant"
                }
        return None

class PatternEngine:
    """Batch-level frequency analysis."""
    @classmethod
    def analyze_batch(cls, transactions: List[Dict]) -> Dict[str, str]:
        """Detects personal vs corporate transfers based on frequency."""
        counts = {}
        for txn in transactions:
            desc = txn.get('description', '').upper()
            name_match = re.search(r"UPI-(\w+)", desc)
            if name_match:
                name = name_match.group(1)
                counts[name] = counts.get(name, 0) + 1
        
        results = {}
        for name, count in counts.items():
            results[name] = "Transfer (Frequent/Personal)" if count > 1 else "Transfer (One-time)"
        return results

# --- Main Intelligence Agent ---

class CategorizationAgent:
    """Production-grade self-learning financial intelligence engine."""
    
    def __init__(self, model_name="gemini-2.5-flash"):
        self.llm = ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=0, 
            google_api_key=settings.GEMINI_API_KEY
        )
        self.structured_llm = self.llm.with_structured_output(BatchCategorization)
        
        # Tools for the Insights Agent
        self._setup_investigator()

    def _setup_investigator(self):
        # We define tools dynamically to ensure they have the proper context
        @tool
        def rule_engine_tool(description: str, amount: float = 0, is_credit: bool = False) -> str:
            """Call the deterministic rule engine. amount and is_credit are optional but help accuracy."""
            match = RuleEngine.match(description, amount, is_credit)
            return json.dumps(match) if match else "No rule matched."

        @tool
        def merchant_lookup_tool(description: str) -> str:
            """Search the merchant regex database."""
            match = MerchantIntelligence.match(description)
            return json.dumps(match) if match else "Merchant unknown."

        @tool
        async def user_history_tool(description: str) -> str:
            """Check historical corrections from MongoDB using extracted identity."""
            # Use the intelligent merchant identity extractor
            identity = self._extract_merchant_identity(description)
            if not identity:
                return "No clear merchant identity found in description."
                
            # Exact match on the extracted identity keyword
            match = await models.Correction.find_one({
                "transaction_description_keyword": identity
            })
            
            if match:
                return f"SUCCESS: Found user correction for '{identity}' -> {match.correct_category}"
            return f"No historical correction for identity: '{identity}'"

        @tool
        async def embedding_similarity_tool(description: str) -> str:
            """Check Pinecone for similar past transactions."""
            try:
                from .pinecone_store import PineconeVectorStore
                vector_db = PineconeVectorStore(
                    api_key=settings.PINECONE_API_KEY,
                    environment=settings.PINECONE_ENVIRONMENT,
                    index_name=settings.PINECONE_INDEX_NAME
                )
                matches = await vector_db.query_transactions(description, n_results=3)
                if matches:
                    results = [f"Match: {m.get('description')} -> {m.get('category')}" for m in matches]
                    return "\n".join(results)
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
            return "No highly similar vector matches found."

        @tool
        async def web_search_tool(query: str) -> str:
            """Last resort: Search the web to identify business type."""
            logger.info(f" INVESTIGATOR: Searching web for '{query}'...")
            return f"Simulated search results: '{query}' appears to be a retail merchant."

        self.tools = [rule_engine_tool, merchant_lookup_tool, user_history_tool, embedding_similarity_tool, web_search_tool]
        
        # System Message to be prepended to every investigation
        self.investigator_prompt = (
            "You are a senior Financial Investigator. Your mission is to categorize unknown transactions accurately. "
            "STRICT INVESTIGATION ORDER:\n"
            "1. rule_engine_tool (Deterministic markers)\n"
            "2. merchant_lookup_tool (Regex patterns)\n"
            "3. user_history_tool (User's past corrections)\n"
            "4. embedding_similarity_tool (Similar descriptions in whole database)\n"
            "5. web_search_tool (EXTERNAL search - strictly only if others fail)\n\n"
            "DO NOT GUESSTIMATE. You MUST use tools to find evidence. "
            "Return the found category, subcategory, and a reasoning trace citing which tool provided the answer."
        )
        
        # Fixed: state_modifier was removed to avoid TypeError on older langgraph versions
        self.investigator = create_react_agent(
            self.llm, 
            self.tools
        )

    # --- Propagation & Learning Engine ---

    @classmethod
    def _extract_merchant_identity(cls, description: str) -> str:
        """Extracts the core name/merchant from complex UPI/Bank descriptions."""
        if not description: return ""
        
        # Indian UPI pattern: Upl Txn: /Masked/Name/Category/Ref/Ref
        if "/" in description:
            parts = description.split("/")
            # Look for the second or third part which usually has the name
            for part in parts[1:3]:
                # Remove masking '*' and then strip leading/trailing non-alpha noise like '-'
                clean_name = re.sub(r'[*]+', '', part).strip()
                clean_name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', clean_name).strip()
                if len(clean_name) > 3:
                    return clean_name
        
        # Fallback: Remove common noise and take first 30 chars
        clean = re.sub(r'[0-9]{10,}', '', description) # remove long numbers
        clean = re.sub(r'[*]+', '', clean).strip()
        return clean[:40]

    @classmethod
    async def propagate_category(cls, user_id: str, pattern: str, correct_category: str):
        """Propagates a category update to all similar transactions for a user."""
        # 0. Intellegently extract the identity keyword from the description
        identity = cls._extract_merchant_identity(pattern)
        logger.info(f"[START] PROPAGATION IDENTIFIED: '{identity}' (Extracted from '{pattern[:30]}...')")
        
        # Use re.escape on the EXTRACTED identity
        escaped_identity = re.escape(identity)
        logger.info(f"[START] PROPAGATION: Updating all transactions matching '{identity}' to '{correct_category}'")
        
        # 1. Update MongoDB
        result = await models.Transaction.find(
            models.Transaction.user_id == user_id,
            {"description": {"$regex": escaped_identity, "$options": "i"}}
        ).update({"$set": {"category": correct_category}})
        
        logger.info(f"   -> Updated {result.modified_count} transactions in MongoDB.")
        
        # 2. Update Pinecone (for future uploads & similarity)
        # We also want to record this correction permanently
        try:
            correction = models.Correction(
                user_id=user_id,
                transaction_description_keyword=identity, # Save the IDENTITY, not the raw string
                correct_category=correct_category
            )
            await correction.insert()
            logger.info(f"   -> Recorded correction rule for '{identity}'")
        except Exception as e:
             logger.warning(f"   [WARN] Could not save permanent correction rule: {e}")

    async def _fallback_agent_classify(self, transaction: Dict) -> CategorizationResult:
        """Deep investigation using the ReAct agent."""
        logger.info(f"[INVESTIGATOR] Fallback triggered: {transaction.get('description')}")
        
        # Fixed: Include system prompt manually since state_modifier failed
        query = f"{self.investigator_prompt}\n\nInvestigate and categorize: {json.dumps(transaction)}. Follow tool priority strictly."
        
        try:
            result = await self.investigator.ainvoke({"messages": [("human", query)]})
            last_msg = result["messages"][-1].content
            
            # Final structuring back to Pydantic
            final = await self.llm.with_structured_output(CategorizationResult).ainvoke(
                f"Extract 'category', 'subcategory', and 'reasoning' from this investigation: {last_msg}. Set source='agent' and confidence=0.85."
            )
            return final
        except Exception as e:
            logger.error(f"Investigator failed: {e}")
            return CategorizationResult(category="Other", subcategory="Unknown", confidence=0.0, reasoning="Agent failure", source="agent")

    def _log_trace(self, transactions: List[Dict]):
        """Writes a detailed categorization trace to a separate log file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOG_DIR / f"trace_{timestamp}.json"
        
        trace_data = {
            "timestamp": timestamp,
            "total_processed": len(transactions),
            "summary": {
                "rule": len([t for t in transactions if t.get('source') == 'rule']),
                "merchant": len([t for t in transactions if t.get('source') == 'merchant']),
                "llm": len([t for t in transactions if t.get('source') == 'llm']),
                "agent": len([t for t in transactions if t.get('source') == 'agent']),
                "other": len([t for t in transactions if t.get('source') not in ['rule', 'merchant', 'llm', 'agent']])
            },
            "transactions": [
                {
                    "description": t.get('description'),
                    "amount": t.get('amount'),
                    "category": t.get('category'),
                    "subcategory": t.get('subcategory'),
                    "confidence": t.get('confidence'),
                    "source_method": t.get('source'),
                    "reasoning": t.get('reasoning')
                } for t in transactions
            ]
        }
        
        try:
            with open(log_file, "w") as f:
                json.dump(trace_data, f, indent=2)
            logger.info(f" Categorization Trace saved to: {log_file}")
        except Exception as e:
            logger.error(f"Failed to write trace log: {e}")

    async def categorize_transactions(self, transactions: List[Dict], user_id: str = None, user_name: str = "User", streaming_id: str = None) -> List[Dict]:
        """Reasoning-First Intelligence: History -> Merchant -> LLM Reasoning -> Rule Fallback."""
        if not transactions: return []
        
        from .log_streamer import log_streamer
        if streaming_id:
            await log_streamer.add_log(streaming_id, f"[CAT] Starting deep reasoning for {len(transactions)} transactions...", "info", 65)

        final_results = []
        remaining_indices = []
        
        for i, txn in enumerate(transactions):
            desc = txn.get('description', '')
            amt = float(txn.get('amount', 0))
            # Determine credit/debit status for rule matching
            is_credit = txn.get('type') == 'credit' or float(txn.get('credit', 0)) > 0
            
            identity = self._extract_merchant_identity(desc)
            
            # --- PHASE 0: User Correction Priority ---
            if user_id:
                try:
                    # Check if user has already corrected this specific identity
                    correction = await models.Correction.find_one(
                        models.Correction.user_id == user_id,
                        models.Correction.transaction_description_keyword == identity
                    )
                    if correction:
                        txn.update({
                            "category": correction.correct_category,
                            "subcategory": "User Preference",
                            "confidence": 1.0,
                            "reasoning": f"Matched previous user correction for '{identity}'",
                            "source": "local_history"
                        })
                        final_results.append(txn)
                        continue
                except Exception as e:
                    logger.warning(f"Error checking local history: {e}")

            # --- PHASE 1: Deterministic Rules (Investment/Dividend/Salary) ---
            rule_match = RuleEngine.match(desc, amount=amt, is_credit=is_credit)
            if rule_match:
                txn.update(rule_match)
                final_results.append(txn)
                continue

            # --- PHASE 2: Merchant Intelligence ---
            match = MerchantIntelligence.match(desc)
            if match:
                txn.update(match)
                final_results.append(txn)
                continue
            
            # Queue for Phase 2: LLM Brain
            remaining_indices.append(i)
            final_results.append(txn)

        # --- PHASE 2: Contextual LLM Reasoning (PARALLEL) ---
        if remaining_indices:
            todo_txns = [transactions[idx] for idx in remaining_indices]
            batch_size = 20
            
            if streaming_id:
                await log_streamer.add_log(streaming_id, f"LLM Brain analyzing {len(todo_txns)} merchants in parallel...", "info", 70)
            
            tasks = []
            for j in range(0, len(todo_txns), batch_size):
                batch = todo_txns[j:j + batch_size]
                tasks.append(self._process_llm_batch(
                    batch, 
                    remaining_indices, 
                    j, 
                    user_name, 
                    streaming_id, 
                    final_results, 
                    transactions
                ))
            
            await asyncio.gather(*tasks)

        self._log_trace(final_results)
        return final_results

    async def _process_llm_batch(self, batch, remaining_indices, start_offset, user_name, streaming_id, final_results, transactions):
        """Processes a single batch of transactions via LLM and applies results."""
        from .log_streamer import log_streamer
        
        system_prompt = f"""You are a world-class Financial Analyst. Your goal is to categorize transactions with 100% precision.
User Name: {user_name} (Used to identify self-transfers)

**SCORING CRITERIA:**
1. **Analyze WHOLE description**: Look for business names (Apollo, SRM, Zomato) anywhere in the string.
2. **Business vs Person**: If it looks like a business (Pharmacy, Travels, Clinic, Store, Pvt Ltd), use a business category.
3. **P2P Transfer Logic**: 
   - If description contains "{user_name}" or looks like own accounts -> Category: 'Personal Transfer'.
   - If description contains a person's name (and no business found) -> Category: 'Other Transfers'.
4. **Amount Context**: Large amounts for specialized names (Travels) confirm the category.

**CATEGORIES & TYPICAL SUBCATEGORIES:**
- Food & Dining, Transportation, Shopping, Entertainment, Bills & Utilities, Healthcare, Education, Travel, Investment, Dividend, Salary, Transfer, Personal Transfer, Other Transfers, Other

**STRUCTURED OUTPUT STRICTNESS**:
- source: 'llm'
- Return reasoning explaining WHY you chose a category.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Categorize this batch of {count} transactions. Return source='llm'.\n\nTransactions:\n{batch}")
        ])
        
        try:
            logger.info(f"   [BATCH] Processing {len(batch)} transactions starting at index {start_offset}...")
            llm_batch = await (prompt | self.structured_llm).ainvoke({
                "count": len(batch),
                "batch": json.dumps(batch)
            })
            
            for k, res in enumerate(llm_batch.transactions):
                if k >= len(batch): break 
                target_idx = remaining_indices[start_offset + k]
                
                # Confidence Fallback
                if res.confidence < 0.70:
                    rule_match = RuleEngine.match(
                        transactions[target_idx].get('description'),
                        amount=float(transactions[target_idx].get('amount', 0)),
                        is_credit=transactions[target_idx].get('type') == 'credit' or float(transactions[target_idx].get('credit', 0)) > 0
                    )
                    if rule_match:
                        final_results[target_idx].update(rule_match)
                        continue
                
                final_results[target_idx].update(res.model_dump())
                
                # Extreme Fallback (Agent)
                if res.confidence < 0.40:
                    agent_res = await self._fallback_agent_classify(transactions[target_idx])
                    final_results[target_idx].update(agent_res.model_dump())
                    
        except Exception as e:
            logger.error(f"LLM Batch failed: {e}")
            for k in range(len(batch)):
                idx = remaining_indices[start_offset + k]
                rule_match = RuleEngine.match(
                    transactions[idx].get('description'),
                    amount=float(transactions[idx].get('amount', 0)),
                    is_credit=transactions[idx].get('type') == 'credit' or float(transactions[idx].get('credit', 0)) > 0
                )
                if rule_match:
                    final_results[idx].update(rule_match)
                else:
                    final_results[idx].update({"category": "Other", "source": "llm", "confidence": 0.0, "reasoning": str(e)})
