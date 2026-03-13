'use client';

import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';
import { useSearchParams } from 'next/navigation';

export default function ArticleExplorerPage() {
  const { runId } = useRun();
  const searchParams = useSearchParams();
  const topicId = searchParams.get('topic_id');

  const { data, loading, error } = useApiData(
    topicId ? `/articles?topic_id=${topicId}` : '/articles',
    runId,
    { deps: [topicId, runId] }
  );

  return (
    <section className="space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Article Explorer</h1>
          <p className="text-sm text-slate-400">
            {topicId ? `Viewing articles for topic cluster ${topicId.slice(0, 8)}...` : 'Deep-dive into competitive content coverage across the industry.'}
          </p>
        </div>
      </header>

      {loading && <p className="animate-pulse text-slate-500">Retrieving article metadata...</p>}
      {error && <p className="text-red-400 bg-red-900/20 p-3 rounded border border-red-900/50">Failed to load articles.</p>}

      <div className="grid gap-6">
        {Array.isArray(data) && data.length > 0 ? (
          data.map((article) => (
            <article key={article.id} className="panel p-6 border-l-4 border-indigo-500 bg-slate-900/40 hover:bg-slate-900/60 transition-colors">
              <div className="flex justify-between items-start mb-3">
                <div className="space-y-1">
                  <h3 className="text-lg font-semibold text-slate-100">
                    <a href={article.url} target="_blank" rel="noopener noreferrer" className="hover:text-indigo-400 hover:underline">
                      {article.title || 'Untitled Article'}
                    </a>
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="bg-slate-800 px-2 py-0.5 rounded text-indigo-300 font-mono">{article.domain}</span>
                    <span>•</span>
                    <span>{article.publish_date ? new Date(article.publish_date).toLocaleDateString() : 'Date Unknown'}</span>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="text-center">
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-tighter">Word Count</p>
                    <p className="text-sm font-semibold">{article.word_count || 'N/A'}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-tighter">SERP Rank</p>
                    <p className="text-sm font-semibold text-amber-400">#{article.serp_rank || '?'}</p>
                  </div>
                </div>
              </div>

              <div className="mt-4 p-4 rounded bg-slate-800/50 border border-slate-700/30">
                <h4 className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-2">AI Summary</h4>
                <p className="text-sm text-slate-300 leading-relaxed italic">
                  {article.summary}...
                </p>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                 <span className="text-[10px] bg-slate-800 text-slate-400 border border-slate-700 px-2 py-1 rounded">Semantic Relevance: High</span>
                 <span className="text-[10px] bg-indigo-900/30 text-indigo-300 border border-indigo-900/50 px-2 py-1 rounded">Strategy Opportunity</span>
              </div>
            </article>
          ))
        ) : !loading && (
          <div className="text-center py-20 border-2 border-dashed border-slate-800 rounded-2xl">
            <p className="text-slate-500">No articles found for the selected criteria.</p>
            <p className="text-xs text-slate-600 mt-2">Try a different topic node in the universe or triggers a new run.</p>
          </div>
        )}
      </div>
    </section>
  );
}
