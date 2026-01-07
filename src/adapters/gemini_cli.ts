/**
 * Gemini CLI Adapter
 * Executes Gemini CLI with support for both streaming and non-streaming modes
 */

import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { CLIExecutionResult } from '../types';
import { config } from '../config';
import { logger } from '../utils/logger';

/**
 * Stream event emitter for Gemini CLI streaming mode
 */
export class GeminiStream extends EventEmitter {
  private process: ChildProcess | null = null;
  private timeout: NodeJS.Timeout | null = null;
  private workDir: string;

  constructor(private prompt: string, private model: string, private requestId: string) {
    super();
    this.workDir = this.createTempWorkDir();
  }

  /**
   * Create temporary working directory for this execution
   */
  private createTempWorkDir(): string {
    const tempDir = path.join(os.tmpdir(), `gemini-bridge-${this.requestId}`);
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }
    return tempDir;
  }

  /**
   * Start streaming execution
   */
  public start(): void {
    logger.info('Starting Gemini CLI (streaming)', {
      requestId: this.requestId,
      model: this.model,
      cliPath: config.geminiCLI.cliPath,
      promptLength: this.prompt.length,
      promptPreview: this.prompt.substring(0, 100),
    });

    // Use stdin to pass prompt to avoid shell encoding issues
    const args = ['-m', this.model, '--sandbox'];

    this.process = spawn(config.geminiCLI.cliPath, args, {
      cwd: this.workDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: true,
    });

    // Write prompt to stdin instead of using -p parameter
    if (this.process.stdin) {
      this.process.stdin.write(this.prompt, 'utf8');
      this.process.stdin.end();
    }

    // Set timeout
    this.timeout = setTimeout(() => {
      this.cleanup('Execution timeout');
      this.emit('error', new Error('Gemini CLI execution timeout'));
    }, config.geminiCLI.timeout);

    // Handle stdout (JSONL stream)
    this.process.stdout?.on('data', (data: Buffer) => {
      this.handleData(data.toString());
    });

    // Handle stderr
    this.process.stderr?.on('data', (data: Buffer) => {
      const stderr = data.toString();
      logger.warn('Gemini CLI stderr', { requestId: this.requestId, stderr });
    });

    // Handle process exit
    this.process.on('exit', (code) => {
      if (this.timeout) {
        clearTimeout(this.timeout);
      }

      if (code !== 0) {
        this.emit('error', new Error(`Gemini CLI exited with code ${code}`));
      }

      this.emit('end');
      this.cleanup();
    });

    // Handle process errors
    this.process.on('error', (error) => {
      this.emit('error', error);
      this.cleanup();
    });
  }

  /**
   * Handle incoming data as plain text stream
   */
  private handleData(data: string): void {
    // Emit data chunks directly as they arrive
    // This provides real-time streaming of the CLI output
    if (data && data.trim()) {
      console.log('[DEBUG] Streaming chunk:', data);
      this.emit('data', data);
    }
  }

  /**
   * Cleanup resources
   */
  private cleanup(reason?: string): void {
    if (this.timeout) {
      clearTimeout(this.timeout);
      this.timeout = null;
    }

    if (this.process) {
      this.process.kill();
      this.process = null;
    }

    // Clean up temp directory
    try {
      if (fs.existsSync(this.workDir)) {
        fs.rmSync(this.workDir, { recursive: true, force: true });
      }
    } catch (error) {
      logger.warn('Failed to cleanup temp directory', {
        requestId: this.requestId,
        workDir: this.workDir,
        error: error instanceof Error ? error.message : String(error),
      });
    }

    if (reason) {
      logger.info('Stream cleanup', { requestId: this.requestId, reason });
    }
  }

  /**
   * Stop streaming
   */
  public stop(): void {
    this.cleanup('Manual stop');
  }
}

/**
 * Execute Gemini CLI in non-streaming mode
 */
