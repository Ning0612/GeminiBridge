"""
CLI Request Queue Manager
Limits concurrent Gemini CLI processes to prevent resource exhaustion
Implements queue with timeout and statistics tracking
"""

import asyncio
import time
import random
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from .config import get_config
from .logger import get_logger


# ============================================================================
# Logger
# ============================================================================

logger = get_logger("gemini_bridge")


@dataclass
class QueueStats:
    """Queue statistics"""
    active_requests: int
    queued_requests: int
    total_processed: int
    average_wait_time_ms: int
    max_concurrent: int


class CLIQueueManager:
    """
    Manages concurrent CLI execution with queue and timeout
    Matches Node.js CLIQueueManager behavior
    """

    def __init__(self, max_concurrent: int = 5, queue_timeout: int = 30, min_request_gap_ms: int = 500):
        """
        Initialize queue manager

        Args:
            max_concurrent: Maximum concurrent CLI processes
            queue_timeout: Queue timeout in seconds
            min_request_gap_ms: Minimum gap between requests in milliseconds
        """
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._queue_timeout = queue_timeout
        self._min_request_gap_ms = min_request_gap_ms

        # Statistics
        self._active_requests = 0
        self._total_processed = 0
        self._total_wait_time_ms = 0
        self._queue: list[tuple[str, float]] = []  # (request_id, enqueue_time)

        # Track last request completion time
        self._last_request_completion_time: float = 0.0

        # Lock for statistics updates and request timing
        self._stats_lock = asyncio.Lock()

    async def execute(
        self,
        request_id: str,
        operation: Callable[[], Coroutine[Any, Any, Any]]
    ) -> Any:
        """
        Execute a CLI operation with concurrency control

        Args:
            request_id: Unique request identifier
            operation: Async operation to execute

        Returns:
            Result of the operation

        Raises:
            TimeoutError: If queued for too long
        """
        enqueue_time = time.time()

        # Add to queue for tracking
        async with self._stats_lock:
            self._queue.append((request_id, enqueue_time))

        try:
            # Add small random delay (10-50ms) before acquiring semaphore
            # This spreads out concurrent request starts and reduces Docker container name conflicts
            random_delay_ms = random.uniform(10, 50)
            await asyncio.sleep(random_delay_ms / 1000)
            
            logger.debug(
                "Pre-semaphore random delay applied",
                extra={"extra": {"request_id": request_id, "delay_ms": round(random_delay_ms, 1)}}
            )
            
            # Try to acquire semaphore with timeout
            try:
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=self._queue_timeout
                )
            except asyncio.TimeoutError:
                # Remove from queue
                async with self._stats_lock:
                    self._queue = [(rid, t) for rid, t in self._queue if rid != request_id]

                raise TimeoutError(
                    f"Request timeout: queued for {self._queue_timeout}s"
                )

            # Enforce minimum gap between requests
            async with self._stats_lock:
                if self._last_request_completion_time > 0:
                    elapsed_ms = (time.time() - self._last_request_completion_time) * 1000
                    if elapsed_ms < self._min_request_gap_ms:
                        wait_ms = self._min_request_gap_ms - elapsed_ms
                        logger.debug(
                            "Enforcing request gap delay",
                            extra={"extra": {"request_id": request_id, "wait_ms": int(wait_ms)}}
                        )
                        # Release lock before sleeping
                        await asyncio.sleep(wait_ms / 1000)

            # Remove from queue and update stats
            wait_time_ms = int((time.time() - enqueue_time) * 1000)

            async with self._stats_lock:
                self._queue = [(rid, t) for rid, t in self._queue if rid != request_id]
                self._active_requests += 1
                self._total_wait_time_ms += wait_time_ms

            if wait_time_ms > 100:  # Log if waited more than 100ms
                logger.info(
                    "Request dequeued after wait",
                    extra={"extra": {"request_id": request_id, "wait_time_ms": wait_time_ms}}
                )

            # Execute operation
            try:
                result = await operation()
                return result
            finally:
                # Update stats, record completion time, and release semaphore
                async with self._stats_lock:
                    self._active_requests -= 1
                    self._total_processed += 1
                    self._last_request_completion_time = time.time()

                self._semaphore.release()

        except Exception:
            # Ensure we remove from queue on any error
            async with self._stats_lock:
                self._queue = [(rid, t) for rid, t in self._queue if rid != request_id]
            raise

    async def get_stats(self) -> QueueStats:
        """
        Get current queue statistics

        Returns:
            QueueStats with current state
        """
        async with self._stats_lock:
            avg_wait_time = (
                self._total_wait_time_ms // self._total_processed
                if self._total_processed > 0
                else 0
            )

            return QueueStats(
                active_requests=self._active_requests,
                queued_requests=len(self._queue),
                total_processed=self._total_processed,
                average_wait_time_ms=avg_wait_time,
                max_concurrent=self._max_concurrent
            )

    def set_max_concurrent(self, max_concurrent: int) -> None:
        """
        Update max concurrent limit
        Note: This recreates the semaphore, may cause temporary disruption

        Args:
            max_concurrent: New maximum concurrent processes
        """
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(
            "Max concurrent CLI processes updated",
            extra={"extra": {"max_concurrent": max_concurrent}}
        )


# Singleton instance
_cli_queue: CLIQueueManager | None = None


def get_cli_queue() -> CLIQueueManager:
    """Get singleton CLI queue manager instance"""
    global _cli_queue
    if _cli_queue is None:
        config = get_config()
        _cli_queue = CLIQueueManager(
            max_concurrent=config.max_concurrent_requests,
            queue_timeout=config.queue_timeout
        )
    return _cli_queue
