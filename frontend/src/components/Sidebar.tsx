import React from 'react';
import { MessageSquare, Plus, Trash2, TrendingUp } from 'lucide-react';
import { Conversation } from '../types';

interface SidebarProps {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}) => {
  return (
    <aside className="sidebar">
      {/* Sidebar Header */}
      <div style={{ padding: '20px 16px 12px 16px', borderBottom: '1px solid var(--border-strong)' }}>
        <button
          onClick={onNew}
          style={{
            width: '100%',
            backgroundColor: 'var(--accent)',
            color: 'white',
            padding: '10px 14px',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            fontWeight: 600,
            fontSize: '14px',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <Plus size={18} />
          New Analysis
        </button>
      </div>

      {/* Conversation List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 8px' }}>
        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', padding: '6px 12px' }}>
          Conversations
        </div>

        {conversations.length === 0 ? (
          <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            No previous conversations.
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeId;
            return (
              <div
                key={conv.id}
                onClick={() => onSelect(conv.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  marginBottom: '4px',
                  cursor: 'pointer',
                  backgroundColor: isActive ? 'var(--bg-primary)' : 'transparent',
                  border: isActive ? '1px solid var(--border-strong)' : '1px solid transparent',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: '13px',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                  <MessageSquare size={16} color={isActive ? 'var(--accent)' : 'var(--text-muted)'} style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {conv.title || 'Untitled Query'}
                  </span>
                </div>
                <button
                  onClick={(e) => onDelete(conv.id, e)}
                  title="Delete conversation"
                  style={{
                    opacity: isActive ? 0.7 : 0.2,
                    padding: '2px 4px',
                    borderRadius: '4px',
                  }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.opacity = '1')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.opacity = isActive ? '0.7' : '0.2')}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div style={{ padding: '16px', borderTop: '1px solid var(--border-strong)', fontSize: '12px', color: 'var(--text-secondary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
          <TrendingUp size={15} color="var(--accent)" />
          Stock AI Engine v1.0
        </div>
        <div>Two-Stage LLM Analytics</div>
      </div>
    </aside>
  );
};
