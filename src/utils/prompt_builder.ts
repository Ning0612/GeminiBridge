/**
 * Prompt builder utility
 * Converts OpenAI messages format to Gemini CLI prompt format
 */

import { Message } from '../types';

const MAX_MESSAGES = 20; // Prevent oversized prompts

/**
 * Build a Gemini CLI prompt from OpenAI messages array
 *
 * Format:
 * [System]
 * system message content
 *
 * [User]
 * user message content
 *
 * [Assistant]
 * assistant message content
 */
export function buildPrompt(messages: Message[]): string {
  // Limit conversation history to prevent oversized prompts
  const limitedMessages = messages.slice(-MAX_MESSAGES);

  const promptParts: string[] = [];

  for (const message of limitedMessages) {
    const role = message.role.charAt(0).toUpperCase() + message.role.slice(1);
    promptParts.push(`[${role}]`);
    promptParts.push(message.content);
    promptParts.push(''); // Empty line separator
  }

  return promptParts.join('\n').trim();
}

/**
 * Validate messages array
 */
export function validateMessages(messages: Message[]): { valid: boolean; error?: string } {
  if (!Array.isArray(messages)) {
    return { valid: false, error: 'Messages must be an array' };
  }

  if (messages.length === 0) {
    return { valid: false, error: 'Messages array cannot be empty' };
  }

  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];

    if (!msg.role || !msg.content) {
      return {
        valid: false,
        error: `Message at index ${i} missing required fields (role, content)`,
      };
    }

    if (!['system', 'user', 'assistant'].includes(msg.role)) {
      return {
        valid: false,
        error: `Message at index ${i} has invalid role: ${msg.role}`,
      };
    }

    if (typeof msg.content !== 'string') {
      return {
        valid: false,
        error: `Message at index ${i} content must be a string`,
      };
    }
  }

  return { valid: true };
}
