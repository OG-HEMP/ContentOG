'use client';

import { useMemo, useState } from 'react';
import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';

function gapColor(score) {
  if (score >= 70) return 'bg-red-700';
  if (score >= 40) return 'bg-orange-600';
  return 'bg-green-700';
}

export default function CoverageMatrix() {
  const { runId } = useRun();
  const { data, loading, error } = useApiData('/coverage', runId, { deps: [runId] });
  const [sortBy, setSortBy] = useState('gap_score');
  const [userDomain, setUserDomain] = useState('contentog.com');

  const rows = useMemo(() => {
    if (!data || typeof data !== 'object') return [];
    
    return Object.entries(data).map(([topicId, stats]) => {
      const topicName = stats[0]?.topic_name || `Topic ${topicId.slice(0, 4)}`;
      const yourDomain = stats.find(s => s.domain.toLowerCase().includes(userDomain.toLowerCase())) || {};
      const competitors = stats.filter(s => !s.domain.toLowerCase().includes(userDomain.toLowerCase()));
      
      const yourCount = yourDomain.article_count || 0;
      const competitorAvg = competitors.length > 0 
        ? competitors.reduce((acc, c) => acc + (c.article_count || 0), 0) / competitors.length 
        : 0;
      
      const gapScore = Math.min(100, Math.max(0, Math.round((competitorAvg - yourCount) * 10)));

      return {
        topic_id: topicId,
        topic_name: topicName,
        your_domain_count: yourCount,
        competitor_a_count: competitors[0]?.article_count || 0,
        competitor_b_count: competitors[1]?.article_count || 0,
        competitor_a_name: competitors[0]?.domain || 'Competitor A',
        competitor_b_name: competitors[1]?.domain || 'Competitor B',
        gap_score: gapScore
      };
    }).sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0));
  }, [data, sortBy, userDomain]);

  return (
    <section className="panel p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">Coverage Matrix</h2>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Your Domain:</span>
            <input 
              className="rounded bg-slate-800 px-2 py-1 text-xs border border-slate-700 focus:border-indigo-500 outline-none"
              value={userDomain}
              onChange={(e) => setUserDomain(e.target.value)}
              placeholder="e.g. contentog.com"
            />
          </div>
          <select className="rounded bg-slate-800 px-2 py-1 text-sm border border-slate-700" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="gap_score">Sort by Gap Score</option>
            <option value="your_domain_count">Sort by Your Domain</option>
          </select>
        </div>
      </div>
      {loading && <p className="animate-pulse text-sm text-slate-400">Calculating coverage...</p>}
      {error && <p className="text-red-300">API unavailable</p>}
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-300 border-b border-slate-800">
              <th className="pb-2">Keyword Topic</th>
              <th className="pb-2">Your Domain</th>
              <th className="pb-2">Competitor A</th>
              <th className="pb-2">Competitor B</th>
              <th className="pb-2">Gap Score</th>
            </tr>
          </thead>
          <tbody>
            {rows.length > 0 ? (
              rows.map((row) => (
                <tr key={row.topic_id} className="border-t border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                  <td className="py-3 pr-4 font-medium text-slate-200">{row.topic_name}</td>
                  <td>
                    <div className="flex flex-col">
                      <span className="font-semibold text-white">{row.your_domain_count}</span>
                      <span className="text-[10px] text-slate-500 uppercase">{userDomain}</span>
                    </div>
                  </td>
                  <td>
                    <div className="flex flex-col">
                      <span className="font-medium text-slate-300">{row.competitor_a_count}</span>
                      <span className="text-[10px] text-slate-500 truncate max-w-[100px]" title={row.competitor_a_name}>{row.competitor_a_name}</span>
                    </div>
                  </td>
                  <td>
                    <div className="flex flex-col">
                      <span className="font-medium text-slate-300">{row.competitor_b_count}</span>
                      <span className="text-[10px] text-slate-500 truncate max-w-[100px]" title={row.competitor_b_name}>{row.competitor_b_name}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`inline-block min-w-[2.5rem] text-center rounded px-2 py-1 font-bold ${gapColor(row.gap_score || 0)}`}>
                      {row.gap_score}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="py-10 text-center text-slate-500 italic">
                  No coverage data available yet. Select a run with completed topic extraction to view the matrix.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
