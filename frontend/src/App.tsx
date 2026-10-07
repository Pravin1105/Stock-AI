import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWorkspace } from './components/ChatWorkspace';
import { ModelSelectorModal } from './components/ModelSelectorModal';
import { getAvailableModels, queryStockAI } from './services/api';
import { Conversation, ChatMessage, LLMProvider, ModelsCatalogResponse } from './types';

const STORAGE_KEY = 'stock_ai_conversations_v1';
const PROVIDER_KEY = 'stock_ai_selected_provider';
const MODEL_KEY = 'stock_ai_selected_model';
const BYOK_KEYS_STORAGE = 'stock_ai_byok_keys';

export const App: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch {
      // ignore
    }
    return [
      {
        id: 'default-1',
        title: 'Retail Demand Analysis',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [],
      },
    ];
  });

  const [activeId, setActiveId] = useState<string>(() => {
    return conversations[0]?.id || 'default-1';
  });

  const [isLoading, setIsLoading] = useState(false);

  // LLM Provider & BYOK State
  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>(() => {
    try {
      const saved = localStorage.getItem(PROVIDER_KEY);
      if (saved && ['gemini', 'openai', 'anthropic', 'groq'].includes(saved)) {
        return saved as LLMProvider;
      }
    } catch {
      // ignore
    }
    return 'gemini';
  });

  const [selectedModel, setSelectedModel] = useState<string>(() => {
    try {
      const saved = localStorage.getItem(MODEL_KEY);
      if (saved) return saved;
    } catch {
      // ignore
    }
    return 'gemini-2.0-flash';
  });

  const [byokKeys, setByokKeys] = useState<Record<string, string>>(() => {
    try {
      const saved = localStorage.getItem(BYOK_KEYS_STORAGE);
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore
    }
    return {};
  });

  const [modelsCatalog, setModelsCatalog] = useState<ModelsCatalogResponse | null>(null);
  const [isModelModalOpen, setIsModelModalOpen] = useState(false);

  // Fetch server models catalog on mount
  useEffect(() => {
    getAvailableModels()
      .then((catalog) => {
        setModelsCatalog(catalog);
      })
      .catch((err) => {
        console.warn('Could not load models catalog from server:', err);
      });
  }, []);

  // Sync Conversations with LocalStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch {
      // ignore
    }
  }, [conversations]);

  // Sync Provider & Model
  const handleSelectProvider = (prov: LLMProvider) => {
    setSelectedProvider(prov);
    try {
      localStorage.setItem(PROVIDER_KEY, prov);
    } catch {
      // ignore
    }
  };

  const handleSelectModel = (mod: string) => {
    setSelectedModel(mod);
    try {
      localStorage.setItem(MODEL_KEY, mod);
    } catch {
      // ignore
    }
  };

  const handleSaveKey = (prov: LLMProvider, key: string) => {
    setByokKeys((prev) => {
      const updated = { ...prev, [prov]: key };
      try {
        localStorage.setItem(BYOK_KEYS_STORAGE, JSON.stringify(updated));
      } catch {
        // ignore
      }
      return updated;
    });
  };

  const handleClearKey = (prov: LLMProvider) => {
    setByokKeys((prev) => {
      const updated = { ...prev };
      delete updated[prov];
      try {
        localStorage.setItem(BYOK_KEYS_STORAGE, JSON.stringify(updated));
      } catch {
        // ignore
      }
      return updated;
    });
  };

  const activeConv = conversations.find((c) => c.id === activeId) || conversations[0];

  const handleNewConversation = () => {
    const newConv: Conversation = {
      id: 'conv-' + Date.now(),
      title: 'New Analysis',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveId(newConv.id);
  };

  const handleDeleteConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== id);
      if (filtered.length === 0) {
        const fallback: Conversation = {
          id: 'conv-' + Date.now(),
          title: 'New Analysis',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          messages: [],
        };
        setActiveId(fallback.id);
        return [fallback];
      }
      if (activeId === id) {
        setActiveId(filtered[0].id);
      }
      return filtered;
    });
  };

  const handleSend = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: 'msg-' + Date.now(),
      sender: 'user',
      timestamp: new Date().toISOString(),
      text: queryText,
    };

    const loadingMessage: ChatMessage = {
      id: 'msg-loading-' + Date.now(),
      sender: 'assistant',
      timestamp: new Date().toISOString(),
      text: '',
      isLoading: true,
    };

    // Update conversation with user message and loading placeholder
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === activeId) {
          const isFirst = c.messages.length === 0;
          return {
            ...c,
            title: isFirst ? (queryText.length > 28 ? queryText.slice(0, 28) + '...' : queryText) : c.title,
            updatedAt: new Date().toISOString(),
            messages: [...c.messages, userMessage, loadingMessage],
          };
        }
        return c;
      })
    );

    setIsLoading(true);

    try {
      const response = await queryStockAI(queryText, {
        provider: selectedProvider,
        model: selectedModel,
        apiKey: byokKeys[selectedProvider],
      });

      const assistantMessage: ChatMessage = {
        id: 'msg-' + Date.now(),
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        text: response.explanation,
        intent: response.intent,
        result: response.result,
        provider: response.provider || selectedProvider,
        model: response.model || selectedModel,
        isLoading: false,
      };

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeId) {
            return {
              ...c,
              messages: c.messages.filter((m) => !m.isLoading).concat(assistantMessage),
            };
          }
          return c;
        })
      );
    } catch (err: any) {
      const errorDetail = err?.message || String(err);
      const errorMessage: ChatMessage = {
        id: 'msg-' + Date.now(),
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        text: `Error processing query: ${errorDetail}`,
        provider: selectedProvider,
        model: selectedModel,
        isLoading: false,
        error: errorDetail,
      };

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeId) {
            return {
              ...c,
              messages: c.messages.filter((m) => !m.isLoading).concat(errorMessage),
            };
          }
          return c;
        })
      );
    } finally {
      setIsLoading(false);
    }
  };

  const hasKeyConfigured = Boolean(
    byokKeys[selectedProvider] ||
    modelsCatalog?.providers[selectedProvider]?.has_server_key
  );

  return (
    <div className="app-container">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
        onOpenSettings={() => setIsModelModalOpen(true)}
      />

      <ChatWorkspace
        messages={activeConv ? activeConv.messages : []}
        onSend={handleSend}
        isLoading={isLoading}
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        hasKeyConfigured={hasKeyConfigured}
        onOpenModelModal={() => setIsModelModalOpen(true)}
      />
      <ModelSelectorModal
        isOpen={isModelModalOpen}
        onClose={() => setIsModelModalOpen(false)}
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        onSelectProvider={handleSelectProvider}
        onSelectModel={handleSelectModel}
        byokKeys={byokKeys}
        onSaveKey={handleSaveKey}
        onClearKey={handleClearKey}
        modelsCatalog={modelsCatalog}
      />
    </div>
  );
};

