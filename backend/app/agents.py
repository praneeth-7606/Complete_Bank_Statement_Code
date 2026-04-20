import google.generativeai as genai
import json
import re
import datetime
import asyncio
from typing import List, Dict, Any, Optional
import logging
from .config import settings
from calendar import monthrange
from pydantic import BaseModel, Field, model_validator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)
genai.configure(api_key=settings.GEMINI_API_KEY)

from .base_agent import BaseAgent, extract_json_from_response



from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

class StructuredTransaction(BaseModel):
    date: str = Field(description="Date in YYYY-MM-DD format")
    description: str = Field(description="Clear transaction description")
    debit: float = Field(default=0.0, description="Amount debited (sent out)")
    credit: float = Field(default=0.0, description="Amount credited (received)")
    amount: Optional[float] = Field(default=None, description="Absolute transaction amount (will be calculated if not provided)")

    @model_validator(mode='after')
    def set_amount(self) -> 'StructuredTransaction':
        if self.amount is None:
            self.amount = max(abs(self.debit), abs(self.credit))
        return self

class BatchStructuredTransactions(BaseModel):
    transactions: List[StructuredTransaction] = Field(description="List of structured transactions matching the input lines exactly.")

class TransactionStructuringAgent:
    """Parses raw transaction lines into structured JSON using LangChain (LLM-First, No Agent Loop)."""
    
    def __init__(self, model_name="gemini-2.5-flash"):
        self.llm = ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=0.1,
            google_api_key=settings.GEMINI_API_KEY
        )
        self.structured_llm = self.llm.with_structured_output(BatchStructuredTransactions)

    async def structure_mini_batch(self, transaction_lines: List[str]) -> List[Dict]:
        """Structure 2-5 transactions for optimal accuracy/speed balance."""
        return await self.structure_transactions_in_batch(transaction_lines)

    async def structure_transactions_in_batch(self, transaction_lines: List[str]) -> List[Dict]:
        if not transaction_lines: return []
        
        system_rules = """You are an expert at parsing Indian bank transactions (UPI/NEFT/IMPS).
Convert raw text lines into structured JSON objects.
        
**CRITICAL RULES:**
1. Extract ALL details accurately.
2. Date must be YYYY-MM-DD. If year is missing, assume current year.
3. For amounts: Payment OUT = debit field (credit=0), Payment IN = credit field (debit=0).
4. Description should be human-readable (e.g., 'Swiggy' instead of 'UPI/4504...-Swiggy').
5. Ensure the output list length matches the input lines EXACTLY.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_rules),
            ("user", "Structure these transactions:\n\n{lines}")
        ])
        
        chain = prompt | self.structured_llm
        
        try:
            result = await chain.ainvoke({"lines": "\n".join(transaction_lines)})
            return [t.model_dump() for t in result.transactions]
        except Exception as e:
            logger.error(f"Structuring error: {e}")
            return []

from .agent_categorization import CategorizationAgent, PrimaryCategorization, BatchCategorization
# Alias for backward compatibility if needed
TransactionCategory = PrimaryCategorization
from .agent_analyst import FinancialAnalystAgent



class FinancialChatAgent(BaseAgent):
    """Generates a natural language response for the chat API - OPTIMIZED FOR SPEED."""
    
    def __init__(self, model_name="gemini-2.5-flash"):
        # Use stable Gemini Flash model (better rate limits)
        super().__init__(model_name)
    
    async def generate_response(self, user_query: str, retrieved_data: List[Dict]) -> str:
        if not retrieved_data: return "I couldn't find any transactions that match your query."
        
        # OPTIMIZATION: Limit data sent to AI for faster responses
        transaction_count = len(retrieved_data)
        
        # If too many transactions, summarize instead of listing all
        if transaction_count > 50:
            # Send only summary data for large result sets
            total_debit = sum(float(t.get('debit', 0)) for t in retrieved_data)
            total_credit = sum(float(t.get('credit', 0)) for t in retrieved_data)
            categories = {}
            for t in retrieved_data:
                cat = t.get('category', 'Uncategorized')
                categories[cat] = categories.get(cat, 0) + 1
            
            summary_data = {
                "total_transactions": transaction_count,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "categories": categories,
                "sample_transactions": retrieved_data[:10]  # First 10 as examples
            }
            data_json_string = json.dumps(summary_data, indent=2, default=str)
        else:
            data_json_string = json.dumps(retrieved_data, indent=2, default=str)
        
        prompt = f"""You are a FAST and precise financial assistant. Respond quickly and concisely.

