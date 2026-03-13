'use client';

import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';

export default function RunHistory() {
  const { setRunId, runId } = useRun();
  const { data: runs, loading, error } = useApiData('/runs', null, { refreshInterval: 10000 });

  const formatStatus = (status) => {
    switch (status) {
      case 'completed': return <span className="text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded text-[10px] font-bold uppercase">Completed</span>;
      case 'failed': return <span className="text-red-400 bg-red-400/10 px-2 py-0.5 rounded text-[10px] font-bold uppercase">Failed</span>;
      case 'running': return <span className="text-indigo-400 bg-indigo-400/10 px-2 py-0.5 rounded text-[10px] font-bold uppercase animate-pulse">Running</span>;
      default: return <span className="text-slate-500 bg-slate-500/10 px-2 py-0.5 rounded text-[10px] font-bold uppercase">{status}</span>;
    }
  };

  if (loading && !runs) return <p className="text-sm text-slate-500 italic">Loading run history...</p>;
  if (error) return <p className="text-sm text-red-400">Failed to load history</p>;

  return (
    <div className="panel p-0 overflow-hidden">
      <div className="bg-slate-900/50 p-4 border-b border-slate-800">
        <h3 className="text-sm font-semibold text-white">Execution History</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider font-bold">
              <th className="px-4 py-3">Run ID</th>
              <th className="px-4 py-3">Started</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-center">Keywords</th>
              <th className="px-4 py-3 text-center">Articles</th>
              <th className="px-4 py-3 text-center">Topics</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {runs?.map((run) => (
              <tr 
                key={run.id} 
                className={`group cursor-pointer hover:bg-slate-800/30 transition-colors ${runId === run.id ? 'bg-indigo-500/5 border-l-2 border-l-indigo-500' : ''}`}
                onClick={() => setRunId(run.id)}
              >
                <td className="px-4 py-3 font-mono text-slate-300">
                  {run.id.slice(0, 8)}...
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {new Date(run.started_at).toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  {formatStatus(run.status)}
                </td>
                <td className="px-4 py-3 text-center font-semibold">{run.keyword_count || 0}</td>
                <td className="px-4 py-3 text-center text-slate-300">{run.article_count || 0}</td>
                <td className="px-4 py-3 text-center text-slate-300">{run.cluster_count || 0}</td>
                <td className="px-4 py-3 text-right">
                  <button 
                    className={`text-[10px] px-2 py-1 rounded border transition-all ${
                      runId === run.id ? 'bg-indigo-500 text-white border-indigo-500' : 'text-slate-400 border-slate-700 group-hover:border-slate-500'
                    }`}
                  >
                    {runId === run.id ? 'Active' : 'View Details'}
                  </button>
                </td>
              </tr>
            ))}
            {runs?.length === 0 && (
                <tr>
                    <td colSpan="7" className="px-4 py-8 text-center text-slate-500 italic">
                        No historical runs found. Start a new discovery to begin.
                    </td>
                </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
