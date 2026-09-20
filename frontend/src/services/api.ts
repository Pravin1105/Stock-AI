import { StructuredIntent, UnifiedResult } from '../types';

export interface PipelineResponseData {
  query: string;
  intent: StructuredIntent;
  result: UnifiedResult;
  explanation: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function queryStockAI(query: string): Promise<PipelineResponseData> {
  const cleanQuery = query.trim();
  if (!cleanQuery) {
    throw new Error('Query string cannot be empty.');
  }

  const res = await fetch(`${API_BASE_URL}/api/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query: cleanQuery }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Server error: ${res.status}`);
  }

  return await res.json();
}
