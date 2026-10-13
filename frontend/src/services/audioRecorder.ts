/**
 * Browser MediaRecorder service for capturing voice messages with configurable limits.
 */

export interface RecordedAudio {
  blob: Blob;
  file: File;
  url: string;
  durationSeconds: number;
  mimeType: string;
}

export type RecorderState = 'idle' | 'recording' | 'stopped' | 'denied' | 'unsupported';

export interface RecorderOptions {
  maxDurationSeconds?: number;
  maxSizeBytes?: number;
  onTick?: (elapsedSeconds: number) => void;
  onMaxDurationReached?: () => void;
}

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private mediaStream: MediaStream | null = null;
  private recordedChunks: Blob[] = [];
  private startTime: number = 0;
  private timerInterval: any = null;
  private currentElapsed: number = 0;

  public state: RecorderState = 'idle';
  public maxDurationSeconds: number = 60; // 60s default limit
  public maxSizeBytes: number = 10 * 1024 * 1024; // 10MB limit

  constructor(options?: RecorderOptions) {
    if (options?.maxDurationSeconds) {
      this.maxDurationSeconds = options.maxDurationSeconds;
    }
    if (options?.maxSizeBytes) {
      this.maxSizeBytes = options.maxSizeBytes;
    }
  }

  /**
   * Check if the browser supports audio media recording.
   */
  public static isSupported(): boolean {
    return Boolean(
      typeof window !== 'undefined' &&
        typeof navigator?.mediaDevices?.getUserMedia === 'function' &&
        window.MediaRecorder
    );
  }

  /**
   * Determine preferred audio MIME type supported by browser.
   */
  private static getSupportedMimeType(): string {
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
      'audio/aac',
    ];

    for (const candidate of candidates) {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(candidate)) {
        return candidate;
      }
    }
    return '';
  }

  /**
   * Start recording audio from the microphone.
   */
  public async startRecording(options?: RecorderOptions): Promise<void> {
    if (!AudioRecorder.isSupported()) {
      this.state = 'unsupported';
      throw new Error('Audio recording is not supported in this browser.');
    }

    if (this.state === 'recording') {
      return;
    }

    if (options?.maxDurationSeconds) {
      this.maxDurationSeconds = options.maxDurationSeconds;
    }

    this.recordedChunks = [];
    this.currentElapsed = 0;

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch (err: any) {
      this.state = 'denied';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        throw new Error('Microphone permission was denied. Please allow microphone access in browser settings.');
      }
      throw new Error(`Could not access microphone: ${err.message || err}`);
    }

    const mimeType = AudioRecorder.getSupportedMimeType();
    const recorderOptions = mimeType ? { mimeType } : undefined;

    try {
      this.mediaRecorder = new MediaRecorder(this.mediaStream, recorderOptions);
    } catch (err: any) {
      this.cleanupStream();
      throw new Error(`MediaRecorder initialization failed: ${err.message || err}`);
    }

    this.mediaRecorder.ondataavailable = (event: BlobEvent) => {
      if (event.data && event.data.size > 0) {
        this.recordedChunks.push(event.data);
      }
    };

    this.mediaRecorder.start(200); // 200ms slice chunks
    this.state = 'recording';
    this.startTime = Date.now();

    // Timer tracking elapsed time and max duration limit
    this.timerInterval = setInterval(() => {
      this.currentElapsed = Math.floor((Date.now() - this.startTime) / 1000);

      if (options?.onTick) {
        options.onTick(this.currentElapsed);
      }

      if (this.currentElapsed >= this.maxDurationSeconds) {
        if (options?.onMaxDurationReached) {
          options.onMaxDurationReached();
        }
        this.stopRecording().catch((e) => console.warn('Auto-stop error:', e));
      }
    }, 250);
  }

  /**
   * Stop recording and return the recorded audio payload.
   */
  public stopRecording(): Promise<RecordedAudio> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || this.state !== 'recording') {
        reject(new Error('Recorder is not actively recording.'));
        return;
      }

      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }

      const finalElapsed = Math.max(1, Math.round((Date.now() - this.startTime) / 1000));

      this.mediaRecorder.onstop = () => {
        const mimeType = this.mediaRecorder?.mimeType || 'audio/webm';
        const audioBlob = new Blob(this.recordedChunks, { type: mimeType });

        if (audioBlob.size === 0) {
          this.cleanupStream();
          this.state = 'idle';
          reject(new Error('Recorded audio file is empty.'));
          return;
        }

        if (audioBlob.size > this.maxSizeBytes) {
          this.cleanupStream();
          this.state = 'idle';
          reject(
            new Error(
              `Audio file size (${(audioBlob.size / 1024 / 1024).toFixed(1)}MB) exceeds limit of ${(
                this.maxSizeBytes /
                1024 /
                1024
              ).toFixed(0)}MB.`
            )
          );
          return;
        }

        // Determine extension based on mime type
        const ext = mimeType.includes('mp4') ? 'mp4' : mimeType.includes('ogg') ? 'ogg' : 'webm';
        const fileName = `voice_message_${Date.now()}.${ext}`;
        const audioFile = new File([audioBlob], fileName, { type: mimeType });
        const audioUrl = URL.createObjectURL(audioBlob);

        this.cleanupStream();
        this.state = 'stopped';

        resolve({
          blob: audioBlob,
          file: audioFile,
          url: audioUrl,
          durationSeconds: finalElapsed,
          mimeType,
        });
      };

      try {
        this.mediaRecorder.stop();
      } catch (err) {
        this.cleanupStream();
        this.state = 'idle';
        reject(err);
      }
    });
  }

  /**
   * Discard any current recording and release the microphone hardware immediately.
   */
  public discardRecording(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try {
        this.mediaRecorder.stop();
      } catch {
        // ignore
      }
    }

    this.cleanupStream();
    this.recordedChunks = [];
    this.state = 'idle';
    this.currentElapsed = 0;
  }

  /**
   * Release media tracks to ensure the browser recording indicator turns off.
   */
  private cleanupStream(): void {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // ignore
        }
      });
      this.mediaStream = null;
    }
    this.mediaRecorder = null;
  }
}
