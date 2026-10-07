import React, { useEffect, useRef } from 'react';
import { Sparkles, TrendingUp, Database, Brain, Key, Zap, ChevronDown } from 'lucide-react';
import { ChatMessage, LLMProvider } from '../types';
import { MessageItem } from './MessageItem';
import { ChatInput } from './ChatInput';

interface ChatWorkspaceProps {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  isLoading: boolean;
  selectedProvider: LLMProvider;
  selectedModel: string;
  hasKeyConfigured: boolean;
  onOpenModelModal: () => void;
}

const PROVIDER_LABELS: Record<LLMProvider, string> = {
  gemini: 'Gemini',
  openai: 'OpenAI',
  anthropic: 'Claude',
  groq: 'Groq',
};

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  messages,
  onSend,
  isLoading,
  selectedProvider,
  selectedModel,
  hasKeyConfigured,
  onOpenModelModal,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <main className="main-content">
      {/* Top Navigation Header */}
      <header className="top-header">
        <div className="logo-badge">
          <div className="logo-icon">S</div>
          <div>
            <span>Stock AI</span>
            <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)', marginLeft: '8px' }}>
              Conversational Analytics Workspace
            </span>
          </div>
        </div>

        {/* Model & BYOK Trigger Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={onOpenModelModal}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'white',
              border: '1px solid var(--border-strong)',
              borderRadius: '20px',
              padding: '6px 14px',
              boxShadow: 'var(--shadow-sm)',
              cursor: 'pointer',
            }}
            title="Configure LLM Model and Bring Your Own Key (BYOK)"
          >
            <div
              style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                backgroundColor: 'var(--surface-warm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent)',
              }}
            >
              {selectedProvider === 'groq' ? (
                <Zap size={12} />
              ) : selectedProvider === 'gemini' ? (
                <Sparkles size={12} />
              ) : (
                <Key size={12} />
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
              <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                {PROVIDER_LABELS[selectedProvider]}
              </span>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 500, maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {selectedModel}
              </span>
            </div>

            {/* Key Status Indicator Dot */}
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: hasKeyConfigured ? '#34A853' : '#FBBC05',
                marginLeft: '2px',
              }}
              title={hasKeyConfigured ? 'API Key Active (BYOK or Server)' : 'Personal Key Recommended'}
            />

            <ChevronDown size={14} color="var(--text-muted)" />
          </button>
        </div>
      </header>


      {/* Message Stream */}
      <div className="chat-scroll-area">
        {messages.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', marginTop: '60px', textAlign: 'center', gap: '20px' }}>
            <div style={{ width: '56px', height: '56px', borderRadius: '16px', backgroundColor: 'var(--surface-warm)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <TrendingUp size={28} color="var(--accent)" />
            </div>

            <div style={{ maxWidth: '540px' }}>
              <h2 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
                Retail Demand & Sales Intelligence
              </h2>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Ask questions about historical store sales, identify top or bottom products, examine seasonal trends, or forecast future inventory demand using trained gradient-boosted ML models.
              </p>
            </div>

            {/* Architecture Explanatory Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', width: '100%', maxWidth: '640px', marginTop: '12px' }}>
              <div style={{ background: 'white', border: '1px solid var(--border)', padding: '14px', borderRadius: '12px', textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent)', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>
                  <Brain size={16} /> 1. Query Parser
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Extracts task ("What?") and scope ("Store/Item") without math hallucinations.</div>
              </div>

              <div style={{ background: 'white', border: '1px solid var(--border)', padding: '14px', borderRadius: '12px', textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#2F649B', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>
                  <Database size={16} /> 2. Analytics Engine
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>SQL aggregations, statistics, and XGBoost machine learning inference.</div>
              </div>

              <div style={{ background: 'white', border: '1px solid var(--border)', padding: '14px', borderRadius: '12px', textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#A35728', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>
                  <Sparkles size={16} /> 3. LLM Explainer
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Generates clear executive summaries grounded in exact calculated data.</div>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => <MessageItem key={msg.id} message={msg} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* Persistent Input Dock */}
      <ChatInput onSend={onSend} disabled={isLoading} />
    </main>
  );
};
