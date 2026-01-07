/**
 * Request logger middleware
 * Attaches request context and logs requests
 */

import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { RequestContext } from '../types';
import { logger } from '../utils/logger';

// Extend Express Request to include context
declare global {
  namespace Express {
    interface Request {
      context?: RequestContext;
    }
  }
}

/**
 * Request logger middleware
 */
export function requestLoggerMiddleware(req: Request, res: Response, next: NextFunction): void {
  const requestId = uuidv4();
  const clientIp = req.ip || 'unknown';
  const userAgent = req.headers['user-agent'] || 'unknown';

  // Attach context to request
  req.context = {
    requestId,
    clientIp,
    userAgent,
    timestamp: new Date(),
  };

  logger.info('Incoming request', {
    requestId,
    method: req.method,
    path: req.path,
    ip: clientIp,
    userAgent,
  });

  // Log response when finished
  res.on('finish', () => {
    logger.info('Response sent', {
      requestId,
      statusCode: res.statusCode,
      path: req.path,
    });
  });

  next();
}
