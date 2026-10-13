import { CometChat } from '@cometchat/chat-sdk-javascript';
import { CometChatMessage, CometChatPublicConfig, CometChatUser } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export interface InitResult {
  initialized: boolean;
  isConfigured: boolean;
  appId?: string;
  region?: string;
  error?: string;
}

export interface UserSessionState {
  isLoggedIn: boolean;
  user: CometChatUser | null;
  isMock: boolean;
}

let isInitialized = false;
let currentConfig: CometChatPublicConfig | null = null;
let currentSession: UserSessionState = {
  isLoggedIn: false,
  user: null,
  isMock: false,
};

// In-memory mock store for test-mode bidirectional messaging
const mockMessageStore: CometChatMessage[] = [];
const mockListeners: Map<string, (msg: CometChatMessage) => void> = new Map();

const FALLBACK_DEFAULT_USERS: CometChatUser[] = [
  { uid: 'analyst_1', name: 'Senior Demand Analyst', role: 'Analyst' },
  { uid: 'analyst_2', name: 'Inventory Operations Lead', role: 'Operations' },
];

/**
 * Fetch public CometChat config from the backend without exposing any secret keys.
 */
export async function getCometChatConfig(): Promise<CometChatPublicConfig> {
  const fallbackConfig: CometChatPublicConfig = {
    app_id: import.meta.env.VITE_COMETCHAT_APP_ID || '',
    region: import.meta.env.VITE_COMETCHAT_REGION || 'us',
    is_configured: Boolean(import.meta.env.VITE_COMETCHAT_APP_ID),
    default_users: FALLBACK_DEFAULT_USERS,
  };

  if (currentConfig && Array.isArray(currentConfig.default_users) && currentConfig.default_users.length > 0) {
    return currentConfig;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/cometchat/config`);
    if (res.ok) {
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = await res.json();
        if (data && Array.isArray(data.default_users) && data.default_users.length > 0) {
          currentConfig = {
            app_id: data.app_id || fallbackConfig.app_id,
            region: data.region || fallbackConfig.region,
            is_configured: Boolean(data.is_configured),
            default_users: data.default_users,
          };
          return currentConfig;
        }
      }
    }
  } catch (err) {
    console.warn('Failed to load CometChat config from server, using fallback:', err);
  }

  currentConfig = fallbackConfig;
  return currentConfig;
}

/**
 * Initializes CometChat SDK with regional AppSettings.
 */
export async function initCometChat(): Promise<InitResult> {
  if (isInitialized) {
    return {
      initialized: true,
      isConfigured: Boolean(currentConfig?.is_configured),
      appId: currentConfig?.app_id,
      region: currentConfig?.region,
    };
  }

  const config = await getCometChatConfig();

  if (!config.app_id || !config.is_configured) {
    return {
      initialized: false,
      isConfigured: false,
      message: 'CometChat credentials (APP_ID / REST_API_KEY) are not configured. Running in demo mode.',
    } as any;
  }

  try {
    const appSettings = new CometChat.AppSettingsBuilder()
      .subscribePresenceForAllUsers()
      .setRegion(config.region)
      .autoEstablishSocketConnection(true)
      .build();

    await CometChat.init(config.app_id, appSettings);
    isInitialized = true;
    return {
      initialized: true,
      isConfigured: true,
      appId: config.app_id,
      region: config.region,
    };
  } catch (err: any) {
    console.error('CometChat.init failed:', err);
    return {
      initialized: false,
      isConfigured: true,
      error: err?.message || String(err),
    };
  }
}

/**
 * Securely logs in user via server-issued auth token.
 */
export async function loginCometChatUser(uid: string, name?: string): Promise<UserSessionState> {
  const config = await getCometChatConfig();
  const defaultUsers = config?.default_users?.length ? config.default_users : FALLBACK_DEFAULT_USERS;
  const displayName = name || defaultUsers.find((u) => u.uid === uid)?.name || uid;

  try {
    // Request auth token from backend
    const tokenRes = await fetch(`${API_BASE_URL}/api/cometchat/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid, name: displayName }),
    });

    if (!tokenRes.ok) {
      const errText = await tokenRes.text();
      console.warn(`Server auth token retrieval returned ${tokenRes.status}: ${errText}. Activating demo mode.`);
      currentSession = {
        isLoggedIn: true,
        user: { uid, name: displayName },
        isMock: true,
      };
      return currentSession;
    }

    const tokenData = await tokenRes.json();

    // If running in mock/demo mode because server keys are absent
    if (tokenData.status === 'mock_mode' || !isInitialized) {
      currentSession = {
        isLoggedIn: true,
        user: { uid, name: displayName },
        isMock: true,
      };
      return currentSession;
    }

    // Real CometChat SDK login using server-generated auth token
    const loggedIn = await CometChat.login(tokenData.auth_token);
    currentSession = {
      isLoggedIn: true,
      user: {
        uid: loggedIn.getUid ? loggedIn.getUid() : uid,
        name: loggedIn.getName ? loggedIn.getName() : displayName,
        avatar: loggedIn.getAvatar ? loggedIn.getAvatar() : undefined,
      },
      isMock: false,
    };
    return currentSession;
  } catch (err: any) {
    console.warn('CometChat login/token error, falling back to demo session:', err);
    currentSession = {
      isLoggedIn: true,
      user: { uid, name: displayName },
      isMock: true,
    };
    return currentSession;
  }
}

