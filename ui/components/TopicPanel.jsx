'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
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

    return () => { mounted = false; };
  }, [selected, runId]);

  return (
    <aside className="panel h-full flex flex-col border-l border-slate-800">
      <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/40">
        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">Topic Strategy Panel</h2>
        {selected && (
            <button 
              onClick={() => setSelected(null)}
              className="text-slate-500 hover:text-slate-300 transition-colors"
            >
              ✕
            </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
        {!selected && (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-50 grayscale">
             <div className="w-16 h-16 rounded-full bg-slate-800 border-2 border-dashed border-slate-700 mb-4 animate-pulse flex items-center justify-center">
                <span className="text-2xl">🪄</span>
             </div>
             <p className="text-sm text-slate-400 max-w-[200px]">Select a topic node from the universe to view intelligence.</p>
          </div>
        )}

        {selected && (
          <div className="space-y-6">
            <header className="space-y-1">
              <h3 className="text-xl font-bold text-white">{selected.label}</h3>
              <p className="text-xs text-indigo-400 font-medium">Semantic Cluster: Enterprise Strategy</p>
            </header>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/30">
                <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Search Volume</p>
                <p className="text-lg font-semibold flex items-center gap-2">
                  4.2k <span className="text-xs text-green-400 font-normal">↑ 12%</span>
                </p>
              </div>
              <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/30">
                <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Difficulty</p>
                <div className="flex items-center gap-2">
                  <p className="text-lg font-semibold">68<span className="text-xs text-slate-500 font-normal">/100</span></p>
                  <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500 rounded-full" style={{ width: '68%' }}></div>
                  </div>
                </div>
              </div>
            </div>

            {loading && (
              <div className="space-y-4 animate-pulse pt-4">
                <div className="h-4 bg-slate-800 rounded w-1/2"></div>
                <div className="h-20 bg-slate-800 rounded"></div>
              </div>
            )}

            {!loading && (
              <>
                <section>
                  <h4 className="text-xs font-bold uppercase text-slate-500 mb-3 tracking-widest">Top Competitors</h4>
                  <div className="space-y-2">
                    {Array.isArray(coverage) && coverage.length > 0 ? coverage.slice(0, 3).map((c, i) => (
                      <div key={i} className="flex justify-between items-center text-sm p-2 rounded bg-slate-800/30">
                        <span className="text-slate-300">{c.domain}</span>
                        <span className="text-indigo-400 font-mono font-bold">{c.article_count} articles</span>
                      </div>
                    )) : <p className="text-xs text-slate-600 italic">No coverage data detected for this cluster.</p>}
                  </div>
                </section>

                <section>
                  <h4 className="text-xs font-bold uppercase text-slate-500 mb-3 tracking-widest">Strategic Pillars</h4>
                  <div className="space-y-2">
                    {Array.isArray(strategies) && strategies.length > 0 ? strategies.map((s, i) => (
                      <div key={i} className="p-3 rounded-lg bg-indigo-900/10 border border-indigo-900/30 hover:border-indigo-500/50 transition-all cursor-pointer group">
                        <h5 className="text-sm font-semibold text-indigo-100 group-hover:text-indigo-400">{s.title}</h5>
                        <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">{s.description}</p>
                      </div>
                    )) : <p className="text-xs text-slate-600 italic">No strategies generated yet.</p>}
                  </div>
                </section>
              </>
            )}
          </div>
        )}
      </div>

      {selected && (
        <div className="p-4 bg-slate-900/60 border-t border-slate-800 grid grid-cols-2 gap-2">
          <Link 
            href={`/article-explorer?topic_id=${selected.id}`}
            className="text-center text-[11px] font-bold uppercase py-2 bg-indigo-600 rounded text-white hover:bg-indigo-500 transition-colors shadow-lg shadow-indigo-900/20"
          >
            Explore Articles
          </Link>
          <Link 
            href={`/pillar-builder?topic_id=${selected.id}`}
            className="text-center text-[11px] font-bold uppercase py-2 bg-slate-800 rounded text-slate-200 hover:bg-slate-700 transition-colors"
          >
            Build Pillar
          </Link>
        </div>
      )}
    </aside>
  );
}
