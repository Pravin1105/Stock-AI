import React, { useState } from 'react';
import { BarChart3, Table as TableIcon, Cpu } from 'lucide-react';
import { ChatMessage } from '../types';

interface MessageItemProps {
  message: ChatMessage;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const [viewMode, setViewMode] = useState<'both' | 'chart' | 'table'>('both');

  if (message.sender === 'user') {
    return (
      <div className="message-row user">
        <div className="user-bubble">{message.text}</div>
      </div>
    );
  }

  const { intent, result, text, isLoading } = message;

  if (isLoading) {
    return (
      <div className="message-row assistant">
        <div className="assistant-card" style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '20px', height: '20px', border: '3px solid var(--border-strong)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            Parsing query intent & executing analytics engine...
          </span>
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  return (
    <div className="message-row assistant">
      <div className="assistant-card">
        {/* Header: Intent Badge & Routing State */}
        {intent && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`status-pill ${intent.task}`}>
                <Cpu size={13} />
                {intent.task}
              </span>
              {intent.scope.store_id && (
                <span style={{ fontSize: '12px', background: 'var(--bg-primary)', border: '1px solid var(--border-strong)', padding: '2px 8px', borderRadius: '12px', fontWeight: 500 }}>
                  Store: #{intent.scope.store_id}
                </span>
              )}
              {intent.scope.item_id && (
                <span style={{ fontSize: '12px', background: 'var(--bg-primary)', border: '1px solid var(--border-strong)', padding: '2px 8px', borderRadius: '12px', fontWeight: 500 }}>
                  Item: #{intent.scope.item_id}
                </span>
              )}
            </div>

            {/* Toggle View Mode */}
            {result && result.records.length > 0 && (
              <div style={{ display: 'flex', background: 'var(--bg-primary)', border: '1px solid var(--border-strong)', borderRadius: '8px', padding: '2px' }}>
                <button
                  onClick={() => setViewMode('both')}
                  style={{ padding: '4px 8px', fontSize: '12px', borderRadius: '6px', backgroundColor: viewMode === 'both' ? 'white' : 'transparent', fontWeight: viewMode === 'both' ? 600 : 400 }}
                >
                  Overview
                </button>
                <button
                  onClick={() => setViewMode('chart')}
                  style={{ padding: '4px 8px', fontSize: '12px', borderRadius: '6px', backgroundColor: viewMode === 'chart' ? 'white' : 'transparent', fontWeight: viewMode === 'chart' ? 600 : 400 }}
                >
                  <BarChart3 size={13} style={{ display: 'inline', marginRight: '4px' }} /> Chart
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  style={{ padding: '4px 8px', fontSize: '12px', borderRadius: '6px', backgroundColor: viewMode === 'table' ? 'white' : 'transparent', fontWeight: viewMode === 'table' ? 600 : 400 }}
                >
                  <TableIcon size={13} style={{ display: 'inline', marginRight: '4px' }} /> Table
                </button>
              </div>
            )}
          </div>
        )}

        {/* Narrative Explanation */}
        <div style={{ fontSize: '14.5px', color: 'var(--text-primary)', whiteSpace: 'pre-line', lineHeight: 1.6 }}>
          {formatMarkdownText(text)}
        </div>

        {/* Summary Metrics */}
        {result && result.summary && result.summary.record_count > 0 && (
          <div className="metrics-grid">
            {result.summary.total_sales !== undefined && (
              <div className="metric-card">
                <span className="metric-label">Total Volume</span>
                <span className="metric-value">{result.summary.total_sales.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
              </div>
            )}
            {result.summary.mean_sales !== undefined && (
              <div className="metric-card">
                <span className="metric-label">Daily Avg</span>
                <span className="metric-value">{result.summary.mean_sales.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
              </div>
            )}
            {result.summary.max_sales !== undefined && (
              <div className="metric-card">
                <span className="metric-label">Peak</span>
                <span className="metric-value">{result.summary.max_sales.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
              </div>
            )}
            <div className="metric-card">
              <span className="metric-label">Data Points</span>
              <span className="metric-value">{result.summary.record_count}</span>
            </div>
          </div>
        )}

        {/* Chart Visualization */}
        {result && result.records.length > 0 && (viewMode === 'both' || viewMode === 'chart') && (
          <div className="chart-container">
            <div className="chart-header">
              <span>{result.task === 'ranking' ? 'Sales Distribution' : result.task === 'forecast' ? '7-Day Demand Forecast' : 'Historical Trend'}</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{result.metadata?.model || 'Dataset Source'}</span>
            </div>
            {result.task === 'ranking' ? (
              <BarChartSVG records={result.records} />
            ) : (
              <LineChartSVG records={result.records} isForecast={result.task === 'forecast'} />
            )}
          </div>
        )}

        {/* Tabular Records */}
        {result && result.records.length > 0 && (viewMode === 'both' || viewMode === 'table') && (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  {result.columns.map((col) => (
                    <th key={col}>{col.replace(/_/g, ' ')}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.records.slice(0, 10).map((row, idx) => (
                  <tr key={idx}>
                    {result.columns.map((col) => {
                      const val = row[col];
                      const formatted = typeof val === 'number' ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(val);
                      return <td key={col}>{formatted}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            {result.records.length > 10 && (
              <div style={{ padding: '8px 14px', fontSize: '12px', color: 'var(--text-muted)', background: 'var(--bg-primary)' }}>
                Showing first 10 of {result.records.length} records.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/* Formatter for bold text and bullet points */
function formatMarkdownText(content: string) {
  const lines = content.split('\n');
  return lines.map((line, i) => {
    // Bold matches **text**
    const parts = line.split(/(\*\*.*?\*\*)/g);
    return (
      <p key={i} style={{ margin: line.trim() === '' ? '8px 0' : '3px 0' }}>
        {parts.map((part, idx) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={idx}>{part.slice(2, -2)}</strong>;
          }
          return part;
        })}
      </p>
    );
  });
}

/* Responsive SVG Bar Chart Component */
const BarChartSVG: React.FC<{ records: any[] }> = ({ records }) => {
  const maxVal = Math.max(...records.map((r) => r.total_sales || r.sales || 1));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '8px 0' }}>
      {records.slice(0, 5).map((r, i) => {
        const label = r.store !== undefined ? `Store ${r.store}` : r.item !== undefined ? `Item ${r.item}` : `#${i + 1}`;
        const val = r.total_sales || r.sales || 0;
        const widthPct = Math.max(8, (val / maxVal) * 100);

        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '12px' }}>
            <span style={{ width: '65px', textAlign: 'right', fontWeight: 600, color: 'var(--text-secondary)' }}>{label}</span>
            <div style={{ flex: 1, backgroundColor: 'var(--bg-primary)', height: '22px', borderRadius: '4px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${widthPct}%`,
                  height: '100%',
                  backgroundColor: i === 0 ? 'var(--accent)' : 'var(--border-strong)',
                  borderRadius: '4px',
                  transition: 'width 0.4s ease',
                  display: 'flex',
                  alignItems: 'center',
                  paddingLeft: '8px',
                  color: i === 0 ? 'white' : 'var(--text-primary)',
                  fontWeight: 600,
                  fontSize: '11px',
                }}
              >
                {val.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

/* Responsive SVG Line Chart Component */
const LineChartSVG: React.FC<{ records: any[]; isForecast?: boolean }> = ({ records, isForecast }) => {
  const valKey = isForecast ? 'forecasted_sales' : 'total_sales';
  const vals = records.map((r) => r[valKey] || 0);
  const minVal = Math.min(...vals);
  const maxVal = Math.max(...vals);
  const range = maxVal - minVal || 1;

  const width = 500;
  const height = 150;
  const padding = 20;

  const points = records.map((r, i) => {
    const x = padding + (i / (records.length - 1 || 1)) * (width - 2 * padding);
    const y = height - padding - (((r[valKey] || 0) - minVal) / range) * (height - 2 * padding);
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(' L ')}`;

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', maxHeight: '160px' }}>
        {/* Horizontal grid lines */}
        <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#EEEEEE" strokeDasharray="3,3" />
        <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="#EEEEEE" strokeDasharray="3,3" />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#EEEEEE" />

        {/* Data Line */}
        <path d={pathD} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Point markers */}
        {records.map((_r, i) => {
          const [cx, cy] = points[i].split(',').map(Number);
          return (
            <circle key={i} cx={cx} cy={cy} r="3.5" fill="white" stroke="var(--accent)" strokeWidth="2" />
          );
        })}
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', padding: '0 8px' }}>
        <span>{records[0]?.date || 'Start'}</span>
        <span>{records[Math.floor(records.length / 2)]?.date || 'Mid'}</span>
        <span>{records[records.length - 1]?.date || 'End'}</span>
      </div>
    </div>
  );
};
