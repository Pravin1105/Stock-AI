import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Send,
  Users,
  X,
  Minimize2,
  Maximize2,
  Radio,
  Mic,
  Square,
  Trash2,
  Play,
  Pause,
  AlertCircle,
} from 'lucide-react';
import {
  initCometChat,
  loginCometChatUser,
  sendCometChatTextMessage,
  sendCometChatAudioMessage,
  fetchCometChatMessageHistory,
  addCometChatMessageListener,
  removeCometChatMessageListener,
  getCometChatConfig,
} from '../services/cometchat';
import { AudioRecorder, RecordedAudio } from '../services/audioRecorder';
import { AudioMessageItem } from './AudioMessageItem';
import { CometChatMessage, CometChatUser } from '../types';

interface CometChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CometChatPanel: React.FC<CometChatPanelProps> = ({ isOpen, onClose }) => {
  const [availableUsers, setAvailableUsers] = useState<CometChatUser[]>([
    { uid: 'analyst_1', name: 'Senior Demand Analyst', role: 'Analyst' },
    { uid: 'analyst_2', name: 'Inventory Operations Lead', role: 'Operations' },
  ]);
  const [currentUserUid, setCurrentUserUid] = useState<string>('analyst_1');
  const [targetUserUid, setTargetUserUid] = useState<string>('analyst_2');
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isMockMode, setIsMockMode] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('Initializing CometChat...');
  const [messages, setMessages] = useState<CometChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  // Voice recording states
  const [isRecording, setIsRecording] = useState(false);
  const [recordingElapsed, setRecordingElapsed] = useState(0);
  const [recordedAudio, setRecordedAudio] = useState<RecordedAudio | null>(null);
  const [recordingError, setRecordingError] = useState<string | null>(null);
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recorderRef = useRef<AudioRecorder | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);

  // Format seconds to mm:ss
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Load config & default test users
  useEffect(() => {
    getCometChatConfig().then((cfg) => {
      if (cfg.default_users && cfg.default_users.length >= 2) {
        setAvailableUsers(cfg.default_users);
      }
    });
  }, []);

  // Initialize and connect current user
  useEffect(() => {
    let isMounted = true;

    async function connect() {
      setIsConnecting(true);
      setStatusMessage('Initializing CometChat SDK...');

      try {
        const initRes = await initCometChat();
        if (!isMounted) return;

        if (initRes.error) {
          console.warn('CometChat init warning:', initRes.error);
        }

        setStatusMessage(`Logging in as ${currentUserUid}...`);
        const session = await loginCometChatUser(currentUserUid);

        if (!isMounted) return;
        setIsConnected(session.isLoggedIn);
        setIsMockMode(session.isMock);
        setStatusMessage(
          session.isMock
            ? 'Demo Channel Active (Simulated SDK)'
            : 'CometChat Live Connected'
        );

        // Fetch initial conversation history
        const history = await fetchCometChatMessageHistory(targetUserUid);
        if (isMounted) setMessages(history);
      } catch (err: any) {
        if (!isMounted) return;
        console.warn('CometChat connection status:', err);
        setStatusMessage(`Connection warning: ${err?.message || err}`);
      } finally {
        if (isMounted) setIsConnecting(false);
      }
    }

    if (isOpen) {
      connect();
    }

    return () => {
      isMounted = false;
    };
  }, [isOpen, currentUserUid, targetUserUid]);

  // Real-time message listener (strictly listens for target user to avoid self-echo)
  useEffect(() => {
    if (!isOpen) return;

    const listenerId = `listener_${currentUserUid}_${Date.now()}`;
    addCometChatMessageListener(listenerId, (incomingMsg: CometChatMessage) => {
      if (incomingMsg.senderUid === targetUserUid && incomingMsg.receiverUid === currentUserUid) {
        setMessages((prev) => {
          if (prev.some((m) => m.id === incomingMsg.id)) return prev;
          return [...prev, incomingMsg];
        });
      }
    });

    return () => {
      removeCometChatMessageListener(listenerId);
    };
  }, [isOpen, currentUserUid, targetUserUid]);

  // Cleanup audio preview & recording on unmount
  useEffect(() => {
    return () => {
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
        previewAudioRef.current = null;
      }
      if (recorderRef.current) {
        recorderRef.current.discardRecording();
        recorderRef.current = null;
      }
    };
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSwitchUser = (newUid: string) => {
    if (newUid === currentUserUid) return;
    handleDiscardRecording();
    const newTarget = availableUsers.find((u) => u.uid !== newUid)?.uid || 'analyst_2';
    setCurrentUserUid(newUid);
    setTargetUserUid(newTarget);
    setMessages([]);
  };

  const handleSendText = async () => {
    const textToSend = inputText.trim();
    if (!textToSend || isSending) return;

    setIsSending(true);
    try {
      const sentMsg = await sendCometChatTextMessage(targetUserUid, textToSend);
      setInputText('');
      setMessages((prev) => {
        if (prev.some((m) => m.id === sentMsg.id)) return prev;
        return [...prev, sentMsg];
      });
    } catch (err: any) {
      console.error('Failed to send CometChat message:', err);
      alert(`Send failed: ${err?.message || err}`);
    } finally {
      setIsSending(false);
    }
  };

  // --- Voice Message Handlers ---

  const handleStartRecording = async () => {
    setRecordingError(null);
    setRecordedAudio(null);
    setIsPreviewPlaying(false);
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current = null;
    }

    try {
      const recorder = new AudioRecorder({
        maxDurationSeconds: 60,
      });
      recorderRef.current = recorder;

      await recorder.startRecording({
        maxDurationSeconds: 60,
        onTick: (elapsed) => {
          setRecordingElapsed(elapsed);
        },
        onMaxDurationReached: () => {
          handleStopRecording();
        },
      });

      setIsRecording(true);
      setRecordingElapsed(0);
    } catch (err: any) {
      console.warn('Microphone error:', err);
      setRecordingError(err?.message || 'Microphone access failed. Please verify permissions.');
      setIsRecording(false);
    }
  };

  const handleStopRecording = async () => {
    if (!recorderRef.current) return;
    try {
      const audioResult = await recorderRef.current.stopRecording();
      setRecordedAudio(audioResult);
      setIsRecording(false);
    } catch (err: any) {
      console.warn('Stop recording failed:', err);
      setRecordingError(err?.message || 'Could not process audio recording.');
      setIsRecording(false);
    }
  };

  const handleDiscardRecording = () => {
    if (recorderRef.current) {
      recorderRef.current.discardRecording();
      recorderRef.current = null;
    }
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current = null;
    }
    setIsRecording(false);
    setRecordingElapsed(0);
    setRecordedAudio(null);
    setIsPreviewPlaying(false);
    setRecordingError(null);
  };

  const togglePreviewPlay = () => {
    if (!recordedAudio) return;

    if (isPreviewPlaying && previewAudioRef.current) {
      previewAudioRef.current.pause();
      setIsPreviewPlaying(false);
      return;
    }

    if (!previewAudioRef.current) {
      const audio = new Audio(recordedAudio.url);
      previewAudioRef.current = audio;
      audio.onended = () => setIsPreviewPlaying(false);
      audio.onerror = () => setIsPreviewPlaying(false);
    }

    previewAudioRef.current
      .play()
      .then(() => setIsPreviewPlaying(true))
      .catch((err) => {
        console.warn('Preview playback failed:', err);
        setIsPreviewPlaying(false);
      });
  };

  const handleSendVoiceMessage = async (audioToSend = recordedAudio) => {
    if (!audioToSend || isSending) return;

    const currentUserObj = availableUsers.find((u) => u.uid === currentUserUid) || availableUsers[0];
    const optimisticId = `temp-audio-${Date.now()}`;
    const optimisticMsg: CometChatMessage = {
      id: optimisticId,
      senderUid: currentUserUid,
      senderName: currentUserObj.name,
      receiverUid: targetUserUid,
      type: 'audio',
      audioUrl: audioToSend.url,
      durationSeconds: audioToSend.durationSeconds,
      timestamp: Date.now(),
      status: 'sending',
      audioFile: audioToSend.file,
    };

    // Optimistically add to messages
    setMessages((prev) => [...prev, optimisticMsg]);
    setIsSending(true);

    // Reset recording dock immediately
    handleDiscardRecording();

    try {
      const sentMsg = await sendCometChatAudioMessage(
        targetUserUid,
        audioToSend.file,
        audioToSend.durationSeconds
      );

      // Replace optimistic message with confirmed sent message
      setMessages((prev) =>
        prev.map((m) => (m.id === optimisticId ? { ...sentMsg, status: 'sent' } : m))
      );
    } catch (err: any) {
      console.error('Failed to send voice message:', err);
      // Mark optimistic message as failed
      setMessages((prev) =>
        prev.map((m) =>
          m.id === optimisticId
            ? { ...m, status: 'failed', error: err?.message || 'Send failed' }
            : m
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleRetryAudio = async (failedMsg: CometChatMessage) => {
    if (!failedMsg.audioFile || isSending) return;

    setMessages((prev) =>
      prev.map((m) => (m.id === failedMsg.id ? { ...m, status: 'sending', error: undefined } : m))
    );
    setIsSending(true);

    try {
      const sentMsg = await sendCometChatAudioMessage(
        failedMsg.receiverUid,
        failedMsg.audioFile,
        failedMsg.durationSeconds
      );

      setMessages((prev) =>
        prev.map((m) => (m.id === failedMsg.id ? { ...sentMsg, status: 'sent' } : m))
      );
    } catch (err: any) {
      console.error('Retry voice message failed:', err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === failedMsg.id
            ? { ...m, status: 'failed', error: err?.message || 'Retry failed' }
            : m
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  if (!isOpen) return null;

  const currentUserObj = availableUsers.find((u) => u.uid === currentUserUid) || availableUsers[0];
  const targetUserObj = availableUsers.find((u) => u.uid === targetUserUid) || availableUsers[1];

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        width: isExpanded ? '460px' : '380px',
        height: isExpanded ? '640px' : '520px',
        backgroundColor: '#FFFFFF',
        borderRadius: '16px',
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.16)',
        border: '1px solid var(--border-strong)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 999,
        overflow: 'hidden',
        transition: 'width 0.2s ease, height 0.2s ease',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--border)',
          backgroundColor: 'var(--surface-warm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '30px',
              height: '30px',
              borderRadius: '8px',
              backgroundColor: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent)',
            }}
          >
            <MessageSquare size={16} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--text-primary)' }}>
                CometChat Collaboration
              </span>
              <span
                style={{
                  fontSize: '9.5px',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: '4px',
                  backgroundColor: isMockMode ? '#FFF3E0' : '#E8F5E9',
                  color: isMockMode ? '#E65100' : '#2E7D32',
                }}
              >
                {isMockMode ? 'DEMO' : 'LIVE'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px' }}>
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  backgroundColor: isConnected ? '#34A853' : '#FBBC05',
                }}
              />
              <span style={{ color: 'var(--text-secondary)' }}>
                {isConnecting ? 'Connecting...' : statusMessage}
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            style={{ padding: '6px', borderRadius: '6px', color: 'var(--text-muted)' }}
            title={isExpanded ? 'Minimize' : 'Expand'}
          >
            {isExpanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
          <button
            onClick={onClose}
            style={{ padding: '6px', borderRadius: '6px', color: 'var(--text-muted)' }}
            title="Close"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Test User Switcher Bar */}
      <div
        style={{
          padding: '8px 12px',
          backgroundColor: '#FAFAFA',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
          <Users size={13} />
          <span>Active Persona:</span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          {availableUsers.map((u) => {
            const isSelected = u.uid === currentUserUid;
            return (
              <button
                key={u.uid}
                onClick={() => handleSwitchUser(u.uid)}
                style={{
                  padding: '3px 8px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: isSelected ? 700 : 500,
                  backgroundColor: isSelected ? 'var(--accent)' : 'white',
                  color: isSelected ? 'white' : 'var(--text-secondary)',
                  border: isSelected ? '1px solid var(--accent)' : '1px solid var(--border)',
                  cursor: 'pointer',
                }}
              >
                {u.name.split(' ')[0]} ({u.role || u.uid})
              </button>
            );
          })}
        </div>
      </div>

      {/* Target conversation recipient info */}
      <div
        style={{
          padding: '6px 14px',
          backgroundColor: '#F5F5F5',
          borderBottom: '1px solid var(--border)',
          fontSize: '11px',
          color: 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>
          Chatting with: <strong>{targetUserObj.name}</strong> ({targetUserObj.uid})
        </span>
        <span
          style={{
            fontSize: '10px',
            backgroundColor: isMockMode ? '#FFF3E0' : '#E8F5E9',
            color: isMockMode ? '#E65100' : '#2E7D32',
            padding: '1px 6px',
            borderRadius: '4px',
            fontWeight: 600,
          }}
        >
          {isMockMode ? 'MOCK CHANNEL' : 'COMETCHAT LIVE'}
        </span>
      </div>

      {/* Error alert banner */}
      {recordingError && (
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: '#FFEBEE',
            borderBottom: '1px solid #FFCDD2',
            fontSize: '11.5px',
            color: '#C62828',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertCircle size={14} style={{ flexShrink: 0 }} />
            <span>{recordingError}</span>
          </div>
          <button
            onClick={() => setRecordingError(null)}
            style={{ background: 'none', border: 'none', color: '#C62828', cursor: 'pointer' }}
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* Message Stream */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          backgroundColor: '#FFFFFF',
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '12.5px',
              padding: '20px',
            }}
          >
            <Radio size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
            <div>
              No messages yet between {currentUserObj.name.split(' ')[0]} and{' '}
              {targetUserObj.name.split(' ')[0]}.
            </div>
            <div style={{ marginTop: '4px', fontSize: '11px' }}>
              Send a text or voice message below to start your conversation. Switch personas above to test receiving!
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isMe = msg.senderUid === currentUserUid;
            return (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isMe ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    fontSize: '10px',
                    color: 'var(--text-muted)',
                    marginBottom: '2px',
                    paddingLeft: '4px',
                    paddingRight: '4px',
                  }}
                >
                  {isMe ? 'You' : msg.senderName || msg.senderUid} ·{' '}
                  {new Date(msg.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>

                {msg.type === 'audio' ? (
                  <AudioMessageItem message={msg} isMe={isMe} onRetry={handleRetryAudio} />
                ) : (
                  <div
                    style={{
                      maxWidth: '82%',
                      padding: '8px 12px',
                      borderRadius: isMe ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                      backgroundColor: isMe ? 'var(--accent)' : 'var(--surface-warm)',
                      color: isMe ? 'white' : 'var(--text-primary)',
                      fontSize: '13px',
                      lineHeight: 1.45,
                      wordBreak: 'break-word',
                    }}
                  >
                    {msg.text}
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Dock (Text or Voice Mode) */}
      <div
        style={{
          padding: '10px 12px',
          borderTop: '1px solid var(--border)',
          backgroundColor: '#FFFFFF',
        }}
      >
        {isRecording ? (
          /* Active Recording Bar */
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: '#FFEBEE',
              borderRadius: '24px',
              padding: '6px 14px',
              border: '1px solid #FFCDD2',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  width: '9px',
                  height: '9px',
                  borderRadius: '50%',
                  backgroundColor: '#D32F2F',
                  display: 'inline-block',
                  animation: 'pulse 1s infinite alternate',
                }}
              />
              <span style={{ fontSize: '12.5px', fontWeight: 600, color: '#C62828' }}>
                Recording... {formatTime(recordingElapsed)} / 01:00
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={handleDiscardRecording}
                style={{
                  padding: '6px',
                  borderRadius: '50%',
                  border: 'none',
                  backgroundColor: 'transparent',
                  color: '#C62828',
                  cursor: 'pointer',
                }}
                title="Discard recording"
              >
                <Trash2 size={16} />
              </button>
              <button
                onClick={handleStopRecording}
                style={{
                  padding: '6px 12px',
                  borderRadius: '16px',
                  border: 'none',
                  backgroundColor: '#D32F2F',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                }}
                title="Stop recording"
              >
                <Square size={13} />
                <span>Done</span>
              </button>
            </div>
          </div>
        ) : recordedAudio ? (
          /* Post-Recording Review & Preview Dock */
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: 'var(--surface-warm)',
              borderRadius: '24px',
              padding: '6px 12px',
              border: '1px solid var(--border-strong)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={togglePreviewPlay}
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--accent)',
                  color: 'white',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                }}
                title={isPreviewPlaying ? 'Pause preview' : 'Play preview'}
              >
                {isPreviewPlaying ? <Pause size={13} /> : <Play size={13} style={{ marginLeft: '1px' }} />}
              </button>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>
                Voice Message ({formatTime(recordedAudio.durationSeconds)})
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onClick={handleDiscardRecording}
                style={{
                  padding: '6px',
                  borderRadius: '50%',
                  border: 'none',
                  backgroundColor: 'transparent',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                }}
                title="Discard voice message"
              >
                <Trash2 size={15} />
              </button>
              <button
                onClick={() => handleSendVoiceMessage(recordedAudio)}
                disabled={isSending}
                style={{
                  padding: '5px 12px',
                  borderRadius: '16px',
                  border: 'none',
                  backgroundColor: 'var(--accent)',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                }}
                title="Send voice message"
              >
                <Send size={13} />
                <span>Send Voice</span>
              </button>
            </div>
          </div>
        ) : (
          /* Default Text Input + Voice Record Button */
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="text"
              placeholder={`Message ${targetUserObj.name.split(' ')[0]}...`}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendText();
                }
              }}
              disabled={isSending || isConnecting}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '20px',
                border: '1px solid var(--border-strong)',
                fontSize: '13px',
                outline: 'none',
              }}
            />

            {/* Voice record trigger button */}
            <button
              onClick={handleStartRecording}
              disabled={isSending || isConnecting}
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                backgroundColor: 'white',
                color: 'var(--accent)',
                border: '1px solid var(--border-strong)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                flexShrink: 0,
                transition: 'all 0.15s ease',
              }}
              title="Record voice message"
            >
              <Mic size={16} />
            </button>

            {/* Send text button */}
            <button
              onClick={handleSendText}
              disabled={!inputText.trim() || isSending || isConnecting}
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                backgroundColor: inputText.trim() ? 'var(--accent)' : '#E0E0E0',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: inputText.trim() ? 'pointer' : 'default',
                border: 'none',
                flexShrink: 0,
                transition: 'background-color 0.15s ease',
              }}
              title="Send text message"
            >
              <Send size={15} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
