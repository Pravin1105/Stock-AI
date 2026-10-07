import React, { useState, useEffect } from 'react';
import {
  X,
  Key,
  Check,
  Eye,
  EyeOff,
  Zap,
  Sparkles,
  ShieldCheck,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { LLMProvider, ModelsCatalogResponse } from '../types';

interface ModelSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedProvider: LLMProvider;
  selectedModel: string;
  onSelectProvider: (provider: LLMProvider) => void;
  onSelectModel: (model: string) => void;
  byokKeys: Record<string, string>;
  onSaveKey: (provider: LLMProvider, key: string) => void;
  onClearKey: (provider: LLMProvider) => void;
  modelsCatalog: ModelsCatalogResponse | null;
}

const PROVIDER_METAS: Record<
  LLMProvider,
  {
    name: string;
    description: string;
    accentColor: string;
    keyPlaceholder: string;
    keyDocUrl: string;
    defaultModels: string[];
  }
> = {
  gemini: {
    name: 'Google Gemini',
    description: 'Multimodal multimodal reasoning with large context windows',
    accentColor: '#1A73E8',
    keyPlaceholder: 'AIzaSy...',
    keyDocUrl: 'https://aistudio.google.com/app/apikey',
    defaultModels: ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.5-flash'],
  },
  openai: {
    name: 'OpenAI',
    description: 'Industry-standard GPT models with high reasoning fidelity',
    accentColor: '#10A37F',
    keyPlaceholder: 'sk-proj-...',
    keyDocUrl: 'https://platform.openai.com/api-keys',
    defaultModels: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'o3-mini', 'gpt-3.5-turbo'],
  },
  anthropic: {
    name: 'Anthropic Claude',
    description: 'Nuanced executive synthesis and steerable conversational reasoning',
    accentColor: '#D97706',
    keyPlaceholder: 'sk-ant-api03-...',
    keyDocUrl: 'https://console.anthropic.com/settings/keys',
    defaultModels: [
      'claude-3-5-haiku-latest',
      'claude-3-7-sonnet-latest',
      'claude-3-5-sonnet-latest',
      'claude-3-haiku-20240307',
    ],
  },
  groq: {
    name: 'Groq',
    description: 'Ultra-low latency LPU inference with open-source Llama & Mixtral',
    accentColor: '#F55036',
    keyPlaceholder: 'gsk_...',
    keyDocUrl: 'https://console.groq.com/keys',
    defaultModels: [
      'llama-3.3-70b-versatile',
      'llama-3.1-8b-instant',
      'mixtral-8x7b-32768',
      'gemma2-9b-it',
    ],
  },
};

