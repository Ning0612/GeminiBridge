/**
 * CORS middleware configuration
 * Allows browser extensions to access the API
 */

import cors from 'cors';

/**
 * CORS options
 */
const corsOptions: cors.CorsOptions = {
  origin: (origin, callback) => {
    // Allow requests with no origin (like mobile apps or curl)
    if (!origin) {
      callback(null, true);
      return;
    }

    // Allow localhost and browser extensions
    const allowedOrigins = [
      'http://localhost',
      'http://127.0.0.1',
      'chrome-extension://',
      'moz-extension://',
    ];

    const isAllowed = allowedOrigins.some((allowed) => origin.startsWith(allowed));

    if (isAllowed) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
};

export const corsMiddleware = cors(corsOptions);
