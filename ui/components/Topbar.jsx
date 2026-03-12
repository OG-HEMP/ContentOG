'use client';

import { useEffect } from 'react';
import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';

export default function Topbar() {
  const { runId, setRunId } = useRun();
  const { data, loading, error } = useApiData('/runs');

  useEffect(() => {
    if (!runId && data?.runs?.length) {
      setRunId(String(data.runs[0].id));
    }
  }, [data, runId, setRunId]);

  return (
    <header className="panel mb-4 flex items-center justify-between p-3">
      <div>
        <h1 className="text-lg font-semibold">ContentOG Intelligence UI</h1>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-300">Run Selector</span>
        {loading && <span className="text-xs text-slate-400">Loading...</span>}
        {error && <span className="text-xs text-red-300">API unavailable</span>}
        {data?.runs && (
          <select
            className="rounded-md bg-slate-800 px-2 py-1 text-sm"
            value={runId}
            onChange={(event) => setRunId(event.target.value)}
          >
            {data.runs.map((run) => (
              <option key={run.id} value={run.id}>
                Run {run.id}
              </option>
            ))}
          </select>
        )}
      </div>
    </header>
  );
}
