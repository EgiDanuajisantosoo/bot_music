'use client';

import { useEffect, useState } from 'react';
import {
  BOT_API_BASE_URL_STORAGE_KEY,
  getBotApiHint,
  getBotApiBaseUrl,
  setBotApiBaseUrlOverride,
  fetchBotStatus
} from '@/lib/bot-api';
import { appendActivityLog } from '@/lib/activity-log';

export default function SettingsPage() {
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [status, setStatus] = useState('Belum diuji.');

  useEffect(() => {
    setApiBaseUrl(getBotApiBaseUrl() ?? '');
  }, []);

  function saveSettings() {
    setBotApiBaseUrlOverride(apiBaseUrl);
    appendActivityLog({
      kind: 'system',
      title: 'Settings disimpan',
      detail: apiBaseUrl.trim() || 'Menggunakan nilai default dari .env'
    });
    setStatus('Konfigurasi disimpan di browser.');
  }

  async function testConnection() {
    try {
      const botStatus = await fetchBotStatus();
      appendActivityLog({
        kind: 'status',
        title: 'Tes koneksi berhasil',
        detail: `Backend merespons dalam status ${botStatus.status}`
      });
      setStatus(`Terhubung: ${botStatus.status}`);
    } catch (error) {
      appendActivityLog({
        kind: 'error',
        title: 'Tes koneksi gagal',
        detail: error instanceof Error ? error.message : 'Gagal menguji koneksi.'
      });
      setStatus(error instanceof Error ? error.message : 'Gagal menguji koneksi.');
    }
  }

  return (
    <main className="shell page-shell">
      <section className="page-hero">
        <div>
          <span className="eyebrow">Settings</span>
          <h1>Pengaturan dashboard</h1>
          <p>Atur alamat backend, cek koneksi, dan lihat parameter yang dipakai panel web.</p>
        </div>
      </section>

      <section className="page-grid">
        <article className="panel panel--wide">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">Connection</span>
              <h3>API base URL</h3>
            </div>
          </div>

          <div className="settings-form">
            <label>
              <span>Backend URL</span>
              <input
                value={apiBaseUrl}
                onChange={(event) => setApiBaseUrl(event.target.value)}
                placeholder={getBotApiHint()}
              />
            </label>

            <div className="control-row">
              <button className="control-btn" onClick={saveSettings}>
                Simpan
              </button>
              <button className="ghost" onClick={testConnection}>
                Test koneksi
              </button>
            </div>
          </div>
        </article>

        <aside className="panel">
          <div className="panel-header">
            <div>
              <span className="panel-kicker">Storage</span>
              <h3>Local override</h3>
            </div>
          </div>

          <div className="status-card">
            <span>Key browser</span>
            <strong>{BOT_API_BASE_URL_STORAGE_KEY}</strong>
          </div>

          <div className="status-card">
            <span>Status</span>
            <strong>{status}</strong>
          </div>
        </aside>
      </section>
    </main>
  );
}