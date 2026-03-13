'use client';

import { useApiData } from '@/hooks/useApiData';

export default function LiveProgress({ runId }) {
  const { data: tasks, loading, error } = useApiData(`/runs/${runId}/tasks`, null, {
    refreshInterval: 3000 // Poll every 3 seconds
  });

  if (loading && !tasks) return <div className="animate-pulse py-4 text-sm text-slate-400">Loading progress...</div>;
  if (error) return null;

  const total = tasks?.length || 0;
  const completed = tasks?.filter(t => t.status === 'completed').length || 0;
  const failed = tasks?.filter(t => t.status === 'failed').length || 0;
  const active = tasks?.filter(t => t.status === 'running').length || 0;
  const progress = total > 0 ? ((completed + failed) / total) * 100 : 0;

  return (
    <div className="panel overflow-hidden p-0">
      <div className="border-b border-slate-800 bg-slate-900/50 p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Live Run Progress</h3>
          <span className="text-xs font-medium text-slate-400">
            {completed}/{total} Keywords Processed
          </span>
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
          {tasks?.map((task) => (
            <li key={task.id} className="flex flex-col rounded p-2 text-xs hover:bg-slate-800/50">
              <div className="flex items-center justify-between w-full">
                <span className="truncate font-medium text-slate-300">{task.keyword}</span>
                <div className="flex items-center gap-2">
                  {task.status === 'running' && (
                    <span className="flex h-2 w-2">
                      <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-indigo-400 opacity-75"></span>
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-indigo-500"></span>
                    </span>
                  )}
                  <span className={`rounded px-1.5 py-0.5 font-bold uppercase transition-colors ${
                    task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                    task.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                    task.status === 'running' ? 'text-indigo-400' :
                    'bg-slate-700/50 text-slate-500'
                  }`}>
                    {task.status}
                  </span>
                </div>
              </div>
              {task.status === 'running' && task.status_message && (
                <p className="mt-1 text-[10px] text-slate-500 italic animate-pulse">
                  {task.status_message}
                </p>
              )}
              {task.status === 'failed' && task.error_message && (
                <p className="mt-1 text-[10px] text-red-400/80">
                  Error: {task.error_message}
                </p>
              )}
            </li>
          ))}
          {total === 0 && <li className="py-4 text-center text-xs text-slate-500">No tasks found for this run</li>}
        </ul>
      </div>
    </div>
  );
}
