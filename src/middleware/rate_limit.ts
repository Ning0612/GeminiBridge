/**
 * Rate limiting middleware
 * Implements sliding window rate limiter
 */

import { Request, Response, NextFunction } from 'express';
import { config } from '../config';
import { handleRateLimitError, sendError } from '../utils/error_handler';
import { logger } from '../utils/logger';

interface RequestLog {
  timestamp: number;
}

// In-memory store for request logs (IP -> timestamps)
const requestLogs = new Map<string, RequestLog[]>();

/**
 * Get client IP address (supports reverse proxy)
 */
function getClientIP(req: Request): string {
  // Check X-Forwarded-For header (if behind reverse proxy)
  const forwarded = req.headers['x-forwarded-for'];
  if (forwarded && typeof forwarded === 'string') {
    // Take the first IP in the list (original client IP)
    return forwarded.split(',')[0].trim();
  }

  // Fallback to req.ip
  return req.ip || req.socket.remoteAddress || 'unknown';
}

/**
 * Monitor memory usage of rate limit store
 */
function checkMemoryUsage(): void {
  const entryCount = requestLogs.size;

  if (entryCount > 10000) {
    const memoryMB = process.memoryUsage().heapUsed / 1024 / 1024;
    logger.warn('Rate limit store has many entries', {
      entryCount,
      memoryUsageMB: memoryMB.toFixed(2)
    });
  }
}

/**
 * Clean up old request logs
 */
function cleanupOldLogs(ip: string, windowMs: number): void {
  const logs = requestLogs.get(ip);
  if (!logs) {
    return;
  }

  const now = Date.now();
  const validLogs = logs.filter((log) => now - log.timestamp < windowMs);

  if (validLogs.length === 0) {
    requestLogs.delete(ip);
  } else {
    requestLogs.set(ip, validLogs);
  }
}

/**
 * Rate limiting middleware
 */
export function rateLimitMiddleware(req: Request, res: Response, next: NextFunction): void {
  const ip = getClientIP(req);  // Use improved IP detection
  const { maxRequests, windowMs } = config.rateLimit;

  // Clean up old logs
  cleanupOldLogs(ip, windowMs);

  // Get current logs for this IP
  const logs = requestLogs.get(ip) || [];

  // Check if rate limit exceeded
  if (logs.length >= maxRequests) {
    logger.warn('Rate limit exceeded', {
      ip,
      path: req.path,
      requests: logs.length,
      limit: maxRequests,
    });

    sendError(res, handleRateLimitError());
    return;
  }

  // Add current request to logs
  logs.push({ timestamp: Date.now() });
  requestLogs.set(ip, logs);

  next();
}

/**
 * Cleanup interval to prevent memory leaks
 */
setInterval(() => {
  const now = Date.now();
  const windowMs = config.rateLimit.windowMs;

  for (const [ip, logs] of requestLogs.entries()) {
    const validLogs = logs.filter((log) => now - log.timestamp < windowMs);

    if (validLogs.length === 0) {
      requestLogs.delete(ip);
    } else {
      requestLogs.set(ip, validLogs);
    }
  }

  // Monitor memory usage
  checkMemoryUsage();
}, 60000); // Run cleanup every minute
