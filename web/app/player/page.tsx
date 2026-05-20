'use client';

import { useEffect, useState } from 'react';
import { fetchBotQueue, fetchBotStatus, sendBotCommand } from '@/lib/bot-api';

type Track = {
  title: string;
  artist: string;
  duration: string;
  requestedBy: string;
};

type ControlAction = 'play' | 'skip' | 'pause' | 'shuffle' | 'loop' | 'clear';

const actionLabels: Record<ControlAction, string> = {
  play: 'Putar',
  skip: 'Skip',
  pause: 'Pause',
  shuffle: 'Shuffle',
  loop: 'Loop',
  clear: 'Clear'
};

export default function PlayerPage() {
  const [search, setSearch] = useState('');
  const [queue, setQueue] = useState<Track[]>([]);
  const [status, setStatus] = useState('Siap terhubung ke API bot.');
  const [isPlaying, setIsPlaying] = useState(false);
  const [queueCount, setQueueCount] = useState(0);
  const [connectionState, setConnectionState] = useState('Menunggu...');
  const [nowPlaying, setNowPlaying] = useState<Track | null>(null);
  const [busy, setBusy] = useState(false);

  function formatDuration(length: number) {
    const mins = Math.floor(length / 1000 / 60);
    const secs = Math.floor(length / 1000) % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  async function refreshFromBackend() {
    try {
      const [botStatus, botQueue] = await Promise.all([fetchBotStatus(), fetchBotQueue()]);
      const mappedQueue: Track[] = botQueue.map((item) => ({
        title: item.title,
        artist: item.author,
        duration: formatDuration(item.length),
        requestedBy: 'API'
      }));

      setQueue(mappedQueue);
      setQueueCount(botStatus.queue_length);
      setConnectionState(botStatus.status);
      setIsPlaying(botStatus.status === 'playing');
      setNowPlaying(
        botStatus.track
          ? {
              title: botStatus.track.title,
              artist: botStatus.track.author,
              duration: formatDuration(botStatus.track.length),
              requestedBy: 'API'
            }
          : null
      );

      if (botStatus.track) {
        setStatus(`Status bot: ${botStatus.status}`);
      } else if (botStatus.status === 'idle') {
        setStatus('Bot online, tetapi belum memutar lagu.');
      } else if (botStatus.status === 'disconnected') {
        setStatus('Bot belum masuk voice channel.');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Tidak bisa terhubung ke backend.';
      setStatus(message);
      setConnectionState('offline');
      setQueue([]);
      setQueueCount(0);
      setNowPlaying(null);
      setIsPlaying(false);
    }
  }

  useEffect(() => {
    void refreshFromBackend();
    
    // Auto-refresh every 2 seconds
    const intervalId = setInterval(() => {
      void refreshFromBackend();
    }, 2000);
    
    return () => clearInterval(intervalId);
  }, []);

  async function handleAction(action: ControlAction) {
    setBusy(true);

    try {
      switch (action) {
        case 'play': {
          const query = search.trim();
          if (!query) {
            setStatus('Masukkan judul lagu atau URL dulu untuk diputar.');
            return;
          }
          const response = await sendBotCommand('play', { query });
          setStatus(response.message);
          break;
        }
        case 'skip': {
          const response = await sendBotCommand('skip');
          setStatus(response.message);
          break;
        }
        case 'pause': {
          const response = await sendBotCommand('pause');
          setStatus(response.message);
          break;
        }
        case 'shuffle': {
          const response = await sendBotCommand('shuffle');
          setStatus(response.message);
          break;
        }
        case 'loop': {
          const response = await sendBotCommand('loop');
          setStatus(response.message);
          break;
        }
        case 'clear': {
          const response = await sendBotCommand('clear');
          setStatus(response.message);
          break;
        }
      }

      await refreshFromBackend();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Aksi gagal dikirim.';
      setStatus(message);
    } finally {
      setBusy(false);
    }
  }

  const currentTrack = nowPlaying ?? queue[0];
  const queuePreview = queue.slice(0, 8);

  const stats = [
    { label: 'Antrean aktif', value: `${queueCount} lagu` },
    { label: 'Server online', value: connectionState },
    { label: 'Mode putar', value: isPlaying ? 'Playing' : 'Paused' }
  ];

  return (
    <main className="shell page-shell">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">Player</span>
          <h1>Kontrol pemutaran lagu dari web.</h1>
          <p>
            Putar lagu, skip track, shuffle antrean, ubah mode loop, dan bersihkan queue langsung
            dari panel ini.
          </p>

          <div className="search-bar">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Cari lagu atau tempel URL YouTube"
              aria-label="Cari lagu"
            />
            <button onClick={() => handleAction('play')} disabled={busy}>
              {busy ? 'Memproses...' : 'Putar'}
            </button>
          </div>

          <div className="stats-row">
            {stats.map((stat) => (
              <article key={stat.label} className="stat-card">
                <span>{stat.label}</span>
                <strong>{stat.value}</strong>
              </article>
            ))}
          </div>
        </div>

        <aside className="now-playing">
          <div className="now-playing__badge">Now Playing</div>
          <h2>{currentTrack?.title ?? 'Tidak ada lagu aktif'}</h2>
          <p>{currentTrack ? `${currentTrack.artist} • ${currentTrack.duration}` : 'Tambahkan lagu ke antrean untuk mulai memutar.'}</p>

          <div className="meter">
            <span style={{ width: isPlaying ? '68%' : '32%' }} />
          </div>

          <div className="now-playing__meta">
            <span>Status</span>
            <strong>{isPlaying ? 'Playing' : 'Paused'}</strong>
          </div>
          <div className="now-playing__meta">
            <span>Requested by</span>
            <strong>{currentTrack?.requestedBy ?? '-'}</strong>
          </div>
        </aside>
      </section>

      <section className="dashboard-grid">
        <div className="panel panel--wide">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">Quick controls</span>
              <h3>Aksi pemutaran</h3>
            </div>
          </div>

          <div className="control-grid">
            {(['skip', 'pause', 'loop', 'shuffle', 'clear'] as ControlAction[]).map((action) => (
              <button key={action} className="control-btn" onClick={() => handleAction(action)} disabled={busy}>
                {actionLabels[action]}
              </button>
            ))}
          </div>

          <div className="status-card">
            <span>System status</span>
            <strong>{status}</strong>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">Preview</span>
              <h3>Antrean singkat</h3>
            </div>
          </div>

          <div className="queue-list">
            {queuePreview.length > 0 ? (
              queuePreview.map((track, index) => (
                <article key={`${track.title}-${index}`} className="queue-item">
                  <div>
                    <strong>{track.title}</strong>
                    <p>{track.artist}</p>
                  </div>
                  <div className="queue-item__meta">
                    <span>{track.duration}</span>
                    <small>{track.requestedBy}</small>
                  </div>
                </article>
              ))
            ) : (
              <div className="empty-state">Belum ada antrean aktif.</div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}