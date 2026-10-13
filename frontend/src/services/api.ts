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

export interface TranscribeResponseData {
  transcript: string;
  provider: string;
  model?: string;
  confidence?: number;
  is_simulated?: boolean;
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      if (!result) {
        reject(new Error('Failed to read recorded audio data.'));
        return;
      }
      const base64 = result.includes(',') ? result.split(',')[1] : result;
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error || new Error('Audio reading failed'));
    reader.readAsDataURL(blob);
  });
}

export async function transcribeVoiceQuery(
  audioBlob: Blob,
  options?: QueryOptions
): Promise<TranscribeResponseData> {
  if (!audioBlob || audioBlob.size === 0) {
    throw new Error('Recorded audio is empty. Please speak clearly for at least 1-2 seconds.');
  }

  const base64Audio = await blobToBase64(audioBlob);
  if (!base64Audio || !base64Audio.trim()) {
    throw new Error('Could not encode audio data. Please try recording again.');
  }

  const payload: Record<string, any> = {
    audio_base64: base64Audio,
    mime_type: audioBlob.type || 'audio/webm',
  };
  if (options?.provider) payload.provider = options.provider;
  if (options?.apiKey) payload.api_key = options.apiKey;

  const res = await fetch(`${API_BASE_URL}/api/voice/transcribe`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorMessage = `Transcription error (${res.status})`;
    try {
      const errData = await res.json();
      if (typeof errData.detail === 'string') {
        errorMessage = errData.detail;
      } else if (Array.isArray(errData.detail)) {
        errorMessage = errData.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
      } else if (errData.error?.message) {
        errorMessage = errData.error.message;
      } else if (errData.detail) {
        errorMessage = JSON.stringify(errData.detail);
      }
    } catch {
      errorMessage = res.statusText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return await res.json();
}


