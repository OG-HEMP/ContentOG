'use client';

import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';
import LiveProgress from '@/components/LiveProgress';

export default function DashboardPage() {
  const { runId } = useRun();
  const { data, loading, error } = useApiData('/runs', null, { 
    refreshInterval: 5000 // Poll runs to update global status
  });
  
  const runs = Array.isArray(data) ? data : data?.runs;
  const currentRun = runs?.find(r => String(r.id) === String(runId)) || runs?.[0] || {};
  const isRunning = currentRun.status === 'running';

  const cards = [
    ['Total Topics', currentRun.cluster_count || 0],
    ['Coverage Gaps', currentRun.keyword_count || 0],
    ['Pillar Opportunities', currentRun.article_count || 0],
    ['Recent Runs', runs?.length || 0]
  ];

  return (
    <section className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {loading && !data && <p>Loading...</p>}
        {error && <p className="text-red-300">API unavailable</p>}
        {cards.map(([label, value]) => (
          <article key={label} className="panel p-5">
            <p className="text-sm text-slate-400">{label}</p>
            <p className="text-3xl font-semibold">{value}</p>
          </article>
        ))}
      </div>

      {runId && isRunning && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <LiveProgress runId={runId} />
        </div>
      )}
    </section>
  );
}
