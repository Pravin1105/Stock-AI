import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  Square,
  Play,
  Pause,
  AlertCircle,
  X,
  RotateCcw,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import { AudioRecorder, RecordedAudio } from '../services/audioRecorder';
import { transcribeVoiceQuery } from '../services/api';

interface VoiceQueryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmitQuery: (reviewedQuery: string) => void;
  provider?: string;
  apiKey?: string;
}

type VoiceStep = 'record' | 'transcribing' | 'review' | 'error';

export const VoiceQueryModal: React.FC<VoiceQueryModalProps> = ({
  isOpen,
  onClose,
  onSubmitQuery,
  provider,
  apiKey,
}) => {
  const [step, setStep] = useState<VoiceStep>('record');
  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [recordedAudio, setRecordedAudio] = useState<RecordedAudio | null>(null);
  const [transcript, setTranscript] = useState('');
  const [transcribeProvider, setTranscribeProvider] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Reset state when opening
  useEffect(() => {
    if (isOpen) {
      setStep('record');
      setIsRecording(false);
      setElapsed(0);
      setRecordedAudio(null);
      setTranscript('');
      setErrorMessage(null);
      setIsPlayingAudio(false);
    } else {
      cleanup();
    }
  }, [isOpen]);

  const cleanup = () => {
    if (recorderRef.current) {
      recorderRef.current.discardRecording();
      recorderRef.current = null;
    }
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current = null;
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const handleStartRecording = async () => {
    setErrorMessage(null);
    try {
      const recorder = new AudioRecorder({ maxDurationSeconds: 60 });
      recorderRef.current = recorder;

      await recorder.startRecording({
        maxDurationSeconds: 60,
        onTick: (secs) => setElapsed(secs),
        onMaxDurationReached: () => handleStopAndTranscribe(),
      });

      setIsRecording(true);
      setElapsed(0);
    } catch (err: any) {
      console.warn('Microphone error in voice query:', err);
      setErrorMessage(err?.message || 'Could not access microphone.');
      setStep('error');
      setIsRecording(false);
    }
  };

  const handleStopAndTranscribe = async () => {
    if (!recorderRef.current) return;

    setIsRecording(false);
    setStep('transcribing');

    try {
      const audio = await recorderRef.current.stopRecording();
      setRecordedAudio(audio);

      // Call backend STT endpoint
      const result = await transcribeVoiceQuery(audio.blob, {
        provider,
        apiKey,
      });

      if (!result.transcript || !result.transcript.trim()) {
        throw new Error('Transcription returned empty text. Please try speaking again.');
      }

      setTranscript(result.transcript.trim());
      setTranscribeProvider(result.provider || 'AI STT');
      setStep('review');
    } catch (err: any) {
      console.error('Transcription failed:', err);
      setErrorMessage(err?.message || 'Audio transcription failed. Please try again.');
      setStep('error');
    }
  };

  const handleToggleAudioPlay = () => {
    if (!recordedAudio) return;

    if (isPlayingAudio && audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      setIsPlayingAudio(false);
      return;
    }

    if (!audioPlayerRef.current) {
      const audio = new Audio(recordedAudio.url);
      audioPlayerRef.current = audio;
      audio.onended = () => setIsPlayingAudio(false);
      audio.onerror = () => setIsPlayingAudio(false);
    }

    audioPlayerRef.current
      .play()
      .then(() => setIsPlayingAudio(true))
      .catch(() => setIsPlayingAudio(false));
  };

  const handleSubmit = () => {
    const cleanText = transcript.trim();
    if (!cleanText) return;

    cleanup();
    onClose();
    onSubmitQuery(cleanText);
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(3px)',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isRecording) onClose();
      }}
    >
      <div
        style={{
          width: '90%',
          maxWidth: '520px',
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          boxShadow: '0 20px 48px rgba(0, 0, 0, 0.2)',
          border: '1px solid var(--border-strong)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--surface-warm)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent)',
              }}
            >
              <Mic size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Ask Stock AI with Voice
              </h3>
              <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', margin: 0 }}>
                Spoken Analytics & Demand Forecasting Query
              </p>
            </div>
          </div>

          {!isRecording && (
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '4px',
              }}
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div style={{ padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {step === 'record' && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                textAlign: 'center',
                gap: '16px',
                padding: '10px 0',
              }}
            >
              <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', maxWidth: '400px', lineHeight: 1.5 }}>
                Speak your question clearly. You will be able to review and edit the transcribed text before submitting.
              </p>

              {/* Big Record Button */}
              <div style={{ position: 'relative', margin: '12px 0' }}>
                <button
                  onClick={isRecording ? handleStopAndTranscribe : handleStartRecording}
                  style={{
                    width: '80px',
                    height: '80px',
                    borderRadius: '50%',
                    backgroundColor: isRecording ? '#D32F2F' : 'var(--accent)',
                    color: 'white',
                    border: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    boxShadow: isRecording
                      ? '0 0 0 10px rgba(211, 47, 47, 0.2)'
                      : '0 8px 24px rgba(0, 0, 0, 0.12)',
                    transition: 'all 0.2s ease',
                  }}
                  title={isRecording ? 'Click to Stop and Transcribe' : 'Click to Record'}
                >
                  {isRecording ? <Square size={28} /> : <Mic size={32} />}
                </button>
              </div>

              {isRecording ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#D32F2F', fontWeight: 600 }}>
                  <span
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: '#D32F2F',
                      display: 'inline-block',
                      animation: 'pulse 1s infinite alternate',
                    }}
                  />
                  <span>Recording: {formatTime(elapsed)} / 01:00</span>
                </div>
              ) : (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Click the microphone to start speaking
                </div>
              )}

              {/* Suggested Questions */}
              <div style={{ width: '100%', marginTop: '8px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Example Spoken Queries:
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', justifyContent: 'center' }}>
                  <span style={{ fontSize: '11.5px', padding: '4px 10px', backgroundColor: 'var(--surface-warm)', borderRadius: '12px', color: 'var(--text-secondary)' }}>
                    "Forecast sales for store 5 item 10 for the next 7 days"
                  </span>
                  <span style={{ fontSize: '11.5px', padding: '4px 10px', backgroundColor: 'var(--surface-warm)', borderRadius: '12px', color: 'var(--text-secondary)' }}>
                    "Show sales trend for item 15 in store 2"
                  </span>
                </div>
              </div>
            </div>
          )}

          {step === 'transcribing' && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '40px 20px',
                gap: '16px',
                textAlign: 'center',
              }}
            >
              <Loader2 size={36} color="var(--accent)" style={{ animation: 'spin 1s linear infinite' }} />
              <div>
                <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
                  Transcribing your audio...
                </h4>
                <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', margin: 0 }}>
                  Converting speech into structured text using backend AI Speech-to-Text
                </p>
              </div>
            </div>
          )}

          {step === 'review' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Review & Edit Transcribed Query:
                </span>
                <span
                  style={{
                    fontSize: '11px',
                    backgroundColor: '#E8F5E9',
                    color: '#2E7D32',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    fontWeight: 600,
                  }}
                >
                  STT: {transcribeProvider}
                </span>
              </div>

              {/* Editable Transcript Textarea */}
              <textarea
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                rows={3}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: '1px solid var(--border-strong)',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  lineHeight: 1.5,
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
                placeholder="Transcribed query..."
              />

              {/* Original Audio Preview Bar */}
              {recordedAudio && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    backgroundColor: 'var(--surface-warm)',
                    borderRadius: '10px',
                    fontSize: '12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      onClick={handleToggleAudioPlay}
                      style={{
                        width: '26px',
                        height: '26px',
                        borderRadius: '50%',
                        backgroundColor: 'var(--accent)',
                        color: 'white',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                      }}
                      title={isPlayingAudio ? 'Pause' : 'Listen to recording'}
                    >
                      {isPlayingAudio ? <Pause size={12} /> : <Play size={12} style={{ marginLeft: '1px' }} />}
                    </button>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      Original Voice Audio ({formatTime(recordedAudio.durationSeconds)})
                    </span>
                  </div>

                  <button
                    onClick={() => {
                      cleanup();
                      setStep('record');
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--accent)',
                      fontSize: '11.5px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <RotateCcw size={12} />
                    Re-record
                  </button>
                </div>
              )}

              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                * Tip: Ensure store IDs and item numbers match what you intended before submitting.
              </div>
            </div>
          )}

          {step === 'error' && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                textAlign: 'center',
                padding: '20px 10px',
                gap: '12px',
              }}
            >
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '50%',
                  backgroundColor: '#FFEBEE',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#D32F2F',
                }}
              >
                <AlertCircle size={24} />
              </div>

              <div>
                <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
                  Audio Transcription Failed
                </h4>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '360px', margin: 0 }}>
                  {errorMessage || 'Could not process audio. Please try speaking again.'}
                </p>
              </div>

              <button
                onClick={() => {
                  cleanup();
                  setStep('record');
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  marginTop: '10px',
                  padding: '8px 16px',
                  backgroundColor: 'var(--accent)',
                  color: 'white',
                  borderRadius: '18px',
                  border: 'none',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <RotateCcw size={14} />
                Try Recording Again
              </button>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        {step === 'review' && (
          <div
            style={{
              padding: '14px 20px',
              borderTop: '1px solid var(--border)',
              backgroundColor: '#FAFAFA',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '10px',
            }}
          >
            <button
              onClick={() => {
                cleanup();
                onClose();
              }}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                backgroundColor: 'white',
                color: 'var(--text-secondary)',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!transcript.trim()}
              style={{
                padding: '8px 18px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: transcript.trim() ? 'var(--accent)' : '#E0E0E0',
                color: 'white',
                fontSize: '13px',
                fontWeight: 600,
                cursor: transcript.trim() ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>Submit Query</span>
              <ArrowRight size={15} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
