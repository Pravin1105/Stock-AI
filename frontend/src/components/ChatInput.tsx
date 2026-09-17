import React, { useState, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [query, setQuery] = useState('');

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
  );
};