**SPEED-OPTIMIZED RULES:**
1. Be CONCISE - users want fast answers
2. For large datasets (>50 transactions): Provide summary with key insights
3. For small datasets (50 or less): List all transactions
4. Use bullet points and emojis for readability
5. Calculate totals and provide insights quickly

**RESPONSE FORMATS:**

For SMALL datasets (50 or less transactions):
Found {transaction_count} transactions:
- Date | Description | Amount | Category

For LARGE datasets (>50 transactions):
Analysis of {transaction_count} transactions:
- Total Spent: Rs X,XXX
- Total Received: Rs X,XXX
- Top Categories: [list top 3]
- Sample transactions: [show 5-10 examples]

**USER QUESTION:**
{user_query}

**DATA ({transaction_count} transactions):**
{data_json_string}

**YOUR FAST RESPONSE:**
"""
        try:
            # Use faster generation config via invoke
            response = await self.llm.ainvoke(prompt)
            if response and hasattr(response, 'content') and response.content: 
                return response.content.strip()
            else: 
                return "I received an empty response from the analysis service."
        except Exception as e:
            logger.error(f"Chat response error: {e}")
            return "An error occurred while trying to formulate a response."

class RoutePayload(BaseModel):
    query_type: str = Field(description="Must be either 'filter' or 'vector'")
    payload: Any = Field(description="A MongoDB JSON query dict for filter, or a string string for vector")

class QueryRouterAgent:
    """Analyzes a user query to decide between vector search and filter-based search using Structured Output."""
    
    def __init__(self, model_name="gemini-2.5-flash"):
        self.llm = ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=0.1,
            google_api_key=settings.GEMINI_API_KEY
        )
        self.structured_llm = self.llm.with_structured_output(RoutePayload)

    async def route_query(self, user_query: str) -> Dict:
        current_year = datetime.datetime.now().year
        
        system_rules = f"""You are a master query routing agent. Convert the user's question into a valid MongoDB query filter.
        
**DATABASE SCHEMA:**
- `date`: A BSON Date object. MUST be queried with date ranges using `$gte` and `$lt`.
- `description`: Text. Use `$regex` for text matching (case-insensitive with "i" flag).
- `category`: String, e.g., "Food & Dining", "Shopping", "Investments", "Utilities", etc.
- `debit`: Float. For expenses, query with {{"debit": {{"$gt": 0}} }}.
- `credit`: Float. For income, query with {{"credit": {{"$gt": 0}} }}.

**CRITICAL DATE RULES:**
1. NEVER use `$regex` on the `date` field.
2. Always convert date queries into a range using `$gte` (start date) and `$lt` (day AFTER end date).
3. Dates in the payload MUST be strings formatted as "YYYY-MM-DD".
4. Current year is {current_year}. Used if no year is explicitly mentioned.

**CRITICAL ROUTING RULES:**
- Keywords like "list", "all", "show me", "give me" with dates/categories  FILTER
- Specific merchant names without date/category  VECTOR
- Date + category combinations  FILTER
- "transactions in [month]" or "during [month]"  FILTER
- Always prefer FILTER over VECTOR when the query has clear date/category/amount criteria.

Examples:
- "what did I spend on food in august": {{"query_type": "filter", "payload": {{"category": "Food & Dining", "date": {{"$gte": "{current_year}-08-01", "$lt": "{current_year}-09-01"}}}}}}
- "what was that purchase at the bike zone?": {{"query_type": "vector", "payload": "purchase at the bike zone"}}
- "list all transactions in august": {{"query_type": "filter", "payload": {{"date": {{"$gte": "{current_year}-08-01", "$lt": "{current_year}-09-01"}}}}}}
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_rules),
            ("user", "{query}")
        ])
        
        chain = prompt | self.structured_llm
        
        try:
            result = await chain.ainvoke({"query": user_query})
            return {"query_type": result.query_type, "payload": result.payload}
        except Exception as e:
            logger.error(f"Routing error: {{e}}")
            # Default to vector search if structured routing fails
            return {"query_type": "vector", "payload": user_query}

