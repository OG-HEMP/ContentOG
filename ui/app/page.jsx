'use client';

import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';

export default function DashboardPage() {
  const { runId } = useRun();
  const { data, loading, error } = useApiData('/runs', runId);
  const latest = data?.runs?.[0] || {};

  const cards = [
    ['Total Topics', latest.total_topics || 0],
    ['Coverage Gaps', latest.coverage_gaps || 0],
    ['Pillar Opportunities', latest.pillar_opportunities || 0],
    ['Recent Runs', data?.runs?.length || 0]
  ];

  return (
    <section className="grid gap-4 md:grid-cols-2">
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-300">API unavailable</p>}
      {cards.map(([label, value]) => (
        <article key={label} className="panel p-5">
          <p className="text-sm text-slate-400">{label}</p>
          <p className="text-3xl font-semibold">{value}</p>
        </article>
      ))}
    </section>
  );
}
