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
    """
    
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.active_streams: Dict[str, bool] = {}
    
    def create_stream(self, upload_id: str) -> asyncio.Queue:
        """Create a new log stream for an upload"""
        if upload_id in self.queues:
            logger.warning(f"Stream already exists for upload_id: {upload_id}")
            return self.queues[upload_id]
        
        queue = asyncio.Queue(maxsize=100)
        self.queues[upload_id] = queue
        self.active_streams[upload_id] = True
        logger.info(f"Created log stream for upload_id: {upload_id}")
        return queue
    
    async def add_log(self, upload_id: str, message: str, level: str = "info", progress: Optional[int] = None):
        """
        Add a log message to the stream.
        
        Args:
            upload_id: Upload ID
            message: Log message
            level: Log level (info, success, warning, error)
            progress: Optional progress percentage (0-100)
        """
        if upload_id not in self.queues:
            logger.warning(f"No stream found for upload_id: {upload_id}")
            return
        
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
            await self.queues[upload_id].put(log_entry)
            # LOG TO TERMINAL as INFO so the user can see progress in the terminal
            logger.info(f"   [LOG] [{upload_id}] {message}")
        except asyncio.QueueFull:
            logger.warning(f"Queue full for upload_id: {upload_id}")
    
    async def get_logs(self, upload_id: str):
        """
        Generator that yields logs for SSE streaming.
        
        Usage:
            async for log in log_streamer.get_logs(upload_id):
                yield f"data: {json.dumps(log)}\n\n"
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
        
        logger.info(f"Closed log stream for upload_id: {upload_id}")
    
    def is_active(self, upload_id: str) -> bool:
        """Check if a stream is active"""
        return self.active_streams.get(upload_id, False)


# Global instance
log_streamer = LogStreamer()
