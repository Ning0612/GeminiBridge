/**
 * CLI Request Queue Manager
 * Limits concurrent Gemini CLI processes to prevent resource exhaustion
 */

import { logger } from './logger';
import { EventEmitter } from 'events';

interface QueuedRequest {
    id: string;
    timestamp: number;
    resolve: (value: any) => void;
    reject: (error: Error) => void;
}

interface QueueStats {
    activeRequests: number;
    queuedRequests: number;
    totalProcessed: number;
    averageWaitTime: number;
    maxConcurrent: number;
}

class CLIQueueManager extends EventEmitter {
    private activeRequests = 0;
    private queue: QueuedRequest[] = [];
    private maxConcurrent: number;
    private totalProcessed = 0;
    private totalWaitTime = 0;
    private queueTimeout: number;

    constructor(maxConcurrent: number = 5, queueTimeout: number = 30000) {
        super();
        this.maxConcurrent = maxConcurrent;
        this.queueTimeout = queueTimeout;
    }

    /**
     * Execute a CLI operation with concurrency control
     */
    async execute<T>(requestId: string, operation: () => Promise<T>): Promise<T> {
        // Check if we can execute immediately
        if (this.activeRequests < this.maxConcurrent) {
            return this.executeImmediate(requestId, operation);
        }

        // Need to queue
        logger.info('Request queued due to concurrency limit', {
            requestId,
            activeRequests: this.activeRequests,
            queueLength: this.queue.length,
            maxConcurrent: this.maxConcurrent,
        });

        return this.enqueue(requestId, operation);
    }

    /**
     * Execute immediately
     */
    private async executeImmediate<T>(_requestId: string, operation: () => Promise<T>): Promise<T> {
        this.activeRequests++;
        this.emit('active-change', this.activeRequests);

        try {
            const result = await operation();
            return result;
        } finally {
            this.activeRequests--;
            this.totalProcessed++;
            this.emit('active-change', this.activeRequests);
            this.processQueue();
        }
    }

    /**
     * Add to queue
     */
    private enqueue<T>(requestId: string, operation: () => Promise<T>): Promise<T> {
        return new Promise((resolve, reject) => {
            const queueEntry: QueuedRequest = {
                id: requestId,
                timestamp: Date.now(),
                resolve: async () => {
                    const waitTime = Date.now() - queueEntry.timestamp;
                    this.totalWaitTime += waitTime;

                    logger.info('Request dequeued', {
                        requestId,
                        waitTimeMs: waitTime,
                        activeRequests: this.activeRequests,
                    });

                    try {
                        const result = await this.executeImmediate(requestId, operation);
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                },
                reject,
            };

            this.queue.push(queueEntry);

            // Set timeout
            setTimeout(() => {
                const index = this.queue.findIndex(q => q.id === requestId);
                if (index !== -1) {
                    this.queue.splice(index, 1);
                    reject(new Error(`Request timeout: queued for ${this.queueTimeout}ms`));
                    logger.warn('Request timeout in queue', {
                        requestId,
                        queueTimeMs: this.queueTimeout,
                    });
                }
            }, this.queueTimeout);
        });
    }

    /**
     * Process queue
     */
    private processQueue(): void {
        while (this.queue.length > 0 && this.activeRequests < this.maxConcurrent) {
            const queueEntry = this.queue.shift();
            if (queueEntry) {
                queueEntry.resolve(undefined);
            }
        }
    }

    /**
     * Get current statistics
     */
    getStats(): QueueStats {
        return {
            activeRequests: this.activeRequests,
            queuedRequests: this.queue.length,
            totalProcessed: this.totalProcessed,
            averageWaitTime: this.totalProcessed > 0
                ? Math.round(this.totalWaitTime / this.totalProcessed)
                : 0,
            maxConcurrent: this.maxConcurrent,
        };
    }

    /**
     * Update max concurrent limit
     */
    setMaxConcurrent(max: number): void {
        this.maxConcurrent = max;
        logger.info('Max concurrent CLI processes updated', { maxConcurrent: max });
        this.processQueue();
    }
}

// Export singleton
export const cliQueue = new CLIQueueManager(
    parseInt(process.env.MAX_CONCURRENT_REQUESTS || '5', 10),
    parseInt(process.env.QUEUE_TIMEOUT || '30000', 10)
);
