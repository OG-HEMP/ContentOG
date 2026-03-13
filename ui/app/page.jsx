'use client';

import { useEffect, useState, useMemo } from 'react';
import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';
import LiveProgress from '@/components/LiveProgress';

export default function DashboardPage() {
  const { runId } = useRun();
  const { data: runsData, loading, error } = useApiData('/runs', null, { 
    refreshInterval: 5000 
  });
  
  const { data: tasksData } = useApiData(runId ? `/runs/${runId}/tasks` : null, null, {
    refreshInterval: runId ? 3000 : null
  });

  const runs = Array.isArray(runsData) ? runsData : [];
  const selectedRun = runs.find(r => String(r.id) === String(runId)) || runs[0];
  
  const stats = useMemo(() => {
    if (!selectedRun) return {};
    const tasks = tasksData || [];
    const completed = tasks.filter(t => t.status === 'completed').length;
    const failed = tasks.filter(t => t.status === 'failed').length;
    const total = tasks.length || selectedRun.keyword_count || 0;
    
    return {
      completed,
      failed,
      total,
      progress: total > 0 ? Math.round((completed + failed) / total * 100) : 0,
      hasTopics: (selectedRun.cluster_count || 0) > 0
    };
  }, [selectedRun, tasksData]);

  const cards = [
    ['Topics Found', selectedRun?.cluster_count || 0],
    ['Keywords Analyzed', `${stats.completed || 0}/${stats.total || 0}`],
    ['Articles Scraped', selectedRun?.article_count || 0],
    ['Run Status', selectedRun?.status?.toUpperCase() || 'NONE']
  ];

  return (
    <section className="space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Discovery Control Center</h1>
          {selectedRun && (
            <p className="text-sm text-slate-400">
              Selected Run ID: <span className="text-slate-200">#{selectedRun.id.slice(0, 12)}...</span> 
              • Started {new Date(selectedRun.started_at).toLocaleString()}
            </p>
          )}
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-4">
        {loading && !runsData && <p className="col-span-full">Loading engine state...</p>}
        {error && <p className="col-span-full text-red-400 bg-red-900/20 p-3 rounded border border-red-900/50">Backend connectivity lost. Check API health.</p>}
        
        {cards.map(([label, value]) => (
          <article key={label} className="panel p-5 border-t-2 border-indigo-500/30">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</p>
            <p className="text-3xl font-semibold mt-1">{value}</p>
          </article>
        ))}
      </div>

      {selectedRun?.status === 'completed' && !stats.hasTopics && (
        <div className="bg-amber-900/20 border border-amber-900/50 p-4 rounded-lg flex items-start gap-3 text-amber-200">
          <span className="text-xl">⚠️</span>
          <div>
            <p className="font-semibold">No topic clusters discovered.</p>
            <p className="text-sm text-amber-200/70">The run completed successfully but didn't produce enough data for clustering. Try broader keywords or check crawler logs.</p>
          </div>
        </div>
      )}

      {(runId || (selectedRun && selectedRun.status === 'running')) && (
        <div className="panel p-6 border border-slate-700/50 bg-slate-900/50">
          <div className="flex justify-between items-end mb-4">
            <h3 className="text-lg font-medium">Pipeline Orchestration</h3>
            <span className="text-2xl font-mono text-indigo-400">{stats.progress}%</span>
          </div>
          <LiveProgress runId={runId || selectedRun.id} />
        </div>
      )}
    </section>
  );
}
