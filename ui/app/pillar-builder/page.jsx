'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useRun } from '@/components/RunContext';
import { useApiData } from '@/hooks/useApiData';

function PillarBuilderContent() {
  const { runId } = useRun();
  const searchParams = useSearchParams();
  const topicIdFromUrl = searchParams.get('topic_id');
  const { data: allStrategies, loading, error } = useApiData('/strategies', runId, { deps: [runId] });

  // If a topic_id was passed from Topic Universe, show only that topic; otherwise show all
  const data = topicIdFromUrl && Array.isArray(allStrategies)
    ? allStrategies.filter(s => s.topic_id === topicIdFromUrl)
    : allStrategies;
  const [outlines, setOutlines] = useState({});
  const [generating, setGenerating] = useState({});

  const handleGenerateOutline = async (topicId) => {
    if (generating[topicId]) return;
    
    setGenerating(prev => ({ ...prev, [topicId]: true }));
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8080'}/topics/${topicId}/outline`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Generation failed');
      const outline = await response.json();
      setOutlines(prev => ({ ...prev, [topicId]: outline }));
    } catch (err) {
      console.error(err);
      alert('Failed to generate outline. Please try again.');
    } finally {
      setGenerating(prev => ({ ...prev, [topicId]: false }));
    }
  };

  return (
    <section className="space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Pillar Strategy Builder</h1>
          <p className="text-sm text-slate-400">Define your core topic to generate an authority-building content map.</p>
        </div>
      </header>

      {loading && <p className="animate-pulse text-slate-500">Generating strategic insights...</p>}
      {error && <p className="text-red-400 bg-red-900/20 p-3 rounded border border-red-900/50">Strategy engine offline.</p>}

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {Array.isArray(data) && data.length > 0 ? (
          data.map((item) => (
            <article key={item.topic_id} className="panel flex flex-col h-full bg-slate-900/40 border-t-4 border-indigo-600 overflow-hidden hover:bg-slate-900/60 transition-all">
              <div className="p-5 flex-1 space-y-4">
                <header>
                   <h3 className="text-lg font-bold text-white line-clamp-2 leading-tight">{item.title || "Strategic Pillar"}</h3>
                   <p className="text-xs text-indigo-400 mt-1 uppercase tracking-widest font-bold">Priority: High Opportunity</p>
                </header>

                <div className="space-y-3">
                   <div className="bg-slate-800/40 p-3 rounded border border-slate-700/30">
                      <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Sub-topic Focus</p>
                      <p className="text-sm font-medium text-slate-200">Technical Implementation & Governance</p>
                   </div>
                   
                   <div className="p-3 rounded bg-indigo-900/10 border border-indigo-900/20 italic">
                      <p className="text-xs text-indigo-200/80 leading-relaxed italic">
                        "{item.description || 'Deep-dive into this topic cluster to identify semantic gaps.'}"
                      </p>
                   </div>
                </div>

                {outlines[item.topic_id] && (
                  <div className="mt-4 p-4 rounded bg-indigo-500/10 border border-indigo-500/20 space-y-3 animate-in fade-in slide-in-from-top-2">
                    <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-tight">Generated Outline</h4>
                    <p className="text-[11px] font-bold text-white">{outlines[item.topic_id].title}</p>
                    <div className="text-[10px] text-slate-400 space-y-1 max-h-40 overflow-y-auto">
                      {outlines[item.topic_id].sections?.map((s, idx) => (
                        <div key={idx}>• {s.heading}</div>
                      ))}
                    </div>
                    <button 
                      onClick={() => navigator.clipboard.writeText(JSON.stringify(outlines[item.topic_id], null, 2))}
                      className="text-[9px] text-indigo-300 hover:text-white transition-colors uppercase font-bold"
                    >
                      Copy JSON to Clipboard
                    </button>
                  </div>
                )}
              </div>

              <div className="p-4 bg-slate-950/50 border-t border-slate-800 grid grid-cols-2 gap-2">
                 <button 
                   onClick={() => handleGenerateOutline(item.topic_id)}
                   disabled={generating[item.topic_id]}
                   className={`text-[10px] font-bold uppercase py-2 rounded text-white transition-colors ${generating[item.topic_id] ? 'bg-indigo-800 cursor-not-allowed animate-pulse' : 'bg-indigo-600 hover:bg-indigo-500'}`}
                 >
                   {generating[item.topic_id] ? 'Generating...' : 'Generate Outline'}
                 </button>
                 <button 
                    onClick={() => window.open(`/article-explorer?topic_id=${item.topic_id}`)}
                    className="text-[10px] font-bold uppercase py-2 bg-slate-800 rounded text-slate-300 hover:bg-slate-700 transition-colors"
                 >
                    Research Links
                 </button>
              </div>
            </article>
          ))
        ) : !loading && (
          <div className="col-span-full text-center py-20 border-2 border-dashed border-slate-800 rounded-2xl">
             <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4 grayscale opacity-40">
                <span className="text-2xl">🧱</span>
             </div>
             <p className="text-slate-400 font-medium">No pillar strategies found for this run.</p>
             <p className="text-xs text-slate-600 mt-2 max-w-sm mx-auto leading-relaxed">Pillar strategies are generated automatically once topic clusters are identified. Try refreshing once the discovery pipeline completes.</p>
          </div>
        )}
      </div>
    </section>
  );
}

export default function PillarBuilderPage() {
  return (
    <Suspense fallback={<div className="animate-pulse p-8 text-slate-500">Loading Strategic Pillars...</div>}>
      <PillarBuilderContent />
    </Suspense>
  );
}
