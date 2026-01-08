/**
 * Chat completions endpoint
 * POST /v1/chat/completions - Handles both streaming and non-streaming requests
 */

import { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { config } from '../config';
import { ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChunk } from '../types';
import { buildPrompt, validateMessages } from '../utils/prompt_builder';
import { executeGeminiCLI } from '../adapters/gemini_cli';
import {
  sendError,
  handleValidationError,
  handleCLIError,
  handleParseError,
} from '../utils/error_handler';
import { logRequest, logRequestStart, logError, logger } from '../utils/logger';

const router = Router();

/**
 * POST /v1/chat/completions (and /chat/completions for compatibility)
 * Handles both streaming and non-streaming chat completion requests
 */
const chatCompletionHandler = async (req: Request, res: Response) => {
  const requestId = req.context?.requestId || uuidv4();
  const startTime = Date.now();

  try {
    const body = req.body as Partial<ChatCompletionRequest>;

    // Validate required fields
    if (!body.model) {
      sendError(res, handleValidationError('Missing required field: model', 'model'));
      return;
    }

    if (!body.messages || !Array.isArray(body.messages)) {
      sendError(res, handleValidationError('Missing or invalid messages array', 'messages'));
      return;
    }

    // Validate messages
    const validation = validateMessages(body.messages);
    if (!validation.valid) {
      sendError(res, handleValidationError(validation.error || 'Invalid messages', 'messages'));
      return;
    }

    // Map model to Gemini model (with fallback)
    const requestedModel = body.model;
    const mappedModel = config.modelMappings[requestedModel] || config.defaultModel;

    logger.info('Model mapping', {
      requestId,
      requestedModel,
      mappedModel,
      fallback: !config.modelMappings[requestedModel],
    });

    // Build prompt
    const prompt = buildPrompt(body.messages);

    // Debug: Check if prompt contains valid UTF-8
    console.log('[DEBUG] Built prompt length:', prompt.length);
    console.log('[DEBUG] Built prompt preview:', prompt.substring(0, 100));
    console.log('[DEBUG] Built prompt hex:', Buffer.from(prompt, 'utf8').toString('hex').substring(0, 100));

    // Check if streaming requested
    const isStreaming = body.stream === true;

    logRequestStart(requestId, requestedModel, isStreaming);

    if (isStreaming) {
      // Handle streaming mode
      await handleStreamingRequest(req, res, requestId, requestedModel, mappedModel, prompt, startTime);
    } else {
      // Handle non-streaming mode
      await handleNonStreamingRequest(req, res, requestId, requestedModel, mappedModel, prompt, startTime);
    }
  } catch (error) {
    logError(requestId, error instanceof Error ? error : String(error));
    sendError(res, handleParseError(error instanceof Error ? error : new Error(String(error))));
  }
};

// Register handler for both paths (with and without /v1 prefix)
router.post('/v1/chat/completions', chatCompletionHandler);
router.post('/chat/completions', chatCompletionHandler);

/**
 * Handle non-streaming request
 */
async function handleNonStreamingRequest(
  req: Request,
  res: Response,
  requestId: string,
  requestedModel: string,
  mappedModel: string,
  prompt: string,
  startTime: number
): Promise<void> {
  const result = await executeGeminiCLI(prompt, mappedModel, requestId);

  // Log execution details
  logRequest({
    requestId,
    clientIp: req.context?.clientIp || 'unknown',
    userAgent: req.context?.userAgent || 'unknown',
    timestamp: req.context?.timestamp || new Date(),
    model: requestedModel,
    mappedModel,
    stream: false,
    exitCode: result.exitCode,
    stderr: result.stderr,
    latency: Date.now() - startTime,
    error: result.error,
  });

  if (!result.success) {
    sendError(res, handleCLIError(result.exitCode, result.stderr || result.error || 'Unknown error'));
    return;
  }

  // Build OpenAI response
  const response: ChatCompletionResponse = {
    id: `chatcmpl-${requestId}`,
    object: 'chat.completion',
    created: Math.floor(Date.now() / 1000),
    model: requestedModel,
    choices: [
      {
        index: 0,
        message: {
          role: 'assistant',
          content: result.content || '',
        },
        finish_reason: 'stop',
      },
    ],
  };

  res.json(response);
}

/**
 * Handle streaming request
 * Note: Despite being "streaming", we first read the complete response from CLI,
 * then send it as SSE chunks for OpenAI API compatibility
 */
async function handleStreamingRequest(
  req: Request,
  res: Response,
  requestId: string,
  requestedModel: string,
  mappedModel: string,
  prompt: string,
  startTime: number
): Promise<void> {
  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  try {
    // Execute CLI and get complete response
    const result = await executeGeminiCLI(prompt, mappedModel, requestId);

    // Handle CLI execution errors
    if (!result.success) {
      const errorChunk = {
        error: {
          message: result.error || 'Unknown error',
          type: 'api_error',
          code: 'model_error',
        },
      };

      res.write(`data: ${JSON.stringify(errorChunk)}\n\n`);
      res.end();

      logRequest({
        requestId,
        clientIp: req.context?.clientIp || 'unknown',
        userAgent: req.context?.userAgent || 'unknown',
        timestamp: req.context?.timestamp || new Date(),
        model: requestedModel,
        mappedModel,
        stream: true,
        exitCode: result.exitCode,
        stderr: result.stderr,
        latency: Date.now() - startTime,
        error: result.error,
      });

      return;
    }

    // Send complete response as SSE chunks
    const content = result.content || '';

    // Send initial chunk with role
    const initialChunk: ChatCompletionChunk = {
      id: `chatcmpl-${requestId}`,
      object: 'chat.completion.chunk',
      created: Math.floor(Date.now() / 1000),
      model: requestedModel,
      choices: [
        {
          index: 0,
          delta: { role: 'assistant' },
          finish_reason: null,
        },
      ],
    };
    res.write(`data: ${JSON.stringify(initialChunk)}\n\n`);

    // Send content as single chunk (or split into larger chunks if needed)
    if (content) {
      const contentChunk: ChatCompletionChunk = {
        id: `chatcmpl-${requestId}`,
        object: 'chat.completion.chunk',
        created: Math.floor(Date.now() / 1000),
        model: requestedModel,
        choices: [
          {
            index: 0,
            delta: { content },
            finish_reason: null,
          },
        ],
      };
      res.write(`data: ${JSON.stringify(contentChunk)}\n\n`);
    }

    // Send final chunk with finish_reason
    const finalChunk: ChatCompletionChunk = {
      id: `chatcmpl-${requestId}`,
      object: 'chat.completion.chunk',
      created: Math.floor(Date.now() / 1000),
      model: requestedModel,
      choices: [
        {
          index: 0,
          delta: {},
          finish_reason: 'stop',
        },
      ],
    };

    res.write(`data: ${JSON.stringify(finalChunk)}\n\n`);
    res.write('data: [DONE]\n\n');
    res.end();

    // Log completion
    logRequest({
      requestId,
      clientIp: req.context?.clientIp || 'unknown',
      userAgent: req.context?.userAgent || 'unknown',
      timestamp: req.context?.timestamp || new Date(),
      model: requestedModel,
      mappedModel,
      stream: true,
      exitCode: 0,
      stderr: result.stderr,
      latency: Date.now() - startTime,
    });

    logger.info('Streaming completed', {
      requestId,
      contentLength: content.length,
      latency: Date.now() - startTime,
    });
  } catch (error) {
    logError(requestId, error instanceof Error ? error : String(error), { mappedModel });

    const errorChunk = {
      error: {
        message: error instanceof Error ? error.message : 'Unknown error',
        type: 'api_error',
        code: 'internal_error',
      },
    };

    res.write(`data: ${JSON.stringify(errorChunk)}\n\n`);
    res.end();
  }
}

export default router;
