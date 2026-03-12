'use client';

import { useEffect, useState } from 'react';
import { apiGet } from '@/lib/api';
import { useRun } from '@/components/RunContext';

export default function TopicPanel() {
  const { runId } = useRun();
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [strategies, setStrategies] = useState(null);

  useEffect(() => {
    function onSelect(event) {
      setSelected(event.detail);
    }

    window.addEventListener('topicSelected', onSelect);
    return () => window.removeEventListener('topicSelected', onSelect);
  }, []);

  useEffect(() => {
    if (!selected?.id) return;
    let mounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      apiGet(`/coverage?topic_id=${selected.id}`, { runId }),
      apiGet(`/strategies?topic_id=${selected.id}`, { runId })
    ])
      .then(([coverageData, strategiesData]) => {
        if (!mounted) return;
        setCoverage(coverageData);
        setStrategies(strategiesData);
      })
      .catch((err) => {
        if (mounted) setError(err);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [selected, runId]);

  return (
    <aside className="panel h-full p-4">
      <h2 className="mb-3 text-lg font-semibold">Topic Strategy Panel</h2>
      {!selected && <p className="text-sm text-slate-400">Select a topic node to view context.</p>}
      {selected && (
        <div className="space-y-3 text-sm">
          <div>
            <h3 className="font-medium">{selected.label}</h3>
            <p className="text-slate-400">Topic ID: {selected.id}</p>
          </div>
          {loading && <p>Loading...</p>}
          {error && <p className="text-red-300">API unavailable</p>}
          {coverage && (
            <div>
              <h4 className="font-medium">Coverage stats</h4>
              <pre className="mt-1 overflow-auto rounded bg-slate-800 p-2 text-xs">{JSON.stringify(coverage, null, 2)}</pre>
            </div>
          )}
          {strategies && (
            <div>
              <h4 className="font-medium">Strategy suggestions</h4>
              <pre className="mt-1 overflow-auto rounded bg-slate-800 p-2 text-xs">{JSON.stringify(strategies, null, 2)}</pre>
            </div>
          )}
          <div className="flex gap-2">
            <button className="rounded bg-indigo-600 px-3 py-1">Generate Pillar</button>
            <button className="rounded bg-slate-700 px-3 py-1">Open Coverage Matrix</button>
          </div>
        </div>
      )}
    </aside>
  );
}
