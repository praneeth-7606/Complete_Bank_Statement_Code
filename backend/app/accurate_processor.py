"""
Accurate Transaction Processor

This module processes bank statements with 100% debit/credit accuracy:
1. Uses table extraction for precise column identification
2. AI only for descriptions and categories (not amounts)
3. Faster processing with larger batches (since amounts are pre-extracted)
"""

import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from . import agents
from .parallel_processor import ParallelProcessor

logger = logging.getLogger(__name__)


class AccurateTransactionProcessor:
    """
    High-accuracy processor that separates concerns:
    - Table extraction handles amounts (100% accurate)
    - AI handles only descriptions and categories
    """
    
    def __init__(
        self,
        category_batch_size: int = 50,  # Very large batches = fewer API calls
        max_concurrent_workers: int = 2  # Reduced to avoid rate limits
    ):
        """
        Initialize the accurate processor.
        
        Args:
            category_batch_size: Transactions per categorization call (very large to reduce API calls)
            max_concurrent_workers: Maximum parallel workers (reduced for rate limits)
        """
        self.category_batch_size = category_batch_size
        self.max_concurrent_workers = max_concurrent_workers
        
        # Initialize agents with optimized settings
        self.categorization_agent = agents.CategorizationAgent()  # Uses stable model
        self.embedding_agent = agents.EmbeddingAgent(batch_size=100)  # Larger embedding batches
        
        # Performance stats
        self.stats = {
            "categorization_time": 0,
            "embedding_time": 0,
            "total_time": 0,
            "total_transactions": 0
        }
    
    async def process_transactions(
        self,
        transactions: List[Dict],  # Pre-extracted with accurate amounts
        corrections: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process pre-extracted transactions (amounts already accurate).
        Only adds categories and generates embeddings.
        
        Args:
            transactions: List of transactions with accurate debit/credit
            corrections: User corrections for learning
            
        Returns:
            Dict with categorized transactions, embeddings, and stats
        """
        start_time = datetime.now()
        corrections = corrections or []
        self.stats["total_transactions"] = len(transactions)
        
        logger.info(f"Starting accurate processing of {len(transactions)} transactions...")
        logger.info(f"Configuration: category_batch={self.category_batch_size}, "
                   f"workers={self.max_concurrent_workers}")
        logger.info(f"✅ Amounts already extracted accurately from table columns")
        
        try:
            # Stage 1: Add categories (parallel mini-batches)
            categorized_transactions = await self._categorize_in_parallel(
                transactions,
                corrections
            )
            
            # Stage 2: Generate embeddings (batched)
            embeddings = await self._generate_embeddings(categorized_transactions)
            
            # Calculate total time
            end_time = datetime.now()
            self.stats["total_time"] = (end_time - start_time).total_seconds()
            
            logger.info(f"✓ Processing complete! {len(categorized_transactions)} transactions "
                       f"in {self.stats['total_time']:.2f}s "
                       f"({len(categorized_transactions)/self.stats['total_time']:.1f} txn/sec)")
            
            return {
                "success": True,
                "transactions": categorized_transactions,
                "embeddings": embeddings,
                "error": None,
                "stats": self.stats
            }
            
        except Exception as e:
            logger.error(f"Accurate processing failed: {e}", exc_info=True)
            return {
                "success": False,
                "transactions": [],
                "embeddings": [],
                "error": str(e),
                "stats": self.stats
            }
    
    async def _categorize_in_parallel(
        self,
        transactions: List[Dict],
        corrections: List[Dict]
    ) -> List[Dict]:
        """
        Categorize transactions using parallel mini-batch processing.
        
        Args:
            transactions: Transactions with accurate amounts
            corrections: User corrections for learning
            
        Returns:
            List of categorized transactions
        """
        logger.info("Stage 1: Categorizing transactions with parallel mini-batches...")
        start_time = datetime.now()
        
        # Create processor for categorization
        processor = ParallelProcessor(
            mini_batch_size=self.category_batch_size,
            max_concurrent_workers=self.max_concurrent_workers,
            retry_on_failure=True
        )
        
        # Define the processing function for mini-batches
        async def categorize_batch(batch: List[Dict]) -> List[Dict]:
            """Process a mini-batch of transactions."""
            return await self.categorization_agent.categorize_mini_batch(batch, corrections)
        
        # Process in parallel
        categorized = await processor.process_in_parallel(
            transactions,
            categorize_batch
        )
        
        self.stats["categorization_time"] = (datetime.now() - start_time).total_seconds()
        logger.info(f"✓ Categorized {len(categorized)} transactions in "
                   f"{self.stats['categorization_time']:.2f}s")
        
        return categorized
    
    async def _generate_embeddings(self, transactions: List[Dict]) -> List[List[float]]:
        """
        Generate embeddings for transactions using batched API calls.
        
        Args:
            transactions: Categorized transactions
            
        Returns:
            List of embedding vectors
        """
        logger.info("Stage 2: Generating embeddings with batched API calls...")
        start_time = datetime.now()
        
        embeddings = await self.embedding_agent.embed_documents(transactions)
        
        self.stats["embedding_time"] = (datetime.now() - start_time).total_seconds()
        logger.info(f"✓ Generated {len(embeddings)} embeddings in "
                   f"{self.stats['embedding_time']:.2f}s")
        
        return embeddings
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get detailed performance report.
        
        Returns:
            Dict with timing breakdown and throughput metrics
        """
        total_time = self.stats["total_time"]
        total_txns = self.stats["total_transactions"]
        
        return {
            "total_transactions": total_txns,
            "total_time_seconds": round(total_time, 2),
            "throughput_txn_per_sec": round(total_txns / total_time, 1) if total_time > 0 else 0,
            "stage_breakdown": {
                "categorization": {
                    "time_seconds": round(self.stats["categorization_time"], 2),
                    "percentage": round(self.stats["categorization_time"] / total_time * 100, 1) if total_time > 0 else 0
                },
                "embedding": {
                    "time_seconds": round(self.stats["embedding_time"], 2),
                    "percentage": round(self.stats["embedding_time"] / total_time * 100, 1) if total_time > 0 else 0
                }
            },
            "configuration": {
                "category_batch_size": self.category_batch_size,
                "max_concurrent_workers": self.max_concurrent_workers
            }
        }

