/**
 * Chat completions endpoint
 * POST /v1/chat/completions - Handles both streaming and non-streaming requests
 */

import { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { config } from '../config';
import { ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChunk } from '../types';
import { buildPrompt, validateMessages } from '../utils/prompt_builder';
import { executeGeminiCLI, createGeminiStream } from '../adapters/gemini_cli';
import {
  sendError,
  handleValidationError,
  handleCLIError,
  handleParseError,
} from '../utils/error_handler';
import { logRequest, logRequestStart, logError, logger } from '../utils/logger';

const router = Router();

/**
 * POST /v1/chat/completions
 * Handles both streaming and non-streaming chat completion requests
 */
router.post('/v1/chat/completions', async (req: Request, res: Response) => {
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
});

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

  const stream = createGeminiStream(prompt, mappedModel, requestId);

  let hasError = false;
  let chunkCount = 0;

  // Handle stream data
  stream.on('data', (content: string) => {
    chunkCount++;

    const chunk: ChatCompletionChunk = {
      id: `chatcmpl-${requestId}`,
      object: 'chat.completion.chunk',
      created: Math.floor(Date.now() / 1000),
      model: requestedModel,
      choices: [
        {
          index: 0,
          delta: {
            content,
          },
          finish_reason: null,
        },
      ],
    };

    res.write(`data: ${JSON.stringify(chunk)}\n\n`);
  });

  // Handle stream end
  stream.on('end', () => {
    if (hasError) {
      return;
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
      stderr: undefined,
      latency: Date.now() - startTime,
    });

    logger.info('Streaming completed', {
      requestId,
      chunkCount,
      latency: Date.now() - startTime,
    });
  });

  // Handle stream errors
  stream.on('error', (error: Error) => {
    hasError = true;

    logError(requestId, error, { mappedModel, chunkCount });

    const errorChunk = {
      error: {
        message: error.message,
        type: 'api_error',
        code: 'model_error',
      },
    };

    res.write(`data: ${JSON.stringify(errorChunk)}\n\n`);
    res.end();
  });

  // Handle client disconnect
  req.on('close', () => {
    logger.info('Client disconnected', { requestId, chunkCount });
    stream.stop();
  });

  // Start streaming
  stream.start();
}

export default router;
