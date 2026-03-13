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

  const rows = useMemo(() => {
    if (!data || typeof data !== 'object') return [];
    
    // Transform { topic_id: [ {domain, article_count, avg_rank}, ... ] } 
    // into rows for the table
    return Object.entries(data).map(([topicId, stats]) => {
      const yourDomain = stats.find(s => s.domain.includes('contentog') || s.domain.includes('your-domain')) || {};
      const competitors = stats.filter(s => !s.domain.includes('contentog') && !s.domain.includes('your-domain'));
      
      const yourCount = yourDomain.article_count || 0;
      const competitorAvg = competitors.length > 0 
        ? competitors.reduce((acc, c) => acc + (c.article_count || 0), 0) / competitors.length 
        : 0;
      
      // Heuristic gap score: high if competitors have many articles and you have few
      const gapScore = Math.min(100, Math.max(0, Math.round((competitorAvg - yourCount) * 10)));

      return {
        topic_id: topicId,
        topic_name: `Topic ${topicId.slice(0, 4)}`, // Fallback since names aren't in /coverage
        your_domain_count: yourCount,
        competitor_a_count: competitors[0]?.article_count || 0,
        competitor_b_count: competitors[1]?.article_count || 0,
        gap_score: gapScore
      };
    }).sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0));
  }, [data, sortBy]);

  return (
    <section className="panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Coverage Matrix</h2>
        <select className="rounded bg-slate-800 px-2 py-1 text-sm" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="gap_score">Sort by Gap Score</option>
          <option value="your_domain_count">Sort by Your Domain</option>
        </select>
      </div>
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-300">API unavailable</p>}
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-300">
              <th>Topic</th>
              <th>Your Domain</th>
              <th>Competitor A</th>
              <th>Competitor B</th>
              <th>Gap Score</th>
            </tr>
          </thead>
          <tbody>
            {rows.length > 0 ? (
              rows.map((row) => (
                <tr key={row.topic_id} className="border-t border-slate-700">
                  <td className="py-2">{row.topic_name || row.topic_id}</td>
                  <td>{row.your_domain_count || 0}</td>
                  <td>{row.competitor_a_count || 0}</td>
                  <td>{row.competitor_b_count || 0}</td>
                  <td>
                    <span className={`rounded px-2 py-1 ${gapColor(row.gap_score || 0)}`}>{row.gap_score || 0}</span>
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
