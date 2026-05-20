'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/player', label: 'Player' },
  { href: '/queue', label: 'Queue' },
  { href: '/settings', label: 'Settings' },
  { href: '/logs', label: 'Log aktivitas' }
];

export function DashboardNav() {
  const pathname = usePathname();

  return (
    <nav className="dashboard-nav" aria-label="Dashboard navigation">
      {links.map((link) => {
        const isActive = pathname === link.href;

        return (
          <Link key={link.href} href={link.href} className={isActive ? 'nav-link active' : 'nav-link'}>
            <span>{link.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}