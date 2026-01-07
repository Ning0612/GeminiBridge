/**
 * GeminiBridge Server
 * OpenAI API-compatible proxy for Gemini CLI
 */

import express from 'express';
import { config } from './config';
import { logger } from './utils/logger';

// Middleware
import { corsMiddleware } from './middleware/cors';
import { requestLoggerMiddleware } from './middleware/request_logger';
import { rateLimitMiddleware } from './middleware/rate_limit';
import { authMiddleware } from './middleware/auth';

// Routes
import modelsRouter from './routes/models';
import chatRouter from './routes/chat';

/**
 * Create and configure Express application
 */
function createApp(): express.Application {
  const app = express();

  // Apply middleware in order
  app.use(corsMiddleware);

  // Explicitly handle UTF-8 encoding for JSON requests
  app.use(express.json({
    limit: '10mb',
    type: ['application/json', 'application/json; charset=utf-8']
  }));

  // Add raw body debugging middleware (before request logger)
  app.use((req, _res, next) => {
    if (req.method === 'POST' && req.path.includes('/chat/completions')) {
      console.log('[DEBUG] Raw request body:', JSON.stringify(req.body, null, 2));
      if (req.body?.messages?.[0]?.content) {
        const content = req.body.messages[0].content;
        console.log('[DEBUG] First message content:', content);
        console.log('[DEBUG] First message hex:', Buffer.from(content, 'utf8').toString('hex').substring(0, 100));
      }
    }
    next();
  });

  app.use(requestLoggerMiddleware);
  app.use(rateLimitMiddleware);
  app.use(authMiddleware);

  // Mount routes
  app.use(modelsRouter);
  app.use(chatRouter);

  // Health check endpoint (no auth required)
  app.get('/health', (_req, res) => {
    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    });
  });

  // 404 handler
  app.use((req, res) => {
    res.status(404).json({
      error: {
        message: `Route ${req.method} ${req.path} not found`,
        type: 'invalid_request_error',
        code: 'not_found',
      },
    });
  });

  // Global error handler
  app.use((err: Error, req: express.Request, res: express.Response, _next: express.NextFunction) => {
    logger.error('Unhandled error', {
      error: err.message,
      stack: err.stack,
      path: req.path,
      method: req.method,
    });

    res.status(500).json({
      error: {
        message: 'Internal server error',
        type: 'api_error',
        code: 'internal_error',
      },
    });
  });

  return app;
}

/**
 * Start server
 */
function startServer(): void {
  // Set UTF-8 encoding for Windows console output
  if (process.platform === 'win32') {
    try {
      // Set console code page to UTF-8 (65001)
      require('child_process').execSync('chcp 65001', { stdio: 'ignore' });
    } catch (err) {
      logger.warn('Failed to set console code page to UTF-8', { error: String(err) });
    }
  }

  const app = createApp();

  const server = app.listen(config.port, config.host, () => {
    logger.info('GeminiBridge server started', {
      host: config.host,
      port: config.port,
      geminiCLI: config.geminiCLI.cliPath,
      rateLimit: `${config.rateLimit.maxRequests} requests per ${config.rateLimit.windowMs}ms`,
      models: Object.keys(config.modelMappings).length,
    });

    logger.info('Available model mappings', {
      mappings: config.modelMappings,
      defaultModel: config.defaultModel,
    });
  });

  // Graceful shutdown
  const shutdown = (signal: string) => {
    logger.info(`${signal} received, shutting down gracefully`);

    server.close(() => {
      logger.info('Server closed');
      process.exit(0);
    });

    // Force shutdown after 10 seconds
    setTimeout(() => {
      logger.error('Forced shutdown after timeout');
      process.exit(1);
    }, 10000);
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));

  // Handle uncaught errors
  process.on('uncaughtException', (error) => {
    logger.error('Uncaught exception', {
      error: error.message,
      stack: error.stack,
    });
    process.exit(1);
  });

  process.on('unhandledRejection', (reason) => {
    logger.error('Unhandled rejection', {
      reason: String(reason),
    });
    process.exit(1);
  });
}

// Start server if running directly
if (require.main === module) {
  startServer();
}

export { createApp, startServer };
