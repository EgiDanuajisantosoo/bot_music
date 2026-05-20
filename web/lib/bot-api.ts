export type BotCommand = 'play' | 'skip' | 'pause' | 'shuffle' | 'loop' | 'clear' | 'remove';

export type BotCommandResponse = {
  ok: boolean;
  message: string;
};

export const BOT_API_BASE_URL_STORAGE_KEY = 'bot-music:api-base-url';

function readStoredApiBaseUrl() {
  if (typeof window === 'undefined') {
    return null;
  }

  return window.localStorage.getItem(BOT_API_BASE_URL_STORAGE_KEY);
}

export function getBotApiBaseUrl() {
  return readStoredApiBaseUrl() ?? process.env.NEXT_PUBLIC_BOT_API_URL?.replace(/\/$/, '') ?? null;
}

export function setBotApiBaseUrlOverride(value: string) {
  if (typeof window === 'undefined') {
    return;
  }

  const trimmed = value.trim().replace(/\/$/, '');

  if (!trimmed) {
    window.localStorage.removeItem(BOT_API_BASE_URL_STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(BOT_API_BASE_URL_STORAGE_KEY, trimmed);
}

export type BotStatus = {
  status: 'disconnected' | 'idle' | 'playing' | 'paused';
  queue_length: number;
  track?: {
    title: string;
    author: string;
    uri: string;
    length: number;
    position: number;
    artwork?: string | null;
  };
};

export type BotQueueItem = {
  index: number;
  title: string;
  author: string;
  length: number;
};

export function getBotApiUrl(command: BotCommand) {
  const botApiBaseUrl = getBotApiBaseUrl();

  if (!botApiBaseUrl) {
    return null;
  }

  return `${botApiBaseUrl}/api/player/${command}`;
}

export async function removeBotQueueItem(index: number): Promise<BotCommandResponse> {
  return sendBotCommand('remove', { index });
}

export async function sendBotCommand(
  command: BotCommand,
  payload: Record<string, unknown> = {}
): Promise<BotCommandResponse> {
  const url = getBotApiUrl(command);

  if (!url) {
    const response = {
      ok: false,
      message: 'NEXT_PUBLIC_BOT_API_URL belum diatur.'
    };

    if (typeof window !== 'undefined') {
      void import('@/lib/activity-log').then(({ appendActivityLog }) => {
        appendActivityLog({
          kind: 'error',
          title: `Command ${command} gagal`,
          detail: response.message
        });
      });
    }

    return response;
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Gagal mengirim command ${command} (${response.status})`);
    }

    const data = (await response.json()) as Partial<BotCommandResponse>;
    const result = {
      ok: data.ok ?? true,
      message: data.message ?? `Command ${command} terkirim.`
    };

    if (typeof window !== 'undefined') {
      void import('@/lib/activity-log').then(({ appendActivityLog }) => {
        appendActivityLog({
          kind: 'command',
          title: `Command ${command} terkirim`,
          detail: result.message
        });
      });
    }

    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : `Gagal mengirim command ${command}`;

    if (typeof window !== 'undefined') {
      void import('@/lib/activity-log').then(({ appendActivityLog }) => {
        appendActivityLog({
          kind: 'error',
          title: `Command ${command} gagal`,
          detail: message
        });
      });
    }

    throw error;
  }
}

export async function fetchBotStatus(): Promise<BotStatus> {
  const baseUrl = getBotApiBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/player/status` : null;

  if (!url) {
    throw new Error('NEXT_PUBLIC_BOT_API_URL belum diatur.');
  }

  const response = await fetch(url, { cache: 'no-store' });

  if (!response.ok) {
    throw new Error(`Gagal mengambil status bot (${response.status})`);
  }

  return (await response.json()) as BotStatus;
}

export async function fetchBotQueue(): Promise<BotQueueItem[]> {
  const baseUrl = getBotApiBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/player/queue` : null;

  if (!url) {
    throw new Error('NEXT_PUBLIC_BOT_API_URL belum diatur.');
  }

  const response = await fetch(url, { cache: 'no-store' });

  if (!response.ok) {
    throw new Error(`Gagal mengambil antrean bot (${response.status})`);
  }

  const data = (await response.json()) as { queue: BotQueueItem[] };
  return data.queue ?? [];
}

export function getBotApiHint() {
  return getBotApiBaseUrl() ?? 'http://localhost:8080';
}