export async function executeGeminiCLI(
  prompt: string,
  model: string,
  requestId: string
): Promise<CLIExecutionResult> {
  const startTime = Date.now();
  const workDir = path.join(os.tmpdir(), `gemini-bridge-${requestId}`);

  // Create temp working directory
  if (!fs.existsSync(workDir)) {
    fs.mkdirSync(workDir, { recursive: true });
  }

  return new Promise((resolve) => {
    logger.info('Starting Gemini CLI (non-streaming)', {
      requestId,
      model,
      cliPath: config.geminiCLI.cliPath,
      promptLength: prompt.length,
      promptPreview: prompt.substring(0, 100),
    });

    // Use stdin to pass prompt to avoid shell encoding issues
    const args = ['-m', model, '--sandbox'];

    console.log('[DEBUG] Executing:', config.geminiCLI.cliPath, args.join(' '));
    console.log('[DEBUG] Prompt length:', prompt.length, 'bytes');
    console.log('[DEBUG] Prompt buffer:', Buffer.from(prompt, 'utf8').toString('hex').substring(0, 100));

    const spawnedProcess = spawn(config.geminiCLI.cliPath, args, {
      cwd: workDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: true,
    });

    // Write prompt to stdin with UTF-8 encoding
    if (spawnedProcess.stdin) {
      const promptBuffer = Buffer.from(prompt, 'utf8');
      console.log('[DEBUG] Writing', promptBuffer.length, 'bytes to stdin');
      spawnedProcess.stdin.write(promptBuffer);
      spawnedProcess.stdin.end();
    }

    let stdout = '';
    let stderr = '';

    // Set timeout
    const timeout = setTimeout(() => {
      spawnedProcess.kill();
      resolve({
        success: false,
        error: 'Execution timeout',
        exitCode: -1,
        stderr: 'Process killed due to timeout',
        executionTime: Date.now() - startTime,
      });
    }, config.geminiCLI.timeout);

    spawnedProcess.stdout?.on('data', (data: Buffer) => {
      stdout += data.toString();
    });

    spawnedProcess.stderr?.on('data', (data: Buffer) => {
      stderr += data.toString();
    });

    // Use 'close' event instead of 'exit' to ensure stdout is fully flushed
    spawnedProcess.on('close', (code) => {
      clearTimeout(timeout);

      // Cleanup temp directory
      try {
        if (fs.existsSync(workDir)) {
          fs.rmSync(workDir, { recursive: true, force: true });
        }
      } catch (error) {
        logger.warn('Failed to cleanup temp directory', {
          requestId,
          workDir,
          error: error instanceof Error ? error.message : String(error),
        });
      }

      const executionTime = Date.now() - startTime;

      // Log raw stdout for debugging (first 500 chars)
      logger.info('CLI stdout received', {
        requestId,
        stdoutLength: stdout.length,
        stdoutPreview: stdout.substring(0, 500),
      });

      if (code !== 0) {
        resolve({
          success: false,
          error: `CLI exited with code ${code}`,
          exitCode: code || -1,
          stderr,
          executionTime,
        });
        return;
      }

      // Use stdout directly as plain text response
      // Trim whitespace and use the full output
      const content = stdout.trim();

      if (!content) {
        resolve({
          success: false,
          error: 'Empty response from CLI',
          exitCode: 0,
          stderr,
          executionTime,
        });
        return;
      }

      logger.info('Extracted content from CLI output', {
        requestId,
        contentLength: content.length,
        contentPreview: content.substring(0, 200),
      });

      console.log('[DEBUG] Full CLI response:', content);

      resolve({
        success: true,
        content,
        exitCode: 0,
        stderr,
        executionTime,
      });
    });

    spawnedProcess.on('error', (error) => {
      clearTimeout(timeout);

      resolve({
        success: false,
        error: error.message,
        exitCode: -1,
        stderr,
        executionTime: Date.now() - startTime,
      });
    });
  });
}

/**
 * Create streaming instance
 */
export function createGeminiStream(
  prompt: string,
  model: string,
  requestId: string
): GeminiStream {
  return new GeminiStream(prompt, model, requestId);
}
