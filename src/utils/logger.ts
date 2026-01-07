/**
 * Logger utility using Winston
 * Handles request logging and application logging
 */

import * as winston from 'winston';
import * as path from 'path';
import * as fs from 'fs';
import { LogEntry } from '../types';

// Ensure logs directory exists
const logsDir = path.join(process.cwd(), 'logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

/**
 * Create Winston logger instance
 */
export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    // Console output
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(({ level, message, timestamp, ...meta }) => {
          let logMessage = `${timestamp} [${level}] ${message}`;
          if (Object.keys(meta).length > 0) {
            logMessage += ` ${JSON.stringify(meta)}`;
          }
          return logMessage;
        })
      ),
    }),
    // File output
    new winston.transports.File({
      filename: path.join(logsDir, 'gemini-bridge.log'),
      maxsize: 10 * 1024 * 1024, // 10MB
      maxFiles: 5,
      tailable: true,
    }),
    // Error log file
    new winston.transports.File({
      filename: path.join(logsDir, 'error.log'),
      level: 'error',
      maxsize: 10 * 1024 * 1024, // 10MB
      maxFiles: 5,
    }),
  ],
});

/**
 * Log request details
 */
export function logRequest(entry: LogEntry): void {
  logger.info('Request completed', {
    requestId: entry.requestId,
    clientIp: entry.clientIp,
    userAgent: entry.userAgent,
    model: entry.model,
    mappedModel: entry.mappedModel,
    stream: entry.stream,
    exitCode: entry.exitCode,
    latency: entry.latency,
    error: entry.error,
    stderr: entry.stderr,
  });
}

/**
 * Log request start
 */
export function logRequestStart(requestId: string, model: string, stream: boolean): void {
  logger.info('Request started', { requestId, model, stream });
}

/**
 * Log error with context
 */
export function logError(requestId: string, error: Error | string, context?: Record<string, unknown>): void {
  logger.error('Error occurred', {
    requestId,
    error: error instanceof Error ? error.message : error,
    stack: error instanceof Error ? error.stack : undefined,
    ...context,
  });
}
