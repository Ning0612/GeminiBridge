/**
 * Configuration loader for GeminiBridge
 * Loads environment variables and model mappings
 */

import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';
import { AppConfig, ModelMapping } from '../types';

// Load environment variables
dotenv.config();

/**
 * Load model mappings from JSON file
 */
function loadModelMappings(): ModelMapping {
  const modelsPath = path.join(process.cwd(), 'config', 'models.json');

  try {
    const data = fs.readFileSync(modelsPath, 'utf-8');
    return JSON.parse(data) as ModelMapping;
  } catch (error) {
    console.warn('Failed to load model mappings, using defaults:', error);
    return {
      'gpt-3.5-turbo': 'gemini-2.5-flash',
      'gpt-4': 'gemini-2.5-pro',
    };
  }
}

/**
 * Validate required environment variables
 */
function validateConfig(): void {
  const required = ['BEARER_TOKEN'];
  const missing = required.filter((key) => !process.env[key]);

  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}\n` +
      'Please check your .env file'
    );
  }

  // Validate Bearer Token strength
  const token = process.env.BEARER_TOKEN!;
  if (token.length < 32) {
    console.warn('⚠️  WARNING: BEARER_TOKEN should be at least 32 characters for security');
  }
  if (token === 'your-secret-token-here') {
    console.warn('⚠️  WARNING: Please change the default BEARER_TOKEN in production');
  }
}

/**
 * Get configuration from environment variables
 */
export function getConfig(): AppConfig {
  validateConfig();

  const modelMappings = loadModelMappings();

  const config: AppConfig = {
    port: parseInt(process.env.PORT || '11434', 10),
    host: process.env.HOST || '127.0.0.1',
    bearerToken: process.env.BEARER_TOKEN!,
    geminiCLI: {
      // Hard-coded to 'gemini' for security and compatibility
      // Using full paths or custom values can cause incorrect response content
      cliPath: 'gemini',
      timeout: parseInt(process.env.GEMINI_CLI_TIMEOUT || '30000', 10),
      useSandbox: true, // Always use sandbox for security
    },
    logLevel: process.env.LOG_LEVEL || 'info',
    rateLimit: {
      maxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100', 10),
      windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000', 10),
    },
    modelMappings,
    defaultModel: 'gemini-2.5-flash', // Fallback for unmapped models
  };


  return config;
}

// Export singleton config instance
export const config = getConfig();