export const ModelSelectorModal: React.FC<ModelSelectorModalProps> = ({
  isOpen,
  onClose,
  selectedProvider,
  selectedModel,
  onSelectProvider,
  onSelectModel,
  byokKeys,
  onSaveKey,
  onClearKey,
  modelsCatalog,
}) => {
  const [activeTab, setActiveTab] = useState<LLMProvider>(selectedProvider);
  const [keyInput, setKeyInput] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [isCustomModel, setIsCustomModel] = useState(false);
  const [customModelInput, setCustomModelInput] = useState('');
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    setActiveTab(selectedProvider);
  }, [selectedProvider, isOpen]);

  useEffect(() => {
    const existing = byokKeys[activeTab] || '';
    setKeyInput(existing);
    setShowKey(false);
    setSavedNotice(false);

    const availableModels =
      modelsCatalog?.providers[activeTab]?.models || PROVIDER_METAS[activeTab].defaultModels;
    if (activeTab === selectedProvider && !availableModels.includes(selectedModel)) {
      setIsCustomModel(true);
      setCustomModelInput(selectedModel);
    } else {
      setIsCustomModel(false);
    }
  }, [activeTab, byokKeys, isOpen, modelsCatalog, selectedModel, selectedProvider]);

  if (!isOpen) return null;

  const currentMeta = PROVIDER_METAS[activeTab];
  const providerCatalog = modelsCatalog?.providers[activeTab];
  const availableModels = providerCatalog?.models || currentMeta.defaultModels;
  const hasServerKey = Boolean(providerCatalog?.has_server_key);
  const hasUserKey = Boolean(byokKeys[activeTab]);

  const handleSaveKey = () => {
    onSaveKey(activeTab, keyInput.trim());
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  const handleClearKey = () => {
    onClearKey(activeTab);
    setKeyInput('');
    setSavedNotice(false);
  };

  const handleApply = () => {
    onSelectProvider(activeTab);
    if (isCustomModel && customModelInput.trim()) {
      onSelectModel(customModelInput.trim());
    } else if (!isCustomModel) {
      if (!availableModels.includes(selectedModel) || activeTab !== selectedProvider) {
        onSelectModel(providerCatalog?.default_model || currentMeta.defaultModels[0]);
      }
    }
    onClose();
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.45)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '680px',
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.15)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--surface)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                backgroundColor: 'var(--surface-warm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Key size={18} color="var(--accent)" />
            </div>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>
                LLM Provider & BYOK Settings
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Bring Your Own Key or select inference provider for query routing & explanations
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '6px',
              borderRadius: '8px',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {/* Provider Tabs */}
          <div style={{ marginBottom: '20px' }}>
            <label
              style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 700,
                textTransform: 'uppercase',
                color: 'var(--text-muted)',
                marginBottom: '10px',
                letterSpacing: '0.5px',
              }}
            >
              1. Choose Provider
            </label>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '10px',
              }}
            >
              {(Object.keys(PROVIDER_METAS) as LLMProvider[]).map((provKey) => {
                const meta = PROVIDER_METAS[provKey];
                const isSelected = activeTab === provKey;
                const provServerKey = Boolean(modelsCatalog?.providers[provKey]?.has_server_key);
                const provUserKey = Boolean(byokKeys[provKey]);

                return (

                  <button
                    key={provKey}
                    onClick={() => {
                      setActiveTab(provKey);
                      setIsCustomModel(false);
                      const def =
                        modelsCatalog?.providers[provKey]?.default_model ||
                        meta.defaultModels[0];
                      onSelectModel(def);
                    }}
                    style={{
                      padding: '12px 10px',
                      borderRadius: '12px',
                      border: isSelected
                        ? `2px solid ${meta.accentColor}`
                        : '1px solid var(--border-strong)',
                      backgroundColor: isSelected ? 'var(--bg-primary)' : 'white',
                      textAlign: 'center',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '6px',
                      position: 'relative',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '8px',
                        backgroundColor: `${meta.accentColor}18`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: meta.accentColor,
                        fontWeight: 700,
                        fontSize: '13px',
                      }}
                    >
                      {provKey === 'groq' ? (
                        <Zap size={16} />
                      ) : provKey === 'gemini' ? (
                        <Sparkles size={16} />
                      ) : (
                        meta.name[0]
                      )}
                    </div>
                    <span
                      style={{
                        fontSize: '13px',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                      }}
                    >
                      {meta.name}
                    </span>
                    <span
                      style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '6px',
                        fontWeight: 600,
                        backgroundColor: provUserKey
                          ? '#EBF5EB'
                          : provServerKey
                          ? '#E8F0FE'
                          : '#FFF3E0',
                        color: provUserKey
                          ? '#2E7D32'
                          : provServerKey
                          ? '#1A73E8'
                          : '#E65100',
                      }}
                    >
                      {provUserKey
                        ? 'BYOK Active'
                        : provServerKey
                        ? 'Server Key'
                        : 'Key Needed'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Model Selection */}
          <div style={{ marginBottom: '22px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '10px',
              }}
            >
              <label
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--text-muted)',
                  letterSpacing: '0.5px',
                }}
              >
                2. Select Model for {currentMeta.name}
              </label>
              <button
                type="button"
                onClick={() => setIsCustomModel(!isCustomModel)}
                style={{
                  fontSize: '12px',
                  color: 'var(--accent)',
                  fontWeight: 600,
                }}
              >
                {isCustomModel ? '← Pick from Presets' : 'Custom Model Name →'}
              </button>
            </div>

            {isCustomModel ? (
              <div>
                <input
                  type="text"
                  placeholder="e.g. gpt-4o-2024-08-06 or custom-fine-tuned-model"
                  value={customModelInput}
                  onChange={(e) => setCustomModelInput(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-strong)',
                    fontSize: '13.5px',
                    outline: 'none',
                  }}
                />
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    marginTop: '4px',
                    display: 'block',
                  }}
                >
                  Type any valid model ID supported by {currentMeta.name}.
                </span>
              </div>
            ) : (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '8px',
                }}
              >
                {availableModels.map((m) => {
                  const isCurrent =
                    activeTab === selectedProvider && selectedModel === m;
                  const isDefault =
                    m === (providerCatalog?.default_model || currentMeta.defaultModels[0]);

                  return (
                    <button
                      key={m}
                      onClick={() => {
                        onSelectModel(m);
                        setIsCustomModel(false);
                      }}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '8px',
                        border: isCurrent
                          ? `2px solid var(--accent)`
                          : '1px solid var(--border)',
                        backgroundColor: isCurrent ? 'var(--bg-primary)' : '#FAFAFA',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        textAlign: 'left',
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: '13px',
                            fontWeight: 600,
                            color: 'var(--text-primary)',
                          }}
                        >
                          {m}
                        </div>
                        {isDefault && (
                          <div
                            style={{
                              fontSize: '11px',
                              color: 'var(--text-muted)',
                            }}
                          >
                            Recommended default
                          </div>
                        )}
                      </div>
                      {isCurrent && <Check size={16} color="var(--accent)" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* BYOK Key Section */}
          <div
            style={{
              padding: '16px',
              borderRadius: '12px',
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border-strong)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ShieldCheck size={16} color="var(--accent)" />
                <span
                  style={{
                    fontSize: '13px',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                  }}
                >
                  Bring Your Own Key (BYOK) for {currentMeta.name}
                </span>
              </div>
              <a
                href={currentMeta.keyDocUrl}
                target="_blank"
                rel="noreferrer"
                style={{
                  fontSize: '12px',
                  color: 'var(--accent)',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  textDecoration: 'none',
                }}
              >
                Get API Key <ExternalLink size={12} />
              </a>
            </div>

            <p
              style={{
                fontSize: '12px',
                color: 'var(--text-secondary)',
                marginBottom: '12px',
                lineHeight: 1.5,
              }}
            >
              Keys are stored securely in your browser's LocalStorage and sent only with your
              analytical queries. Stock AI does not store your keys on backend databases.
            </p>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  border: '1px solid var(--border-strong)',
                  padding: '0 12px',
                }}
              >
                <input
                  type={showKey ? 'text' : 'password'}
                  placeholder={`Enter your ${currentMeta.name} key (${currentMeta.keyPlaceholder})`}
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    padding: '10px 0',
                    fontSize: '13px',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  style={{
                    padding: '4px',
                    color: 'var(--text-muted)',
                  }}
                  title={showKey ? 'Hide key' : 'Show key'}
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              <button
                type="button"
                onClick={handleSaveKey}
                style={{
                  backgroundColor: 'var(--accent)',
                  color: 'white',
                  fontWeight: 600,
                  fontSize: '13px',
                  padding: '10px 16px',
                  borderRadius: '8px',
                  whiteSpace: 'nowrap',
                }}
              >
                Save Key
              </button>

              {hasUserKey && (
                <button
                  type="button"
                  onClick={handleClearKey}
                  style={{
                    backgroundColor: '#F3F3F3',
                    color: '#666',
                    fontSize: '13px',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    whiteSpace: 'nowrap',
                  }}
                >
                  Clear
                </button>
              )}
            </div>

            {/* Key Status Pill */}
            <div
              style={{
                marginTop: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '12px',
              }}
            >
              {savedNotice ? (
                <span style={{ color: '#2E7D32', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Check size={14} /> Key saved locally to browser!
                </span>
              ) : hasUserKey ? (
                <span style={{ color: '#2E7D32', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Check size={14} /> Custom BYOK Key is active and saved in browser.
                </span>
              ) : hasServerKey ? (
                <span style={{ color: '#1A73E8', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <ShieldCheck size={14} /> Server environment key configured (no personal key required).
                </span>
              ) : (
                <span style={{ color: '#E65100', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <AlertCircle size={14} /> No API key detected. Queries will use rule-based fallback without a key.
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--surface)',
          }}
        >
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Active: <strong>{PROVIDER_METAS[activeTab].name}</strong> ({isCustomModel ? customModelInput || 'custom' : selectedModel})
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={onClose}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border-strong)',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--text-secondary)',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              style={{
                padding: '8px 20px',
                borderRadius: '8px',
                backgroundColor: 'var(--accent)',
                color: 'white',
                fontSize: '13px',
                fontWeight: 600,
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              Apply Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
