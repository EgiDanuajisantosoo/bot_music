export type ActivityLogEntry = {
  id: string;
  kind: 'command' | 'status' | 'error' | 'system';
  title: string;
  detail: string;
  timestamp: string;
};

const ACTIVITY_LOG_KEY = 'bot-music:activity-log';

function safeParseLog(value: string | null): ActivityLogEntry[] {
  if (!value) {
    return [];
  }

  try {
    const parsed = JSON.parse(value) as ActivityLogEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function readActivityLog(): ActivityLogEntry[] {
  if (typeof window === 'undefined') {
    return [];
  }

  return safeParseLog(window.localStorage.getItem(ACTIVITY_LOG_KEY));
}

export function writeActivityLog(entries: ActivityLogEntry[]) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(ACTIVITY_LOG_KEY, JSON.stringify(entries));
}

export function appendActivityLog(entry: Omit<ActivityLogEntry, 'id' | 'timestamp'>) {
  if (typeof window === 'undefined') {
    return;
  }

  const current = readActivityLog();
  const nextEntry: ActivityLogEntry = {
    ...entry,
    id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
    timestamp: new Date().toISOString()
  };

  writeActivityLog([nextEntry, ...current].slice(0, 100));
}

export function clearActivityLog() {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.removeItem(ACTIVITY_LOG_KEY);
}