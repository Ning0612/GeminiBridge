/**
 * TypeScript type definitions for GeminiBridge
 * OpenAI API compatibility types and internal types
 */

// ============================================================================
// OpenAI API Types
// ============================================================================

export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: Message[];
  stream?: boolean;
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  n?: number;
  stop?: string | string[];
  presence_penalty?: number;
  frequency_penalty?: number;
}

export interface ChatCompletionResponse {
  id: string;
  object: 'chat.completion';
  created: number;
  model: string;
  choices: Array<{
    index: number;
    message: {
      role: 'assistant';
      content: string;
    };
    finish_reason: 'stop' | 'length' | 'content_filter' | null;
  }>;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface ChatCompletionChunk {
  id: string;
  object: 'chat.completion.chunk';
  created: number;
  model: string;
  choices: Array<{
    index: number;
    delta: {
      role?: 'assistant';
      content?: string;
    };
    finish_reason: 'stop' | 'length' | 'content_filter' | null;
  }>;
}

export interface ModelInfo {
  id: string;
  object: 'model';
  created?: number;
  owned_by?: string;
}

export interface ModelsListResponse {
  object: 'list';
  data: ModelInfo[];
}

export interface OpenAIError {
  error: {
    message: string;
    type: string;
    code: string;
    param?: string | null;
  };
}

// ============================================================================
// Gemini CLI Types
// ============================================================================

export interface GeminiCLIConfig {
  cliPath: string;
  timeout: number;
  useSandbox: boolean;
}

export interface CLIExecutionResult {
  success: boolean;
  content?: string;
  error?: string;
  exitCode: number;
  stderr?: string;
  executionTime: number;
}

// ============================================================================
// Internal Application Types
// ============================================================================

export interface RequestContext {
  requestId: string;
  clientIp: string;
  userAgent: string;
  timestamp: Date;
  model?: string;
  mappedModel?: string;
}

export interface LogEntry {
  requestId: string;
  clientIp: string;
  userAgent: string;
  timestamp: Date;
  model: string;
  mappedModel: string;
  stream: boolean;
  exitCode: number;
  stderr?: string;
  latency: number;
  error?: string;
}

export interface ModelMapping {
  [openAIModel: string]: string; // Maps to Gemini model
}

export interface AppConfig {
  port: number;
  host: string;
  bearerToken: string;
  geminiCLI: GeminiCLIConfig;
  logLevel: string;
  logFile: string;
  rateLimit: {
    maxRequests: number;
    windowMs: number;
  };
  modelMappings: ModelMapping;
  defaultModel: string; // Fallback model for unmapped requests
}

// ============================================================================
// HTTP Response Helper Types
// ============================================================================

export enum ErrorCode {
  INVALID_REQUEST = 'invalid_request_error',
  INVALID_RESPONSE_FORMAT = 'invalid_response_format',
  MODEL_ERROR = 'model_error',
  TIMEOUT = 'timeout',
  AUTHENTICATION_ERROR = 'authentication_error',
  RATE_LIMIT_ERROR = 'rate_limit_exceeded',
  INTERNAL_ERROR = 'internal_server_error',
}

export interface ErrorDetails {
  code: ErrorCode;
  message: string;
  param?: string;
  statusCode: number;
}
