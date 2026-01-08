/**
 * Logger utility using Winston
 * Handles request logging and application logging
 */

import * as winston from 'winston';
import * as path from 'path';
import * as fs from 'fs';
import DailyRotateFile from 'winston-daily-rotate-file';
import { LogEntry } from '../types';

// Ensure logs directory exists
const logsDir = path.join(process.cwd(), 'logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Log retention in days (default: 7 days)
const logRetentionDays = process.env.LOG_RETENTION_DAYS ? parseInt(process.env.LOG_RETENTION_DAYS, 10) : 7;

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
    // Daily rotating file for all logs
    new DailyRotateFile({
      dirname: logsDir,
      filename: 'gemini-bridge-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      zippedArchive: true,
      maxSize: '10m',
      maxFiles: `${logRetentionDays}d`,
    }),
    // Daily rotating file for error logs only
    new DailyRotateFile({
      dirname: logsDir,
      filename: 'error-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      level: 'error',
      zippedArchive: true,
      maxSize: '10m',
      maxFiles: `${logRetentionDays}d`,
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
