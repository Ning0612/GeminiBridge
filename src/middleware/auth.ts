/**
 * Authentication middleware
 * Validates Bearer token from Authorization header
 */

import { Request, Response, NextFunction } from 'express';
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

  if (token !== config.bearerToken) {
    logger.warn('Invalid bearer token', {
      ip: req.ip,
      path: req.path,
    });
    sendError(res, handleAuthError());
    return;
  }

  next();
}
