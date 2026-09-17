import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWorkspace } from './components/ChatWorkspace';
import { queryStockAI } from './services/api';
import { Conversation, ChatMessage } from './types';

const STORAGE_KEY = 'stock_ai_conversations_v1';

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

  // Sync with LocalStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch {
      // ignore
    }
  }, [conversations]);

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
      const response = await queryStockAI(queryText);

      const assistantMessage: ChatMessage = {
        id: 'msg-' + Date.now(),
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        text: response.explanation,
        intent: response.intent,
        result: response.result,
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
      const errorMessage: ChatMessage = {
        id: 'msg-' + Date.now(),
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        text: 'An error occurred while processing your request. Please check the backend connection or query format.',
        isLoading: false,
        error: String(err),
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

  return (
    <div className="app-container">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />
      <ChatWorkspace
        messages={activeConv ? activeConv.messages : []}
        onSend={handleSend}
        isLoading={isLoading}
      />
    </div>
  );
};
