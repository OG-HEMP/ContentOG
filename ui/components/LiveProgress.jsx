'use client';

import { useState, useEffect } from 'react';
import { useApiData } from '@/hooks/useApiData';
import { apiPost } from '@/lib/api';

export default function LiveProgress({ runId }) {
  const { data: tasks, loading, error } = useApiData(`/runs/${runId}/tasks`, null, {
    refreshInterval: 3000 // Poll every 3 seconds
  });

  const [isRetryingMap, setIsRetryingMap] = useState({});

  if (loading && !tasks) return <div className="animate-pulse py-4 text-sm text-slate-400">Loading progress...</div>;
  if (error) return null;

  const total = tasks?.length || 0;
  const completed = tasks?.filter(t => t.status === 'completed').length || 0;
  const failed = tasks?.filter(t => t.status === 'failed').length || 0;
  const progress = total > 0 ? ((completed + failed) / total) * 100 : 0;

  const handleRetry = async (taskId) => {
    setIsRetryingMap(prev => ({ ...prev, [taskId]: true }));
    try {
      await apiPost(`/tasks/${taskId}/retry`);
      // No need to clear error here, the next poll will update task status to 'pending' or 'running'
    } catch (err) {
      console.error('Failed to retry task:', err);
      // We could show a toast here if we had a toast system
    } finally {
      setIsRetryingMap(prev => ({ ...prev, [taskId]: false }));
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
            const isRetrying = isRetryingMap[task.id] || task.status === 'pending';
            const isRunning = task.status === 'running';

            return (
              <li key={task.id} className="flex flex-col rounded p-2 text-xs hover:bg-slate-800/50 transition-colors border border-transparent hover:border-slate-700/50">
                <div className="flex items-center justify-between w-full gap-2">
                  <span className="truncate font-medium text-slate-300 flex-1">{task.keyword}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    {(isRunning || isRetrying) && (
                      <span className="flex h-2 w-2">
                        <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-indigo-400 opacity-75"></span>
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500"></span>
                      </span>
                    )}
                    <span className={`rounded-sm px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                      task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                      task.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                      (isRunning || isRetrying) ? 'text-indigo-400' :
                      'bg-slate-700/50 text-slate-500'
                    }`}>
                      {isRetrying ? 'Pending' : task.status}
                    </span>
                    {task.status === 'failed' && (
                      <button 
                        disabled={isRetrying}
                        onClick={() => handleRetry(task.id)}
                        className={`rounded px-2 py-0.5 text-[10px] text-white transition-colors ${
                          isRetrying ? 'bg-slate-600 cursor-not-allowed' : 'bg-slate-700 hover:bg-indigo-600'
                        }`}
                      >
                        {isRetrying ? 'Starting...' : 'Retry'}
                      </button>
                    )}
                  </div>
                </div>
                
                {/* Status Message */}
                {(isRunning || isRetrying || task.status_message) && task.status !== 'completed' && (
                  <p className="mt-1 text-[10px] text-slate-500 italic animate-pulse">
                    {task.status_message || (isRetrying ? 'Re-dispatching...' : 'Processing...')}
                  </p>
                )}

                {/* Error Display */}
                {task.status === 'failed' && (
                  <div className="mt-1 flex flex-col gap-1">
                    <p className="text-[10px] text-red-400/80 leading-relaxed bg-red-400/5 p-1 rounded border border-red-400/10">
                      <span className="font-bold mr-1">Error:</span>
                      {task.error_message || 'Unknown failure'}
                      {task.retry_count > 0 && <span className="ml-2 opacity-60">(Attempt {task.retry_count + 1})</span>}
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
