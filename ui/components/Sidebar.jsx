'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  ['Dashboard', '/'],
  ['Topic Universe', '/topic-universe'],
  ['Coverage Matrix', '/coverage-matrix'],
  ['Pillar Builder', '/pillar-builder'],
  ['Article Explorer', '/article-explorer'],
  ['Runs & Metrics', '/runs-metrics']
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="panel h-full p-3">
      <nav className="space-y-2">
        {links.map(([label, href]) => (
          <Link
            key={href}
            href={href}
            className={`block rounded px-3 py-2 text-sm ${pathname === href ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-200'}`}
          >
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
