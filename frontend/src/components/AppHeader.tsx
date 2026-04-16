'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems: Array<{ href: string; label: string }> = [
  { href: '/', label: 'Evaluation' },
  { href: '/submit', label: 'Research' },
  { href: '/upsell', label: 'Analytics' },
];

export default function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="bg-surface-container-lowest/90 backdrop-blur-md docked full-width top-0 sticky z-50 border-b border-outline-variant/10">
      <div className="flex justify-between items-center w-full max-w-7xl mx-auto px-6 md:px-8 h-20">
        <Link
          href="/"
          className="text-2xl font-extrabold tracking-tighter text-primary-fixed font-headline"
        >
          MatDAO
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          {navItems.map((item) => {
            const active =
              pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={[
                  'transition-colors text-sm font-semibold font-body',
                  active
                    ? 'text-primary-fixed border-b-2 border-primary-fixed pb-1'
                    : 'text-on-surface-variant/50 hover:text-primary-fixed',
                ].join(' ')}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="material-symbols-outlined text-primary-fixed hover:bg-surface-container transition-all duration-300 p-2 rounded-full"
            aria-label="Account"
          >
            account_circle
          </button>
        </div>
      </div>
    </header>
  );
}

