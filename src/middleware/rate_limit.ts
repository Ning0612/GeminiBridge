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
  const ip = req.ip || 'unknown';
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
}, 60000); // Run cleanup every minute
