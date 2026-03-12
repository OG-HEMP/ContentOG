'use client';

import { useApiData } from '@/hooks/useApiData';

export default function RunsMetricsPage() {
  const { data, loading, error } = useApiData('/runs', null, { refreshInterval: 10000 });

  return (
    <section className="panel p-4">
      <h2 className="mb-3 text-lg font-semibold">Runs & Metrics</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-300">API unavailable</p>}
      <ul className="space-y-2 text-sm">
        {(data?.runs || []).map((run) => (
          <li key={run.id} className="rounded bg-slate-800 p-2">
            Run {run.id} - {run.status || 'unknown'}
          </li>
        ))}
      </ul>
    </section>
  );
}
