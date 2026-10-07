import { ModelsCatalogResponse, StructuredIntent, UnifiedResult } from '../types';

export interface PipelineResponseData {
  query: string;
  intent: StructuredIntent;
  result: UnifiedResult;
  explanation: string;
  provider?: string;
  model?: string;
}

export interface QueryOptions {
  provider?: string;
  model?: string;
  apiKey?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function getAvailableModels(): Promise<ModelsCatalogResponse> {
  const res = await fetch(`${API_BASE_URL}/api/models`);
  if (!res.ok) {
    throw new Error(`Failed to load models: ${res.status}`);
  }
  return await res.json();
}

export async function queryStockAI(
  query: string,
  options?: QueryOptions
): Promise<PipelineResponseData> {
  const cleanQuery = query.trim();
  if (!cleanQuery) {
    throw new Error('Query string cannot be empty.');
  }

  const payload: Record<string, any> = { query: cleanQuery };
  if (options?.provider) payload.provider = options.provider;
  if (options?.model) payload.model = options.model;
  if (options?.apiKey) payload.api_key = options.apiKey;

  const res = await fetch(`${API_BASE_URL}/api/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Server error: ${res.status}`);
  }

  return await res.json();
}

