import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, AlertCircle, RotateCcw, Loader2 } from 'lucide-react';
import { CometChatMessage } from '../types';

interface AudioMessageItemProps {
  message: CometChatMessage;
  isMe: boolean;
  onRetry?: (message: CometChatMessage) => void;
}

export const AudioMessageItem: React.FC<AudioMessageItemProps> = ({
  message,
  isMe,
  onRetry,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(message.durationSeconds || 0);
  const [hasError, setHasError] = useState(!message.audioUrl);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Format seconds to mm:ss
  const formatTime = (secs: number) => {
    if (isNaN(secs) || secs < 0) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Sync duration and reset error if audioUrl exists
  useEffect(() => {
    if (message.durationSeconds && message.durationSeconds > 0) {
      setDuration(message.durationSeconds);
    }
    if (message.audioUrl) {
      setHasError(false);
    }
  }, [message.durationSeconds, message.audioUrl]);

  // Cleanly release audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.onerror = null;
        audioRef.current.onended = null;
        audioRef.current.ontimeupdate = null;
        audioRef.current.onloadedmetadata = null;
        audioRef.current = null;
      }
    };
  }, []);

  const getOrCreateAudio = () => {
    if (!message.audioUrl) {
      setHasError(true);
      return null;
    }

    if (!audioRef.current || audioRef.current.src !== message.audioUrl) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.onerror = null;
      }

      const audio = new Audio(message.audioUrl);
      audioRef.current = audio;

      audio.onloadedmetadata = () => {
        if (audio.duration && !isNaN(audio.duration) && isFinite(audio.duration)) {
          setDuration(Math.round(audio.duration));
        }
        setIsLoadingAudio(false);
      };

      audio.ontimeupdate = () => {
        setCurrentTime(audio.currentTime);
      };

      audio.onended = () => {
        setIsPlaying(false);
        setCurrentTime(0);
      };

      audio.onerror = (e) => {
        console.warn('Audio playback error for message:', message.id, e);
        setHasError(true);
        setIsPlaying(false);
        setIsLoadingAudio(false);
      };
    }

    return audioRef.current;
  };

  const togglePlay = () => {
    const audio = getOrCreateAudio();
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      setIsLoadingAudio(true);
      setHasError(false);
      audio
        .play()
        .then(() => {
          setIsPlaying(true);
          setIsLoadingAudio(false);
        })
        .catch((err) => {
          console.warn('Audio playback play() failed:', err);
          setHasError(true);
          setIsPlaying(false);
          setIsLoadingAudio(false);
        });
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        minWidth: '220px',
        maxWidth: '300px',
      }}
    >
      {/* Voice Player Pill */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '10px 14px',
          borderRadius: isMe ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
          backgroundColor: isMe ? 'var(--accent)' : 'var(--surface-warm)',
          color: isMe ? '#FFFFFF' : 'var(--text-primary)',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
        }}
      >
        {/* Play / Pause / Loading button */}
        <button
          onClick={togglePlay}
          disabled={hasError || message.status === 'sending'}
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: isMe ? 'rgba(255, 255, 255, 0.22)' : 'var(--accent)',
            color: '#FFFFFF',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: hasError || message.status === 'sending' ? 'not-allowed' : 'pointer',
            flexShrink: 0,
            transition: 'background-color 0.15s ease, transform 0.1s ease',
          }}
          title={isPlaying ? 'Pause' : 'Play voice message'}
        >
          {isLoadingAudio ? (
            <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
          ) : isPlaying ? (
            <Pause size={14} />
          ) : (
            <Play size={14} style={{ marginLeft: '2px' }} />
          )}
        </button>

        {/* Audio scrub progress bar & duration */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <input
              type="range"
              min={0}
              max={duration || 1}
              step={0.1}
              value={currentTime}
              onChange={handleSeek}
              disabled={hasError || message.status === 'sending'}
              style={{
                width: '100%',
                height: '4px',
                accentColor: isMe ? '#FFFFFF' : 'var(--accent)',
                cursor: 'pointer',
              }}
            />
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '10.5px',
              opacity: isMe ? 0.9 : 0.75,
              fontWeight: 500,
            }}
          >
            <span>{isPlaying ? formatTime(currentTime) : 'Voice Message'}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      </div>

      {/* Status Bar / Error Banner / Retry option */}
      {message.status === 'sending' && (
        <div
          style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            paddingLeft: '4px',
          }}
        >
          <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
          <span>Uploading voice message...</span>
        </div>
      )}

      {message.status === 'failed' && (
        <div
          style={{
            fontSize: '11px',
            color: '#D32F2F',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingLeft: '4px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <AlertCircle size={12} />
            <span>Upload failed</span>
          </div>
          {onRetry && (
            <button
              onClick={() => onRetry(message)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                background: 'none',
                border: 'none',
                color: 'var(--accent)',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                padding: '2px 4px',
              }}
            >
              <RotateCcw size={11} />
              Retry
            </button>
          )}
        </div>
      )}

      {hasError && message.status !== 'failed' && (
        <div
          style={{
            fontSize: '10.5px',
            color: '#D32F2F',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            paddingLeft: '4px',
          }}
        >
          <AlertCircle size={11} />
          <span>Audio could not be loaded</span>
        </div>
      )}
    </div>
  );
};