/**
 * Log out current CometChat user.
 */
export async function logoutCometChatUser(): Promise<void> {
  if (isInitialized && !currentSession.isMock) {
    try {
      await CometChat.logout();
    } catch (err) {
      console.warn('CometChat logout warning:', err);
    }
  }
  currentSession = {
    isLoggedIn: false,
    user: null,
    isMock: false,
  };
}

/**
 * Get current session info.
 */
export function getCurrentCometChatSession(): UserSessionState {
  return currentSession;
}

/**
 * Send an ordinary text message to a recipient user.
 */
export async function sendCometChatTextMessage(
  receiverUID: string,
  text: string
): Promise<CometChatMessage> {
  const cleanText = text.trim();
  if (!cleanText) {
    throw new Error('Message text cannot be empty.');
  }

  if (!currentSession.isLoggedIn || !currentSession.user) {
    throw new Error('Must be logged in to CometChat to send messages.');
  }

  const currentUID = currentSession.user.uid;

  // Real CometChat SDK flow
  if (isInitialized && !currentSession.isMock) {
    const textMessage = new CometChat.TextMessage(
      receiverUID,
      cleanText,
      CometChat.RECEIVER_TYPE.USER
    );

    const sentMessage = await CometChat.sendMessage(textMessage);
    const resultMsg: CometChatMessage = {
      id: String(sentMessage.getId ? sentMessage.getId() : Date.now()),
      senderUid: currentUID,
      senderName: currentSession.user.name,
      receiverUid: receiverUID,
      text: cleanText,
      type: 'text',
      timestamp: sentMessage.getSentAt ? sentMessage.getSentAt() * 1000 : Date.now(),
    };
    return resultMsg;
  }

  // Simulated mock flow
  const mockMsg: CometChatMessage = {
    id: 'mock-msg-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
    senderUid: currentUID,
    senderName: currentSession.user.name,
    receiverUid: receiverUID,
    text: cleanText,
    type: 'text',
    timestamp: Date.now(),
  };

  mockMessageStore.push(mockMsg);

  // Notify registered mock listeners
  mockListeners.forEach((callback) => {
    try {
      callback(mockMsg);
    } catch (err) {
      console.error('Error invoking mock listener:', err);
    }
  });

  return mockMsg;
}

/**
 * Send an audio voice message to a specific user.
 */
export async function sendCometChatAudioMessage(
  receiverUID: string,
  audioFile: File,
  durationSeconds?: number
): Promise<CometChatMessage> {
  if (!receiverUID) {
    throw new Error('Receiver UID is required.');
  }
  if (!audioFile) {
    throw new Error('Audio file is required.');
  }

  if (!currentSession.isLoggedIn || !currentSession.user) {
    throw new Error('Must be logged in to CometChat to send audio messages.');
  }

  const currentUID = currentSession.user.uid;

  // Real CometChat SDK flow
  if (isInitialized && !currentSession.isMock) {
    const mediaMessage = new CometChat.MediaMessage(
      receiverUID,
      audioFile,
      CometChat.MESSAGE_TYPE.AUDIO,
      CometChat.RECEIVER_TYPE.USER
    );

    if (durationSeconds) {
      mediaMessage.setMetadata({ duration: durationSeconds });
    }

    const sentMessage: any = await CometChat.sendMediaMessage(mediaMessage);
    const metadata = sentMessage.getMetadata ? sentMessage.getMetadata() : {};
    const audioUrl =
      sentMessage.getFile?.()?.getUrl?.() ||
      sentMessage.getData?.()?.url ||
      URL.createObjectURL(audioFile);

    const resultMsg: CometChatMessage = {
      id: String(sentMessage.getId ? sentMessage.getId() : Date.now()),
      senderUid: currentUID,
      senderName: currentSession.user.name,
      receiverUid: receiverUID,
      type: 'audio',
      audioUrl: audioUrl,
      durationSeconds: metadata?.duration || durationSeconds,
      timestamp: sentMessage.getSentAt ? sentMessage.getSentAt() * 1000 : Date.now(),
      status: 'sent',
      audioFile: audioFile,
    };
    return resultMsg;
  }

  // Simulated mock flow
  const mockAudioUrl = URL.createObjectURL(audioFile);
  const mockMsg: CometChatMessage = {
    id: 'mock-audio-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
    senderUid: currentUID,
    senderName: currentSession.user.name,
    receiverUid: receiverUID,
    type: 'audio',
    audioUrl: mockAudioUrl,
    durationSeconds: durationSeconds || 5,
    timestamp: Date.now(),
    status: 'sent',
    audioFile: audioFile,
  };

  mockMessageStore.push(mockMsg);

  // Notify registered mock listeners
  mockListeners.forEach((callback) => {
    try {
      callback(mockMsg);
    } catch (err) {
      console.error('Error invoking mock listener for audio:', err);
    }
  });

  return mockMsg;
}

