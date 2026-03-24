from . import models, agents
from .config import settings
import datetime
import json
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Dict, Any, List

# Import Pinecone vector store (Production-ready)
from .vector_store_pinecone import PineconeVectorStore

logger = logging.getLogger(__name__)
logger.info("Using Pinecone vector store (Production)")

# Configure module-level logger
LOGFILE = os.path.join(os.path.dirname(__file__), '..', 'debug.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGFILE, mode='a', encoding='utf-8'),
    ],
)
logger = logging.getLogger(__name__)


# --- DEFINITIVE FIX: Convert date strings to the correct datetime.datetime object ---
def _convert_date_filters(mongo_filter: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively find and convert date strings in filters to datetime.datetime objects."""
    if "date" in mongo_filter and isinstance(mongo_filter["date"], dict):
        for key, value in mongo_filter["date"].items():
            if isinstance(value, str):
                try:
                    # Convert string to a full datetime.datetime object at midnight.
                    # This is the type that the MongoDB driver (BSON) expects.
                    mongo_filter["date"][key] = datetime.datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    logger.warning("Could not parse date string '%s' in filter.", value)
    return mongo_filter
# --- END OF FIX ---


class RAGPipeline:
    def __init__(self):
        self.vector_db: PineconeVectorStore | None = None
        self.chat_agent = None
        self.router_agent = None

    def _ensure_clients(self):
        """Initialize Pinecone vector store, chat agent, and router agent"""
        if self.vector_db is None:
            try:
                logger.info("Initializing Pinecone vector store...")
                self.vector_db = PineconeVectorStore(
                    api_key=settings.PINECONE_API_KEY,
                    environment=settings.PINECONE_ENVIRONMENT,
                    index_name=settings.PINECONE_INDEX_NAME
                )
                logger.info("✓ Pinecone vector store initialized successfully")
            except Exception as e:
                logger.error("❌ Failed to initialize Pinecone: %s", e, exc_info=True)
                raise
        
        if self.chat_agent is None:
            try:
                self.chat_agent = agents.FinancialChatAgent()
            except Exception as e:
                logger.warning("Failed to initialize FinancialChatAgent: %s", e, exc_info=True)
        
        if self.router_agent is None:
            try:
                self.router_agent = agents.QueryRouterAgent()
            except Exception as e:
                logger.warning("Failed to initialize QueryRouterAgent: %s", e, exc_info=True)

    async def index_transactions(self, transactions: List[models.Transaction]):
        if not transactions: return
        transaction_dicts = [t.model_dump(mode='json') for t in transactions]
        self._ensure_clients()
        if self.vector_db: await self.vector_db.add_transactions(transaction_dicts)
    
    async def delete_transactions_by_upload_id(self, upload_id: str):
        """Delete all transactions for a specific upload from vector DB"""
        self._ensure_clients()
        if self.vector_db:
            await self.vector_db.delete_transactions_by_upload_id(upload_id)

    # async def query(self, user_query: str) -> List[Dict[str, Any]]:
    #     """Hybrid routing: filter vs vector search."""
    #     logger.info("Executing router-based RAG flow for query: '%s'", user_query)
    #     self._ensure_clients()
    #     route = {"query_type": "vector", "payload": user_query}
    #     if self.router_agent: route = await self.router_agent.route_query(user_query)
    #     query_type, payload = route.get("query_type"), route.get("payload")
    #     retrieved_docs: List[Dict[str, Any]] = []

    #     if query_type == "filter":
    #         logger.info("Router chose FILTER search. Initial payload: %s", payload)
    #         try:
    #             processed_payload = _convert_date_filters(payload)
    #             logger.info("Querying MongoDB with processed payload: %s", processed_payload)
                
    #             client = AsyncIOMotorClient(settings.MONGO_URI)
    #             db = client.get_default_database()
    #             collection_name = getattr(models.Transaction.Settings, 'name', 'transactions')
                
    #             raw_docs = await db[collection_name].find(processed_payload).to_list(length=100)
    #             for d in raw_docs:
    #                 if '_id' in d and isinstance(d['_id'], ObjectId): d['_id'] = str(d['_id'])
    #                 # Convert date/datetime objects to ISO format strings for JSON serialization
    #                 if 'date' in d and isinstance(d['date'], (datetime.datetime, datetime.date)):
    #                     d['date'] = d['date'].isoformat()
    #                 retrieved_docs.append(d)
    #         except Exception as e:
    #             logger.exception("MongoDB raw query failed: %s", e)
    #     else:
    #         logger.info("Router chose VECTOR search. Querying Pinecone with: '%s'", payload)
    #         if self.vector_db: retrieved_docs = await self.vector_db.query_transactions(query_text=payload)

    #     logger.info("Found %d documents.", len(retrieved_docs))
    #     return retrieved_docs
    # In rag_pipeline.py - UPDATE THIS METHOD ONLY

    async def query(self, user_query: str) -> List[Dict[str, Any]]:
        """Hybrid routing with LangChain agent"""
        logger.info(f"Executing LangChain router agent for query: '{user_query}'")
        self._ensure_clients()
        
        # --- UPDATED LINE ---
        route = await self.router_agent.route_query(user_query)  # This now uses LangChain agent
        # --- END UPDATE ---
        
        query_type, payload = route.get("query_type"), route.get("payload")
        retrieved_docs: List[Dict[str, Any]] = []

        if query_type == "filter":
            logger.info(f"Router chose FILTER search. Payload: {payload}")
            try:
                processed_payload = _convert_date_filters(payload)
                logger.info(f"Querying MongoDB with: {processed_payload}")
                
                client = AsyncIOMotorClient(settings.MONGO_URI)
                db = client.get_default_database()
                collection_name = getattr(models.Transaction.Settings, 'name', 'transactions')
                
                raw_docs = await db[collection_name].find(processed_payload).to_list(length=None)  # No limit - get all matching transactions
                for d in raw_docs:
                    if '_id' in d and isinstance(d['_id'], ObjectId):
                        d['_id'] = str(d['_id'])
                    if 'date' in d and isinstance(d['date'], (datetime.datetime, datetime.date)):
                        d['date'] = d['date'].isoformat()
                    retrieved_docs.append(d)
            except Exception as e:
                logger.exception(f"MongoDB query failed: {e}")
        else:
            logger.info(f"Router chose VECTOR search: '{payload}'")
            if self.vector_db:
                retrieved_docs = await self.vector_db.query_transactions(query_text=payload)

        logger.info(f"Found {len(retrieved_docs)} documents.")
        return retrieved_docs


    async def query_with_pagination(self, user_query: str, limit: int = 50, skip: int = 0) -> Dict[str, Any]:
        """Query with pagination support for handling large result sets"""
        logger.info(f"Executing paginated query: '{user_query}', limit={limit}, skip={skip}")
        self._ensure_clients()
        
        route = await self.router_agent.route_query(user_query)
        query_type, payload = route.get("query_type"), route.get("payload")
        retrieved_docs: List[Dict[str, Any]] = []
        total_count = 0

        if query_type == "filter":
            logger.info(f"Router chose FILTER search. Payload: {payload}")
            try:
                processed_payload = _convert_date_filters(payload)
                logger.info(f"Querying MongoDB with: {processed_payload}")
                
                client = AsyncIOMotorClient(settings.MONGO_URI)
                db = client.get_default_database()
                collection_name = getattr(models.Transaction.Settings, 'name', 'transactions')
                
                # Get total count first
                total_count = await db[collection_name].count_documents(processed_payload)
                logger.info(f"Total matching documents: {total_count}")
                
                # Get paginated results
                raw_docs = await db[collection_name].find(processed_payload).skip(skip).limit(limit).to_list(length=limit)
                for d in raw_docs:
                    if '_id' in d and isinstance(d['_id'], ObjectId):
                        d['_id'] = str(d['_id'])
                    if 'date' in d and isinstance(d['date'], (datetime.datetime, datetime.date)):
                        d['date'] = d['date'].isoformat()
                    retrieved_docs.append(d)
            except Exception as e:
                logger.exception(f"MongoDB paginated query failed: {e}")
        else:
            logger.info(f"Router chose VECTOR search: '{payload}'")
            if self.vector_db:
                all_docs = await self.vector_db.query_transactions(query_text=payload, n_results=1000)
                total_count = len(all_docs)
                retrieved_docs = all_docs[skip:skip+limit]

        logger.info(f"Returning {len(retrieved_docs)} of {total_count} documents (skip={skip}, limit={limit})")
        return {
            "documents": retrieved_docs,
            "total_count": total_count,
            "returned_count": len(retrieved_docs),
            "has_more": (skip + len(retrieved_docs)) < total_count,
            "current_page": (skip // limit) + 1 if limit > 0 else 1
        }

    async def answer(self, user_query: str, retrieved_data: List[Dict]) -> str:
        """Generates a text answer, ensuring it never returns None."""
        self._ensure_clients()
        if self.chat_agent is None: return "Sorry, the chat service is currently unavailable."
        response_text = await self.chat_agent.generate_response(user_query, retrieved_data)
        if response_text is None:
            logger.error("FinancialChatAgent returned None, indicating a critical failure.")
            return "Sorry, a critical error occurred while generating a response."
        return response_text
