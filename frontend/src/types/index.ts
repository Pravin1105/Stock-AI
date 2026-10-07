export type IntentTask = 'ranking' | 'trend' | 'forecast';

export interface QueryScope {
  store_id?: number | null;
  item_id?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  forecast_horizon_days?: number | null;
  limit?: number | null;
  order?: 'asc' | 'desc' | null;
  group_by?: string | null;
}

export interface StructuredIntent {
  raw_query: string;
  task: IntentTask;
  scope: QueryScope;
  explanation?: string;
}

export interface SummaryMetrics {
  total_sales?: number;
  mean_sales?: number;
  median_sales?: number;
  min_sales?: number;
  max_sales?: number;
  record_count: number;
}

export interface UnifiedResult {
  intent: StructuredIntent;
  task: IntentTask;
  status: 'success' | 'error';
  error_message?: string;
  columns: string[];
  records: Record<string, any>[];
  summary: SummaryMetrics;
  metadata: Record<string, any>;
}

export type LLMProvider = 'gemini' | 'openai' | 'anthropic' | 'groq';

export interface ProviderInfo {
  name: string;
  default_model: string;
  models: string[];
  has_server_key: boolean;
}

export interface ModelsCatalogResponse {
  default_provider: LLMProvider;
  providers: Record<LLMProvider, ProviderInfo>;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  intent?: StructuredIntent;
  result?: UnifiedResult;
  provider?: string;
  model?: string;
  isLoading?: boolean;
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

