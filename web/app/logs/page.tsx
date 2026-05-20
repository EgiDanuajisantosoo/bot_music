'use client';

import { useEffect, useState } from 'react';
import { clearActivityLog, readActivityLog } from '@/lib/activity-log';
import type { ActivityLogEntry } from '@/lib/activity-log';

export default function LogsPage() {
  const [logs, setLogs] = useState<ActivityLogEntry[]>([]);

  function refreshLogs() {
    setLogs(readActivityLog());
  }

  useEffect(() => {
    refreshLogs();
  }, []);

  return (
    <main className="shell page-shell">
      <section className="page-hero">
        <div>
          <span className="eyebrow">Log aktivitas</span>
          <h1>Riwayat aksi dashboard</h1>
          <p>Halaman ini menampilkan log aktivitas lokal dari interaksi dashboard.</p>
        </div>

        <div className="page-actions">
          <button className="ghost" onClick={refreshLogs}>
            Refresh
          </button>
          <button
            className="control-btn"
            onClick={() => {
              clearActivityLog();
              refreshLogs();
            }}
          >
            Hapus log
          </button>
        </div>
      </section>

      <section className="page-grid">
        <article className="panel panel--wide">
          <div className="queue-list">
            {logs.length > 0 ? (
              logs.map((entry) => (
                <article key={entry.id} className={`log-item log-item--${entry.kind}`}>
                  <div>
                    <strong>{entry.title}</strong>
                    <p>{entry.detail}</p>
                  </div>
                  <time>{new Date(entry.timestamp).toLocaleString('id-ID')}</time>
                </article>
              ))
            ) : (
              <div className="empty-state">Belum ada log aktivitas.</div>
            )}
          </div>
        </article>

        <aside className="panel">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">Note</span>
              <h3>Scope log</h3>
            </div>
          </div>

          <div className="status-card">
            <span>Jenis log</span>
            <strong>command, status, error, system</strong>
          </div>
        </aside>
      </section>
    </main>
  );
}