class EmbeddingAgent:
    """Handles the creation of embeddings for vector search with batch optimization."""
    
    def __init__(self, model: str = "models/embedding-001", batch_size: int = 100):
        """
        Initialize the embedding agent.
        
        Args:
            model: Embedding model to use
            batch_size: Maximum documents per API call (Google supports up to 100)
        """
        self.model = model
        self.batch_size = batch_size
    
    async def embed_single_document(self, document: Dict) -> List[float]:
        """
        Embed a single document (fallback for error cases).
        
        Args:
            document: Single document dictionary
            
        Returns:
            Embedding vector
        """
        result = await self.embed_documents([document])
        return result[0] if result else []
    
    async def embed_documents(self, documents: List[Dict]) -> List[List[float]]:
        """
        Embed documents in batches for optimal API usage.
        
        Google's embedding API supports batch requests (up to 100 documents),
        which is much faster than individual calls.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            List of embedding vectors
        """
        if not documents:
            return []
        
        # Use the correct model name with prefix for v1beta API
        # models/gemini-embedding-001 is stable and returns 768 dimensions
        model_name = "models/gemini-embedding-001"
        
        # Prepare content strings for all documents
        # Note: input documents are expected to be LangChain Document objects or dicts
        content_strings = []
        for doc in documents:
            if hasattr(doc, 'page_content'):
                content_strings.append(doc.page_content)
            elif isinstance(doc, dict):
                # Fallback for raw dicts
                desc = doc.get('description', '')
                amt = doc.get('amount', 0.0)
                cat = doc.get('category', 'Others')
                content_strings.append(f"Transaction: {desc} | Amount: {amt} | Category: {cat}")
            else:
                content_strings.append(str(doc))

        all_embeddings = []
        
        # Process in batches if necessary (Google supports up to 100 per call)
        for i in range(0, len(content_strings), self.batch_size):
            batch_content = content_strings[i:i + self.batch_size]
            
            try:
                # Explicitly request 768 dimensions for compatibility with Pinecone index
                result = genai.embed_content(
                    model=model_name,
                    content=batch_content,
                    task_type="retrieval_document",
                    output_dimensionality=768
                )
                
                # Handle both single and batch responses
                if 'embedding' in result:
                    emb = result['embedding']
                    if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
                        # Batch response: list of embeddings
                        all_embeddings.extend(emb)
                    else:
                        # Single response: wrap in list
                        all_embeddings.append(emb)
                    
            except Exception as e:
                logger.error(f"Embedding Error for batch {i//self.batch_size + 1}: {e}", 
                           exc_info=True)
                # Return zero vectors (768-dim) for failed batch to avoid crashing Pinecone
                # Note: Pinecone requires at least one non-zero value, but we can use a tiny value
                # Or just skip it. But we must return the same number of vectors.
                # Actually, Pinecone error said "Dense vectors must contain at least one non-zero value"
                # So we use a tiny non-zero value at index 0.
                error_vector = [0.0] * 768
                error_vector[0] = 1e-6 
                all_embeddings.extend([error_vector] * len(batch_content))
        
        logger.info(f"Successfully embedded {len(all_embeddings)} documents in "
                   f"{(len(documents) + self.batch_size - 1) // self.batch_size} API call(s)")
        
        return all_embeddings


# app/agents.py - LangChain Agentic Implementation
# app/agents.py - TRUE AGENTIC IMPLEMENTATION with Credit/Debit Fix

# app/agents.py - FIXED VERSION WITH CORRECT AMOUNT EXTRACTION

# app/agents.py - COMPLETE FINAL VERSION FOR YOUR BANK FORMAT

# app/agents.py - FINAL WORKING VERSION FOR YOUR BANK STATEMENT

