/**
 * Error handler utility
 * Creates OpenAI-compatible error responses
 */

import { OpenAIError, ErrorCode, ErrorDetails } from '../types';
import { Response } from 'express';

/**
 * Error mapping from internal codes to HTTP status codes
 */
const ERROR_STATUS_MAP: Record<ErrorCode, number> = {
  [ErrorCode.INVALID_REQUEST]: 400,
  [ErrorCode.INVALID_RESPONSE_FORMAT]: 500,
  [ErrorCode.MODEL_ERROR]: 500,
  [ErrorCode.TIMEOUT]: 504,
  [ErrorCode.AUTHENTICATION_ERROR]: 401,
  [ErrorCode.RATE_LIMIT_ERROR]: 429,
  [ErrorCode.INTERNAL_ERROR]: 500,
};

/**
 * Create OpenAI error response
 */
export function createErrorResponse(details: ErrorDetails): OpenAIError {
  return {
    error: {
      message: details.message,
      type: 'api_error',
      code: details.code,
      param: details.param || null,
    },
  };
}

/**
 * Send error response
 */
export function sendError(res: Response, details: ErrorDetails): void {
  const statusCode = details.statusCode || ERROR_STATUS_MAP[details.code] || 500;
  const errorResponse = createErrorResponse(details);

  res.status(statusCode).json(errorResponse);
}

/**
 * Handle CLI execution errors
 */
export function handleCLIError(_exitCode: number, stderr: string): ErrorDetails {
  if (stderr.includes('timeout') || stderr.includes('timed out')) {
    return {
      code: ErrorCode.TIMEOUT,
      message: 'Request timed out while processing',
      statusCode: 504,
    };
  }

  return {
    code: ErrorCode.MODEL_ERROR,
    message: `Gemini CLI execution failed: ${stderr || 'Unknown error'}`,
    statusCode: 500,
  };
}

/**
 * Handle JSON parse errors
 */
export function handleParseError(error: Error): ErrorDetails {
  return {
    code: ErrorCode.INVALID_RESPONSE_FORMAT,
    message: `Failed to parse Gemini CLI response: ${error.message}`,
    statusCode: 500,
  };
}

/**
 * Handle authentication errors
 */
export function handleAuthError(): ErrorDetails {
  return {
    code: ErrorCode.AUTHENTICATION_ERROR,
    message: 'Invalid or missing bearer token',
    statusCode: 401,
  };
}

/**
 * Handle rate limit errors
 */
export function handleRateLimitError(): ErrorDetails {
  return {
    code: ErrorCode.RATE_LIMIT_ERROR,
    message: 'Rate limit exceeded. Please try again later.',
    statusCode: 429,
  };
}

/**
 * Handle validation errors
 */
export function handleValidationError(message: string, param?: string): ErrorDetails {
  return {
    code: ErrorCode.INVALID_REQUEST,
    message,
    param,
    statusCode: 400,
  };
}
