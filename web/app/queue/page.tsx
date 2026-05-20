'use client';

import { useEffect, useState } from 'react';
import { fetchBotQueue, fetchBotStatus, sendBotCommand, removeBotQueueItem } from '@/lib/bot-api';

type QueueItem = {
  title: string;
  artist: string;
  duration: string;
  requestedBy: string;
};

export default function QueuePage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [status, setStatus] = useState('Memuat antrean...');
  const [count, setCount] = useState(0);
  const [removingIndex, setRemovingIndex] = useState<number | null>(null);

  function formatDuration(length: number) {
    const mins = Math.floor(length / 1000 / 60);
    const secs = Math.floor(length / 1000) % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  async function refreshQueue() {
    try {
      const [botStatus, botQueue] = await Promise.all([fetchBotStatus(), fetchBotQueue()]);

      setQueue(
        botQueue.map((item) => ({
          title: item.title,
          artist: item.author,
          duration: formatDuration(item.length),
          requestedBy: 'API'
        }))
      );
      setCount(botStatus.queue_length);
      setStatus(`Queue terbaca: ${botStatus.status}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Gagal memuat antrean.';
      setStatus(message);
      setQueue([]);
      setCount(0);
    }
  }

  async function handleRemoveItem(index: number) {
    setRemovingIndex(index);
    try {
      const response = await removeBotQueueItem(index);
      setStatus(response.message);
      await refreshQueue();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Gagal menghapus lagu.';
      setStatus(message);
    } finally {
      setRemovingIndex(null);
    }
  }

  useEffect(() => {
    void refreshQueue();
    
    // Auto-refresh queue every 2 seconds
    const intervalId = setInterval(() => {
      void refreshQueue();
    }, 2000);
    
    return () => clearInterval(intervalId);
  }, []);

  return (
    <main className="shell page-shell">
      <section className="page-hero">
        <div>
          <span className="eyebrow">Queue</span>
          <h1>Antrean lagu</h1>
          <p>Semua track yang sedang menunggu diputar ditampilkan di halaman ini.</p>
        </div>

        <div className="page-actions">
          <button className="ghost" onClick={() => refreshQueue()}>
            Refresh
          </button>
          <button className="control-btn" onClick={() => sendBotCommand('clear').then(refreshQueue)}>
            Clear queue
          </button>
        </div>
      </section>

      <section className="page-grid">
        <article className="panel panel--wide">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">Total</span>
              <h3>{count} lagu</h3>
            </div>
          </div>

          <div className="queue-list">
            {queue.length > 0 ? (
              queue.map((track, index) => (
                <article key={`${track.title}-${index}`} className="queue-item">
                  <div>
                    <strong>{index + 1}. {track.title}</strong>
                    <p>{track.artist}</p>
                  </div>
                  <div className="queue-item__meta">
                    <span>{track.duration}</span>
                    <small>{track.requestedBy}</small>
                  </div>
                  <button
                    className="queue-item__remove"
                    onClick={() => handleRemoveItem(index)}
                    disabled={removingIndex === index}
                    title="Hapus lagu dari antrean"
                    aria-label={`Hapus ${track.title}`}
                  >
                    {removingIndex === index ? '...' : '✕'}
                  </button>
                </article>
              ))
            ) : (
              <div className="empty-state">Antrean kosong.</div>
            )}
          </div>
        </article>

        <aside className="panel">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">Status</span>
              <h3>Sinkronisasi</h3>
            </div>
          </div>

          <div className="status-card">
            <span>Backend</span>
            <strong>{status}</strong>
          </div>
        </aside>
      </section>
    </main>
  );
}