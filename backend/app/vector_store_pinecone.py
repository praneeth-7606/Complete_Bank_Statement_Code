"""
Pinecone Vector Store - Production-Ready Implementation
Handles vector storage and retrieval using Pinecone cloud service
"""
from typing import List, Dict, Optional
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai
import logging
from . import agents

logger = logging.getLogger(__name__)

class PineconeVectorStore:
    """Production-ready vector store using Pinecone"""
    
    def __init__(self, api_key: str, environment: str, index_name: str):
        """
        Initialize Pinecone vector store
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment/region (e.g., 'us-east-1')
            index_name: Name of the Pinecone index
        """
        logger.info(f"Initializing Pinecone vector store with index: {index_name}")
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.embedding_agent = agents.EmbeddingAgent()
        
        # Check if index exists, create if it doesn't
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        
        if index_name not in existing_indexes:
            logger.info(f"Creating new Pinecone index: {index_name}")
            self.pc.create_index(
                name=index_name,
                dimension=768,  # Google text-embedding-004 dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=environment
                )
            )
            logger.info(f"Pinecone index '{index_name}' created successfully")
        else:
            logger.info(f"Using existing Pinecone index: {index_name}")
        
        # Connect to the index
        self.index = self.pc.Index(index_name)
        logger.info(f"Connected to Pinecone index: {index_name}")
    
    async def add_transactions(self, transactions: List[Dict]):
        """
        Add transactions to Pinecone vector store with embeddings
        
        Args:
            transactions: List of transaction dictionaries
        """
        if not transactions:
            logger.warning("No transactions to add")
            return
        
        logger.info(f"Adding {len(transactions)} transactions to Pinecone")
        
        # Generate embeddings for all transactions
        embeddings = await self.embedding_agent.embed_documents(transactions)
        
        if not embeddings or len(embeddings) != len(transactions):
            logger.error("Embedding generation failed or mismatch in count")
            return
        
        # Prepare vectors for Pinecone
        vectors = []
        for txn, emb in zip(transactions, embeddings):
            # Prepare metadata (Pinecone supports str, int, float, bool)
            metadata = {}
            for key, value in txn.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value
                else:
                    # Convert complex types to string
                    metadata[key] = str(value)
            
            vectors.append({
                "id": str(txn["transaction_id"]),  # Ensure ID is string
                "values": emb,
                "metadata": metadata
            })
        
        # Upsert vectors in batches (Pinecone handles batching efficiently)
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            self.index.upsert(
                vectors=batch,
                namespace="transactions"  # Use namespace for organization
            )
            logger.info(f"Upserted batch {i//batch_size + 1}: {len(batch)} vectors")
        
        logger.info(f"Successfully added {len(vectors)} transactions to Pinecone")
    
    async def query_transactions(
        self,
        query_text: str,
        n_results: int = 7,
        where: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Query transactions using semantic search
        
        Args:
            query_text: The search query
            n_results: Number of results to return
            where: Optional metadata filter (Pinecone filter format)
        
        Returns:
            List of matching transaction metadata
        """
        if not query_text:
            logger.warning("Empty query text provided")
            return []
        
        logger.info(f"Querying Pinecone for: '{query_text}' (top {n_results} results)")
        
        # Generate embedding for query using the same model as EmbeddingAgent (768-dim, v1beta compatible)
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=query_text,
            task_type="retrieval_query",
            output_dimensionality=768
        )
        query_embedding = result['embedding']

        
        # Prepare query parameters
        query_params = {
            "vector": query_embedding,
            "top_k": n_results,
            "namespace": "transactions",
            "include_metadata": True
        }
        
        # Add filter if provided
        if where:
            query_params["filter"] = where
            logger.info(f"Applying filter: {where}")
        
        # Execute query
        try:
            results = self.index.query(**query_params)
            matches = [match.metadata for match in results.matches]
            logger.info(f"Found {len(matches)} matching transactions")
            return matches
        except Exception as e:
            logger.error(f"Pinecone query failed: {e}", exc_info=True)
            return []
    
    async def delete_transaction_vector(self, transaction_id: str):
        """
        Delete a single transaction vector from Pinecone
        
        Args:
            transaction_id: The ID of the transaction to delete
        """
        try:
            logger.info(f"Deleting vector for transaction_id: {transaction_id}")
            self.index.delete(ids=[str(transaction_id)], namespace="transactions")
            logger.info(f"Successfully deleted vector for transaction_id: {transaction_id}")
        except Exception as e:
            logger.error(f"Failed to delete vector for transaction_id {transaction_id}: {e}")

    async def delete_transactions_by_upload_id(self, upload_id: str):
        """
        Delete all transactions for a specific upload from Pinecone
        
        Args:
            upload_id: The upload ID to delete transactions for
        """
        try:
            logger.info(f"Deleting vectors for upload_id: {upload_id}")
            self.index.delete(filter={"upload_id": str(upload_id)}, namespace="transactions")
            logger.info(f"Successfully deleted vectors for upload_id: {upload_id}")
        except Exception as e:
            logger.error(f"Failed to delete vectors for upload_id {upload_id}: {e}")

    def get_index_stats(self) -> Dict:
        """Get statistics about the Pinecone index"""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}

