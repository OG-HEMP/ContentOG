'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { label: 'Dashboard', href: '/', icon: '📊' },
  { label: 'Topic Universe', href: '/topic-universe', icon: '🌐' },
  { label: 'Coverage Matrix', href: '/coverage-matrix', icon: '🗺️' },
  { label: 'Pillar Builder', href: '/pillar-builder', icon: '🧱' },
  { label: 'Article Explorer', href: '/article-explorer', icon: '🔍' },
  { label: 'Runs & Metrics', href: '/runs-metrics', icon: '📈' }
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="panel h-full p-4 bg-slate-900/40 border-r border-slate-800">
      <div className="mb-6 px-2">
        <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Navigation</h2>
      </div>
      <nav className="space-y-1">
        {links.map(({ label, href, icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
              pathname === href 
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30' 
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent'
            }`}
          >
            <span className="text-lg grayscale-0">{icon}</span>
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
