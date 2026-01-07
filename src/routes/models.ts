/**
 * Models endpoint
 * GET /v1/models - Returns available model list
 */

import { Router, Request, Response } from 'express';
import { config } from '../config';
import { ModelsListResponse } from '../types';

const router = Router();

/**
 * GET /v1/models
 * Returns OpenAI-compatible list of available models
 */
router.get('/v1/models', (_req: Request, res: Response) => {
  const models = Object.keys(config.modelMappings).map((modelId) => ({
    id: modelId,
    object: 'model' as const,
    created: Math.floor(Date.now() / 1000),
    owned_by: 'gemini-bridge',
  }));

  const response: ModelsListResponse = {
    object: 'list',
    data: models,
  };

  res.json(response);
});

export default router;