/**
 * Fetch previous message history between current user and target user.
 */
export async function fetchCometChatMessageHistory(
  targetUID: string,
  limit = 30
): Promise<CometChatMessage[]> {
  if (!currentSession.isLoggedIn || !currentSession.user) return [];

  const currentUID = currentSession.user.uid;

  if (isInitialized && !currentSession.isMock) {
    try {
      const messagesRequest = new CometChat.MessagesRequestBuilder()
        .setUID(targetUID)
        .setLimit(limit)
        .build();

      const messages = await messagesRequest.fetchPrevious();
      return messages.map((m: any) => {
        const isAudio =
          (m.getType ? m.getType() : m.type) === CometChat.MESSAGE_TYPE?.AUDIO ||
          m.type === 'audio';
        const metadata = m.getMetadata ? m.getMetadata() : m.data?.metadata || {};
        const audioUrl =
          m.getFile?.()?.getUrl?.() ||
          m.getData?.()?.url ||
          m.data?.url ||
          m.data?.file ||
          m.audioUrl;

        return {
          id: String(m.getId ? m.getId() : m.id),
          senderUid: m.getSender ? m.getSender().getUid() : m.sender?.uid,
          senderName: m.getSender ? m.getSender().getName() : m.sender?.name,
          receiverUid: m.getReceiverId ? m.getReceiverId() : targetUID,
          text: m.getText ? m.getText() : m.data?.text || '',
          type: isAudio ? 'audio' : (m.getType ? (m.getType() as any) : 'text'),
          timestamp: m.getSentAt ? m.getSentAt() * 1000 : m.timestamp || Date.now(),
          data: m.getData ? m.getData() : m.data,
          audioUrl: isAudio ? audioUrl : undefined,
          durationSeconds: metadata?.duration || m.durationSeconds,
          status: 'sent',
        };
      });
    } catch (err) {
      console.warn('Failed to fetch CometChat message history:', err);
      return [];
    }
  }

  // Filter in-memory mock messages for this pair
  return mockMessageStore.filter(
    (m) =>
      (m.senderUid === currentUID && m.receiverUid === targetUID) ||
      (m.senderUid === targetUID && m.receiverUid === currentUID)
  );
}

/**
 * Register real-time message listener.
 */
export function addCometChatMessageListener(
  listenerId: string,
  onMessageReceived: (message: CometChatMessage) => void
): void {
  if (isInitialized && !currentSession.isMock) {
    CometChat.addMessageListener(
      listenerId,
      new CometChat.MessageListener({
        onTextMessageReceived: (textMessage: any) => {
          const formatted: CometChatMessage = {
            id: String(textMessage.getId ? textMessage.getId() : Date.now()),
            senderUid: textMessage.getSender ? textMessage.getSender().getUid() : '',
            senderName: textMessage.getSender ? textMessage.getSender().getName() : '',
            receiverUid: textMessage.getReceiverId ? textMessage.getReceiverId() : '',
            text: textMessage.getText ? textMessage.getText() : '',
            type: 'text',
            timestamp: textMessage.getSentAt ? textMessage.getSentAt() * 1000 : Date.now(),
            status: 'sent',
          };
          onMessageReceived(formatted);
        },
        onMediaMessageReceived: (mediaMessage: any) => {
          const isAudio =
            (mediaMessage.getType ? mediaMessage.getType() : mediaMessage.type) ===
              CometChat.MESSAGE_TYPE?.AUDIO || mediaMessage.type === 'audio';
          const metadata = mediaMessage.getMetadata
            ? mediaMessage.getMetadata()
            : mediaMessage.data?.metadata || {};
          const audioUrl =
            mediaMessage.getFile?.()?.getUrl?.() ||
            mediaMessage.getData?.()?.url ||
            mediaMessage.data?.url ||
            mediaMessage.data?.file;

          const formatted: CometChatMessage = {
            id: String(mediaMessage.getId ? mediaMessage.getId() : Date.now()),
            senderUid: mediaMessage.getSender ? mediaMessage.getSender().getUid() : '',
            senderName: mediaMessage.getSender ? mediaMessage.getSender().getName() : '',
            receiverUid: mediaMessage.getReceiverId ? mediaMessage.getReceiverId() : '',
            text: mediaMessage.getText ? mediaMessage.getText() : '',
            type: isAudio ? 'audio' : 'media',
            timestamp: mediaMessage.getSentAt ? mediaMessage.getSentAt() * 1000 : Date.now(),
            audioUrl: isAudio ? audioUrl : undefined,
            durationSeconds: metadata?.duration,
            status: 'sent',
          };
          onMessageReceived(formatted);
        },
      })
    );
    return;
  }

  // Register in mock listeners map
  mockListeners.set(listenerId, onMessageReceived);
}

/**
 * Remove registered real-time message listener.
 */
export function removeCometChatMessageListener(listenerId: string): void {
  if (isInitialized && !currentSession.isMock) {
    CometChat.removeMessageListener(listenerId);
    return;
  }
  mockListeners.delete(listenerId);
}
