import type { Metadata } from 'next';
import { Plus_Jakarta_Sans, Space_Grotesk } from 'next/font/google';
import Link from 'next/link';
import { DashboardNav } from '@/components/dashboard-nav';
import './globals.css';

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-display'
});

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-body'
});

export const metadata: Metadata = {
  title: 'Bot Music Control',
  description: 'Dashboard Next.js untuk mengatur lagu, antrean, dan status bot musik.'
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className={`${spaceGrotesk.variable} ${plusJakarta.variable}`}>
        <div className="app-shell">
          <aside className="sidebar">
            <div className="brand-block">
              <span className="brand-mark">BM</span>
              <div>
                <strong>Bot Music</strong>
                <p>Next.js control center</p>
              </div>
            </div>

            <DashboardNav />

            <div className="sidebar-card">
              <span className="panel-kicker">Backend</span>
              <p>Hubungkan ke [main.py](c:/laragon-6.0.0/www/bot/bot_music/main.py) via endpoint `/api/player/*`.</p>
            </div>
          </aside>

          <main className="content-shell">
            <header className="topbar">
              <div>
                <span className="panel-kicker">Dashboard</span>
                <h1>Bot control panel</h1>
              </div>
              <Link href="/player" className="topbar-link">Open player</Link>
            </header>

            <div className="content-stage">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}