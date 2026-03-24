"""
Parallel Processing Infrastructure for High-Performance Transaction Processing

This module implements a hybrid mini-batch + parallel processing system that:
1. Maintains accuracy by using focused prompts (mini-batches of 3-5 transactions)
2. Achieves speed by processing multiple mini-batches concurrently
3. Provides graceful fallback to individual processing on errors
4. Handles rate limiting and resource management
"""

import asyncio
import logging
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ParallelProcessor:
    """
    Manages parallel processing of transactions with configurable mini-batch sizes.
    
    Key Features:
    - Mini-batch processing (2-5 transactions per AI call)
    - Concurrent execution of multiple mini-batches
    - Automatic fallback on errors
    - Progress tracking
    - Rate limit handling
    """
    
    def __init__(
        self, 
        mini_batch_size: int = 5,
        max_concurrent_workers: int = 10,
        retry_on_failure: bool = True
    ):
        """
        Initialize the parallel processor.
        
        Args:
            mini_batch_size: Number of transactions per AI call (2-5 recommended)
            max_concurrent_workers: Maximum parallel workers (adjust based on API limits)
            retry_on_failure: Whether to retry failed mini-batches individually
        """
        self.mini_batch_size = mini_batch_size
        self.max_concurrent_workers = max_concurrent_workers
        self.retry_on_failure = retry_on_failure
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "start_time": None,
            "end_time": None
        }
    
    def _create_mini_batches(self, items: List[Any]) -> List[List[Any]]:
        """
        Split items into mini-batches for processing.
        
        Args:
            items: List of items to batch
            
        Returns:
            List of mini-batches
        """
        batches = []
        for i in range(0, len(items), self.mini_batch_size):
            batch = items[i:i + self.mini_batch_size]
            batches.append(batch)
        
        logger.info(f"Created {len(batches)} mini-batches from {len(items)} items "
                   f"(batch size: {self.mini_batch_size})")
        return batches
    
    async def _process_mini_batch(
        self,
        batch: List[Any],
        batch_index: int,
        processor_func: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a single mini-batch.
        
        Args:
            batch: Mini-batch of items to process
            batch_index: Index of this batch (for logging)
            processor_func: Async function to process the batch
            **kwargs: Additional arguments for processor_func
            
        Returns:
            Dict with 'success', 'results', and 'error' keys
        """
        try:
            logger.debug(f"Processing mini-batch {batch_index + 1} with {len(batch)} items...")
            
            # Call the processor function
            results = await processor_func(batch, **kwargs)
            
            logger.debug(f"Mini-batch {batch_index + 1} completed successfully")
            return {
                "success": True,
                "results": results if results else [],
                "error": None,
                "batch_index": batch_index,
                "batch_size": len(batch)
            }
            
        except Exception as e:
            logger.error(f"Mini-batch {batch_index + 1} failed: {e}", exc_info=True)
            return {
                "success": False,
                "results": [],
                "error": str(e),
                "batch_index": batch_index,
                "batch_size": len(batch),
                "original_batch": batch  # Store for retry
            }
    
    async def _retry_failed_batch_individually(
        self,
        batch: List[Any],
        processor_func: Callable,
        **kwargs
    ) -> List[Any]:
        """
        Retry a failed mini-batch by processing items individually.
        
        Args:
            batch: Failed mini-batch
            processor_func: Async function to process individual items
            **kwargs: Additional arguments for processor_func
            
        Returns:
            List of successfully processed results
        """
        logger.info(f"Retrying {len(batch)} items individually...")
        results = []
        
        for i, item in enumerate(batch):
            try:
                # Process single item
                result = await processor_func([item], **kwargs)
                if result:
                    results.extend(result if isinstance(result, list) else [result])
                    self.stats["retried"] += 1
                    logger.debug(f"Individual retry {i + 1}/{len(batch)} succeeded")
            except Exception as e:
                logger.warning(f"Individual retry {i + 1}/{len(batch)} failed: {e}")
                self.stats["failed"] += 1
        
        return results
    
    async def process_in_parallel(
        self,
        items: List[Any],
        processor_func: Callable,
        **kwargs
    ) -> List[Any]:
        """
        Process items in parallel using mini-batches.
        
        This is the main entry point for parallel processing. It:
        1. Creates mini-batches
        2. Processes them concurrently (with worker limit)
        3. Handles failures with optional retry
        4. Returns combined results
        
        Args:
            items: List of items to process
            processor_func: Async function that processes a batch
            **kwargs: Additional arguments for processor_func
            
        Returns:
            List of all successfully processed results
        """
        if not items:
            return []
        
        self.stats["start_time"] = datetime.now()
        self.stats["total_processed"] = len(items)
        
        logger.info(f"Starting parallel processing of {len(items)} items...")
        logger.info(f"Config: mini_batch_size={self.mini_batch_size}, "
                   f"max_workers={self.max_concurrent_workers}")
        
        # Create mini-batches
        mini_batches = self._create_mini_batches(items)
        
        # Process batches with concurrency limit
        all_results = []
        failed_batches = []
        
        # Use semaphore to limit concurrent workers
        semaphore = asyncio.Semaphore(self.max_concurrent_workers)
        
        async def process_with_semaphore(batch, index):
            async with semaphore:
                return await self._process_mini_batch(
                    batch, index, processor_func, **kwargs
                )
        
        # Create all tasks
        tasks = [
            process_with_semaphore(batch, i)
            for i, batch in enumerate(mini_batches)
        ]
        
        # Wait for all to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results and identify failures
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Task raised exception: {result}")
                self.stats["failed"] += 1
                continue
            
            if result["success"]:
                all_results.extend(result["results"])
                self.stats["successful"] += len(result["results"])
            else:
                failed_batches.append(result)
        
        # Retry failed batches individually if enabled
        if self.retry_on_failure and failed_batches:
            logger.info(f"Retrying {len(failed_batches)} failed mini-batches individually...")
            
            for failed_batch in failed_batches:
                retry_results = await self._retry_failed_batch_individually(
                    failed_batch["original_batch"],
                    processor_func,
                    **kwargs
                )
                all_results.extend(retry_results)
        
        self.stats["end_time"] = datetime.now()
        elapsed = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        logger.info(f"Parallel processing complete!")
        logger.info(f"  Total items: {self.stats['total_processed']}")
        logger.info(f"  Successful: {self.stats['successful']}")
        logger.info(f"  Retried: {self.stats['retried']}")
        logger.info(f"  Failed: {self.stats['failed']}")
        logger.info(f"  Time taken: {elapsed:.2f}s")
        logger.info(f"  Throughput: {self.stats['total_processed']/elapsed:.1f} items/sec")
        
        return all_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.stats.copy()


class PipelineStage:
    """
    Represents a stage in a processing pipeline that can run in parallel with others.
    """
    
    def __init__(self, name: str, func: Callable, depends_on: Optional[List[str]] = None):
        """
        Initialize a pipeline stage.
        
        Args:
            name: Unique name for this stage
            func: Async function to execute
            depends_on: List of stage names this depends on (must complete first)
        """
        self.name = name
        self.func = func
        self.depends_on = depends_on or []
        self.result = None
        self.completed = False
        self.error = None
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute this stage with the given context.
        
        Args:
            context: Shared context dictionary with results from previous stages
            
        Returns:
            Result of the stage execution
        """
        try:
            logger.info(f"Stage '{self.name}' starting...")
            self.result = await self.func(context)
            self.completed = True
            logger.info(f"Stage '{self.name}' completed successfully")
            return self.result
        except Exception as e:
            self.error = str(e)
            logger.error(f"Stage '{self.name}' failed: {e}", exc_info=True)
            raise


class ParallelPipeline:
    """
    Executes a pipeline of stages with maximum parallelism based on dependencies.
    
    Stages without dependencies run immediately.
    Dependent stages wait for their prerequisites.
    """
    
    def __init__(self):
        self.stages: List[PipelineStage] = []
    
    def add_stage(self, name: str, func: Callable, depends_on: Optional[List[str]] = None):
        """
        Add a stage to the pipeline.
        
        Args:
            name: Unique name for this stage
            func: Async function to execute (receives context dict as argument)
            depends_on: List of stage names this depends on
        """
        stage = PipelineStage(name, func, depends_on)
        self.stages.append(stage)
        logger.debug(f"Added pipeline stage '{name}' with dependencies: {depends_on or 'none'}")
    
    async def execute(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the entire pipeline with maximum parallelism.
        
        Args:
            initial_context: Initial context to pass to stages
            
        Returns:
            Final context with all stage results
        """
        context = initial_context or {}
        completed_stages = set()
        
        logger.info(f"Executing pipeline with {len(self.stages)} stages...")
        
        while len(completed_stages) < len(self.stages):
            # Find stages ready to execute (dependencies met)
            ready_stages = [
                stage for stage in self.stages
                if not stage.completed
                and all(dep in completed_stages for dep in stage.depends_on)
            ]
            
            if not ready_stages:
                incomplete = [s.name for s in self.stages if not s.completed]
                raise RuntimeError(f"Pipeline deadlock! Incomplete stages: {incomplete}")
            
            logger.info(f"Executing {len(ready_stages)} parallel stages: "
                       f"{[s.name for s in ready_stages]}")
            
            # Execute all ready stages in parallel
            tasks = [stage.execute(context) for stage in ready_stages]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update context and mark completed
            for stage, result in zip(ready_stages, results):
                if isinstance(result, Exception):
                    raise RuntimeError(f"Stage '{stage.name}' failed: {result}")
                
                context[stage.name] = result
                completed_stages.add(stage.name)
        
        logger.info("Pipeline execution complete!")
        return context


# Utility functions for common patterns

async def parallel_map(
    items: List[Any],
    async_func: Callable,
    max_concurrent: int = 10
) -> List[Any]:
    """
    Simple parallel map over items with concurrency limit.
    
    Args:
        items: Items to process
        async_func: Async function to apply to each item
        max_concurrent: Maximum concurrent executions
        
    Returns:
        List of results in original order
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_item(item):
        async with semaphore:
            return await async_func(item)
    
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)


async def parallel_batch_map(
    items: List[Any],
    async_batch_func: Callable,
    batch_size: int = 5,
    max_concurrent_batches: int = 10
) -> List[Any]:
    """
    Parallel processing with automatic batching.
    
    Args:
        items: Items to process
        async_batch_func: Async function that processes a batch
        batch_size: Items per batch
        max_concurrent_batches: Maximum concurrent batch executions
        
    Returns:
        Flattened list of all results
    """
    processor = ParallelProcessor(
        mini_batch_size=batch_size,
        max_concurrent_workers=max_concurrent_batches,
        retry_on_failure=True
    )
    
    return await processor.process_in_parallel(items, async_batch_func)

