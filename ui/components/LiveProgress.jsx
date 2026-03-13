'use client';

import { useState, useEffect } from 'react';
import { useApiData } from '@/hooks/useApiData';
import { apiPost } from '@/lib/api';

export default function LiveProgress({ runId }) {
  const { data: tasks, loading, error } = useApiData(`/runs/${runId}/tasks`, null, {
    refreshInterval: 3000 // Poll every 3 seconds
  });

  const [retryStates, setRetryStates] = useState({});

  // Cleanup completed retries or simulate progress
  useEffect(() => {
    if (!tasks) return;

    const interval = setInterval(() => {
      setRetryStates(prev => {
        const next = { ...prev };
        let changed = false;

        Object.keys(next).forEach(taskId => {
          const task = tasks.find(t => t.id === taskId);
          
          // If task moved out of 'failed' or 'pending' to 'running'/'completed', 
          // we can keep simulating or let the real status take over.
          // For now, if it's completed, we clear the retry state.
          if (task?.status === 'completed') {
            delete next[taskId];
            changed = true;
          } else if (next[taskId].progress < 95) {
            // Simulate progress up to 95%
            next[taskId].progress += Math.random() * 5;
            if (next[taskId].progress > 95) next[taskId].progress = 95;
            changed = true;
          }
        });

        return changed ? next : prev;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [tasks]);

  if (loading && !tasks) return <div className="animate-pulse py-4 text-sm text-slate-400">Loading progress...</div>;
  if (error) return null;

  const total = tasks?.length || 0;
  const completed = tasks?.filter(t => t.status === 'completed').length || 0;
  const failed = tasks?.filter(t => t.status === 'failed').length || 0;
  const progress = total > 0 ? ((completed + failed) / total) * 100 : 0;

  const handleRetry = async (taskId) => {
    // Immediate visual feedback
    setRetryStates(prev => ({
      ...prev,
      [taskId]: { progress: 0, error: null, attempts: (prev[taskId]?.attempts || 0) + 1 }
    }));

    try {
      await apiPost(`/tasks/${taskId}/retry`);
    } catch (err) {
      console.error('Failed to retry task:', err);
      setRetryStates(prev => ({
        ...prev,
        [taskId]: { ...prev[taskId], error: 'Retry failed to start', progress: 0 }
      }));
    }
  };

  return (
    <div className="panel overflow-hidden p-0">
      <div className="border-b border-slate-800 bg-slate-900/50 p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Live Run Progress</h3>
          <div className="flex items-center gap-3">
            {failed > 0 && <span className="text-[10px] font-bold text-red-400 bg-red-400/10 px-1.5 rounded uppercase">{failed} Failed</span>}
            <span className="text-xs font-medium text-slate-400">
              {completed}/{total} Keywords Processed
            </span>
          </div>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div 
            className="h-full bg-indigo-500 transition-all duration-500 ease-out" 
            style={{ width: `${progress}%` }} 
          />
        </div>
      </div>

      <div className="max-h-60 overflow-y-auto p-2">
        <ul className="space-y-1">
          {tasks?.map((task) => {
            const retry = retryStates[task.id];
            const isRetrying = retry && task.status !== 'completed';

            return (
              <li key={task.id} className="flex flex-col rounded p-2 text-xs hover:bg-slate-800/50 transition-colors border border-transparent hover:border-slate-700/50">
                <div className="flex items-center justify-between w-full gap-2">
                  <span className="truncate font-medium text-slate-300 flex-1">{task.keyword}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    {(task.status === 'running' || isRetrying) && (
                      <span className="flex h-2 w-2">
                        <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-indigo-400 opacity-75"></span>
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500"></span>
                      </span>
                    )}
                    <span className={`rounded-sm px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                      task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                      task.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                      (task.status === 'running' || isRetrying) ? 'text-indigo-400' :
                      'bg-slate-700/50 text-slate-500'
                    }`}>
                      {isRetrying ? `Retrying ${Math.round(retry.progress)}%` : task.status}
                    </span>
                    {task.status === 'failed' && !isRetrying && (
                      <button 
                        onClick={() => handleRetry(task.id)}
                        className="rounded bg-slate-700 hover:bg-indigo-600 px-2 py-0.5 text-[10px] text-white transition-colors"
                      >
                        Retry
                      </button>
                    )}
                  </div>
                </div>
                
                {/* Status or Retry Progress */}
                {(isRetrying || (task.status === 'running' && task.status_message)) && (
                  <p className="mt-1 text-[10px] text-slate-500 italic animate-pulse">
                    {isRetrying ? 'Reprocessing keyword...' : task.status_message}
                  </p>
                )}

                {/* Error Display */}
                {(task.status === 'failed' || retry?.error) && (
                  <div className="mt-1 flex flex-col gap-1">
                    <p className="text-[10px] text-red-400/80 leading-relaxed bg-red-400/5 p-1 rounded border border-red-400/10">
                      <span className="font-bold mr-1">Error:</span>
                      {retry?.error || task.error_message || 'Unknown failure'}
                      {retry?.attempts > 1 && <span className="ml-2 opacity-60">(Attempt {retry.attempts})</span>}
                    </p>
                  </div>
                )}
              </li>
            );
          })}
          {total === 0 && <li className="py-8 text-center text-xs text-slate-500 italic">No keywords dispatched for this run</li>}
        </ul>
      </div>
    </div>
  );
}
