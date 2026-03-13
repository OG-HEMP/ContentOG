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
        {Array.isArray(data) && data.length > 0 ? (
          data.map((run) => (
            <li key={run.id} className="rounded bg-slate-800 p-2 border border-slate-700">
              <div className="flex justify-between">
                <span className="font-medium text-slate-200">Run #{run.id.slice(0, 8)}</span>
                <span className={`px-2 rounded-full text-xs py-0.5 ${
                  run.status === 'completed' ? 'bg-green-900 text-green-200' : 
                  run.status === 'failed' ? 'bg-red-900 text-red-200' : 'bg-blue-900 text-blue-200'
                }`}>
                  {run.status || 'unknown'}
                </span>
              </div>
              <div className="mt-1 text-xs text-slate-400">
                Started: {new Date(run.started_at).toLocaleString()}
              </div>
            </li>
          ))
        ) : (
          <p className="text-slate-400 italic">No runs recorded yet. Start a new discovery run from the dashboard.</p>
        )}
      </ul>
    </section>
  );
}
