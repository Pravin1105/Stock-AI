import React, { useState, KeyboardEvent } from 'react';
import { Send, Mic } from 'lucide-react';
import { VoiceQueryModal } from './VoiceQueryModal';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  provider?: string;
  apiKey?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  provider,
  apiKey,
}) => {
  const [query, setQuery] = useState('');
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);

  const suggestions = [
    'Show me the top 5 best performing stores',
    'Forecast sales for store 5 item 10 for the next 7 days',
    'Show sales trend for item 15 in store 2',
    'Which 3 items sold the least in store 1?',
  ];

  const handleSend = () => {
    if (query.trim() && !disabled) {
      onSend(query.trim());
      setQuery('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <div className="input-dock">
        {/* Suggestion Chips */}
        <div className="suggestion-chips">
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              className="chip-btn"
              onClick={() => onSend(s)}
              disabled={disabled}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Input Box */}
        <div className="input-box-container">
          <textarea
            className="chat-textarea"
            rows={1}
            placeholder="Ask a demand forecasting or sales question (e.g. 'Top 5 stores', 'Forecast for store 3 item 5')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {/* Ask Stock AI with Voice Trigger Button */}
            <button
              type="button"
              onClick={() => setIsVoiceModalOpen(true)}
              disabled={disabled}
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                backgroundColor: 'var(--surface-warm)',
                color: 'var(--accent)',
                border: '1px solid var(--border-strong)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: disabled ? 'not-allowed' : 'pointer',
                flexShrink: 0,
                transition: 'all 0.15s ease',
              }}
              title="Ask Stock AI with voice (Spoken Query & Review)"
            >
              <Mic size={16} />
            </button>

            {/* Send Text Query Button */}
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={!query.trim() || disabled}
              title="Send Query"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Voice-to-Query Modal with Review Step */}
      <VoiceQueryModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        onSubmitQuery={(spokenQuery) => {
          onSend(spokenQuery);
        }}
        provider={provider}
        apiKey={apiKey}
      />
    </>
  );
};
