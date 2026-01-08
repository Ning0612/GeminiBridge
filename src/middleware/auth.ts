/**
 * Authentication middleware
 * Validates Bearer token from Authorization header
 */

import { Request, Response, NextFunction } from 'express';
import { timingSafeEqual } from 'crypto';
import { config } from '../config';
import { handleAuthError, sendError } from '../utils/error_handler';
import { logger } from '../utils/logger';

/**
 * Bearer token authentication middleware
 */
export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    logger.warn('Missing authorization header', {
      ip: req.ip,
      path: req.path,
    });
    sendError(res, handleAuthError());
    return;
  }

  const parts = authHeader.split(' ');

  if (parts.length !== 2 || parts[0] !== 'Bearer') {
    logger.warn('Invalid authorization header format', {
      ip: req.ip,
      path: req.path,
    });
    sendError(res, handleAuthError());
    return;
  }

  const token = parts[1];

  // Use timing-safe comparison to prevent timing attacks
  const tokenBuffer = Buffer.from(token, 'utf-8');
  const expectedBuffer = Buffer.from(config.bearerToken, 'utf-8');

  // Check length first (still timing-safe since we check both conditions)
  // then use timingSafeEqual for actual comparison
  let isValid = false;
  if (tokenBuffer.length === expectedBuffer.length) {
    isValid = timingSafeEqual(tokenBuffer, expectedBuffer);
  }

  if (!isValid) {
    logger.warn('Invalid bearer token', {
      ip: req.ip,
      path: req.path,
    });
    sendError(res, handleAuthError());
    return;
  }

  next();
}
