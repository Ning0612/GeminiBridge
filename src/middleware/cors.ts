/**
 * CORS middleware configuration
 * Allows browser extensions to access the API
 */

import cors from 'cors';
import { logger } from '../utils/logger';

/**
 * CORS options with strict origin validation
 */
const corsOptions: cors.CorsOptions = {
  origin: (origin, callback) => {
    // Allow requests with no origin (like mobile apps or curl)
    if (!origin) {
      callback(null, true);
      return;
    }

    // Strict origin patterns (using regex for exact matching)
    const allowedOrigins = [
      /^http:\/\/localhost(:\d+)?$/,        // http://localhost or http://localhost:3000
      /^http:\/\/127\.0\.0\.1(:\d+)?$/,     // http://127.0.0.1 or http://127.0.0.1:3000
      /^https:\/\/localhost(:\d+)?$/,       // https://localhost
      /^https:\/\/127\.0\.0\.1(:\d+)?$/,    // https://127.0.0.1
      /^chrome-extension:\/\/[a-z]+$/,      // Chrome extensions
      /^moz-extension:\/\/[a-z0-9-]+$/,     // Firefox extensions
    ];

    const isAllowed = allowedOrigins.some(pattern => {
      if (pattern instanceof RegExp) {
        return pattern.test(origin);
      }
      return origin === pattern;
    });

    if (isAllowed) {
      callback(null, true);
    } else {
      logger.warn('CORS blocked origin', { origin });
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
};

export const corsMiddleware = cors(corsOptions);
