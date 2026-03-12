'use client';

import { useEffect, useState } from 'react';
import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';
import NewRunModal from '@/components/NewRunModal';

export default function Topbar() {
  const { runId, setRunId } = useRun();
  const { data, loading, error, refresh } = useApiData('/runs', null, {
    refreshInterval: 10000 // Poll runs list every 10 seconds
  });
  const [showNewRunModal, setShowNewRunModal] = useState(false);

  useEffect(() => {
    const runs = Array.isArray(data) ? data : data?.runs;
    if (!runId && runs?.length) {
      setRunId(String(runs[0].id));
    }
  }, [data, runId, setRunId]);

  const handleRunStarted = (newId) => {
    refresh();
    setRunId(newId);
  };

  return (
    <header className="panel mb-4 flex items-center justify-between p-3">
      <div>
        <h1 className="text-lg font-semibold">ContentOG Intelligence UI</h1>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowNewRunModal(true)}
          className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 active:scale-95 transition-all"
        >
          <span className="text-lg font-bold">+</span>
          New Run
        </button>

        <div className="h-6 w-px bg-slate-700" />

        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-300">Run Selector</span>
          {loading && <span className="text-xs text-slate-400">Loading...</span>}
          {error && <span className="text-xs text-red-300">API unavailable</span>}
          {(() => {
            const runs = Array.isArray(data) ? data : data?.runs;
            return runs && (
              <select
                className="rounded-md bg-slate-800 px-2 py-1 text-sm border-none focus:ring-1 focus:ring-indigo-500"
                value={runId}
                onChange={(event) => setRunId(event.target.value)}
              >
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    Run {run.id.substring(0, 8)} ({run.status})
                  </option>
                ))}
              </select>
            );
          })()}
        </div>
      </div>

      {showNewRunModal && (
        <NewRunModal
          onClose={() => setShowNewRunModal(false)}
          onRunStarted={handleRunStarted}
        />
      )}
    </header>
  );
}
