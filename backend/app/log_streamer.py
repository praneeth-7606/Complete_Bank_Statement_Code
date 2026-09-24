# app/log_streamer.py - Real-time log streaming for frontend

import asyncio
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class LogStreamer:
    """
    Manages real-time log streaming to frontend using Server-Sent Events (SSE).
    Each upload gets its own queue for logs.

    Multi-statement processing creates child IDs like "{parent}_0". Child logs
    are automatically fanned into the parent queue when a parent exists so the
    browser (subscribed only to the parent) still sees per-file progress.
    """
    
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.active_streams: Dict[str, bool] = {}
        # child_id -> parent_id (for fan-in)
        self.child_parents: Dict[str, str] = {}
    
    def create_stream(self, upload_id: str) -> asyncio.Queue:
        """Create a new log stream for an upload"""
        if upload_id in self.queues:
            logger.warning(f"Stream already exists for upload_id: {upload_id}")
            return self.queues[upload_id]
        
        queue = asyncio.Queue(maxsize=200)
        self.queues[upload_id] = queue
        self.active_streams[upload_id] = True
        logger.info(f"Created log stream for upload_id: {upload_id}")
        return queue

    def create_child_stream(self, child_id: str, parent_id: str) -> asyncio.Queue:
        """Register a child stream that fans logs into parent_id."""
        queue = self.create_stream(child_id)
        self.child_parents[child_id] = parent_id
        return queue

    def _resolve_target(self, upload_id: str) -> Optional[str]:
        """Map a child stream id to its parent when the parent is active."""
        parent = self.child_parents.get(upload_id)
        if parent and self.active_streams.get(parent, False) and parent in self.queues:
            return parent
        if upload_id in self.queues and self.active_streams.get(upload_id, False):
            return upload_id
        # Child may not be registered yet - infer parent from "{parent}_{n}" pattern
        if "_" in upload_id:
            maybe_parent, _, suffix = upload_id.rpartition("_")
            if suffix.isdigit() and self.active_streams.get(maybe_parent, False) and maybe_parent in self.queues:
                self.child_parents[upload_id] = maybe_parent
                return maybe_parent
        return None
    
    async def add_log(self, upload_id: str, message: str, level: str = "info", progress: Optional[int] = None):
        """
        Add a log message to the stream.
        
        Args:
            upload_id: Upload ID (child IDs fan into their parent)
            message: Log message
            level: Log level (info, success, warning, error, complete)
            progress: Optional progress percentage (0-100)
        """
        target = self._resolve_target(upload_id)
        if target is None:
            # Auto-create orphan child as standalone so logs are never dropped
            # when parent is not yet active.
            if upload_id not in self.queues:
                self.create_stream(upload_id)
            target = upload_id
            if not self.active_streams.get(upload_id, False):
                logger.debug(f"Stream closed for upload_id: {upload_id}")
                return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "level": level,
            "progress": progress
        }
        
        try:
            await self.queues[target].put(log_entry)
            # LOG TO TERMINAL as INFO so the user can see progress in the terminal
            logger.info(f"   [LOG] [{upload_id}->{target}] {message}")
        except asyncio.QueueFull:
            logger.warning(f"Queue full for upload_id: {target}")
    
    async def get_logs(self, upload_id: str):
        """
        Generator that yields logs for SSE streaming.
        
        Usage:
            async for log in log_streamer.get_logs(upload_id):
                yield f"data: {json.dumps(log)}\\n\\n"
        """
        if upload_id not in self.queues:
            logger.error(f"No stream found for upload_id: {upload_id}")
            return
        
        queue = self.queues[upload_id]
        
        try:
            while self.active_streams.get(upload_id, False):
                try:
                    # Wait for log with timeout
                    log_entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield log_entry
                    
                    # Check if this is the completion message
                    if log_entry.get("level") == "complete":
                        break
                    # Terminal error at 100 also ends the stream so the UI stops.
                    # Intermediate per-file failures use progress=None and must not
                    # kill the parent batch stream early.
                    if log_entry.get("level") == "error" and (
                        log_entry.get("progress") is not None
                        and int(log_entry.get("progress") or 0) >= 100
                    ):
                        break
                        
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield {"timestamp": "", "message": "ping", "level": "ping"}
                    
        except Exception as e:
            logger.error(f"Error streaming logs for {upload_id}: {e}")
        finally:
            self.close_stream(upload_id)
    
    def close_stream(self, upload_id: str):
        """Close and cleanup a log stream"""
        if upload_id in self.active_streams:
            self.active_streams[upload_id] = False
        
        if upload_id in self.queues:
            # Clear remaining items
            while not self.queues[upload_id].empty():
                try:
                    self.queues[upload_id].get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            del self.queues[upload_id]
        
        # Drop child registrations pointing at this id
        stale = [c for c, p in self.child_parents.items() if p == upload_id or c == upload_id]
        for child in stale:
            self.child_parents.pop(child, None)
        
        logger.info(f"Closed log stream for upload_id: {upload_id}")
    
    def is_active(self, upload_id: str) -> bool:
        """Check if a stream is active"""
        return self.active_streams.get(upload_id, False)


# Global instance
log_streamer = LogStreamer()
