'use client';

import { useEffect, useMemo, useState } from 'react';
import { useApiData } from '@/hooks/useApiData';
import { useRun } from '@/components/RunContext';

function gapColor(score) {
  if (score >= 70) return 'bg-red-700';
  if (score >= 40) return 'bg-orange-600';
  return 'bg-green-700';
}

export default function CoverageMatrix({ topicId }) {
  const { runId, currentRun } = useRun();
  const { data, loading: apiLoading, error: apiError } = useApiData('/coverage', runId, { 
    deps: [runId, topicId],
    params: topicId ? { topic_id: topicId } : {}
  });
  const [sortBy, setSortBy] = useState('gap_score');
  const [yourDomain, setYourDomain] = useState('contentog.com');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Pre-fill from run metadata if available
  useEffect(() => {
    if (currentRun?.target_domain) {
      setYourDomain(currentRun.target_domain);
    }
  }, [currentRun]);

  const handleCalculateGap = async (e) => {
    if (e) e.preventDefault();
    if (!yourDomain) return;
    
    setLoading(true);
    setError(null);
    try {
      console.log('Calculating gap for:', yourDomain);
      await new Promise(r => setTimeout(r, 800));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const rows = useMemo(() => {
    if (!data || typeof data !== 'object') return [];
    
    return Object.entries(data).map(([topicId, stats]) => {
      // stats might be an object if API returned a list and and Object.entries was used on it,
      // but api/app.py returns a dict of lists. Still, let's be safe.
      const statsArray = Array.isArray(stats) ? stats : [];
      
      const topicName = statsArray[0]?.topic_name || `Topic ${topicId.slice(0, 8)}`;
      
      const yourDomainStats = statsArray.find(s => 
        s.domain?.toLowerCase().includes(yourDomain?.toLowerCase() || '')
      ) || {};
      
      const competitors = statsArray.filter(s => 
        !s.domain?.toLowerCase().includes(yourDomain?.toLowerCase() || '')
      );
      
      const yourCount = yourDomainStats.article_count || 0;
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
    }).sort((a, b) => {
      if (sortBy === 'gap_score') return (b.gap_score || 0) - (a.gap_score || 0);
      if (sortBy === 'your_domain_count') return (b.your_domain_count || 0) - (a.your_domain_count || 0);
      return 0;
    });
  }, [data, sortBy, yourDomain]);

  if (apiError) {
    return (
      <section className="panel p-8 text-center">
        <p className="text-red-400">Coverage Matrix Unavailable</p>
        <p className="text-sm text-slate-500 mt-2">{apiError.message || 'API connection failed'}</p>
      </section>
    );
  }

  return (
    <section className="panel p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">Coverage Matrix</h2>
        <div className="flex items-center gap-3">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="mb-2 block text-sm font-medium text-slate-400">Your Domain</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 p-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
                  placeholder="e.g. contentog.com"
                  value={yourDomain}
                  onChange={(e) => setYourDomain(e.target.value)}
                  disabled={loading}
                />
                <button
                  onClick={handleCalculateGap}
                  disabled={loading || !yourDomain}
                  className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
                >
                  {loading ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : 'Update'}
                </button>
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs font-medium text-slate-400">
              <select className="rounded bg-slate-800 px-2 py-1 text-sm border border-slate-700 text-white" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="gap_score">Sort by Gap Score</option>
                <option value="your_domain_count">Sort by Your Domain</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      
      {(apiLoading || loading) && <p className="animate-pulse text-sm text-slate-400 mb-4">Analyzing competitor coverage...</p>}
      
      <div className="overflow-auto max-h-[500px]">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-900 shadow-sm z-10">
            <tr className="text-left text-slate-300 border-b border-slate-800">
              <th className="pb-3 px-2">Topic Cluster</th>
              <th className="pb-3 px-2">Your Profile</th>
              <th className="pb-3 px-2">Competitor A</th>
              <th className="pb-3 px-2">Competitor B</th>
              <th className="pb-3 px-2">Gap Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {rows.length > 0 ? (
              rows.map((row) => (
                <tr key={row.topic_id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-4 px-2 font-medium text-slate-100 max-w-[200px] truncate" title={row.topic_name}>{row.topic_name}</td>
                  <td className="px-2">
                    <div className="flex flex-col">
                      <span className="font-bold text-white text-base">{row.your_domain_count}</span>
                      <span className="text-[10px] text-slate-500 uppercase tracking-tight">{yourDomain}</span>
                    </div>
                  </td>
                  <td className="px-2">
                    <div className="flex flex-col">
                      <span className="font-medium text-slate-300">{row.competitor_a_count}</span>
                      <span className="text-[10px] text-slate-500 truncate max-w-[100px]" title={row.competitor_a_name}>{row.competitor_a_name}</span>
                    </div>
                  </td>
                  <td className="px-2">
                    <div className="flex flex-col">
                      <span className="font-medium text-slate-300">{row.competitor_b_count}</span>
                      <span className="text-[10px] text-slate-500 truncate max-w-[100px]" title={row.competitor_b_name}>{row.competitor_b_name}</span>
                    </div>
                  </td>
                  <td className="px-2">
                    <span className={`inline-flex items-center justify-center min-w-[3rem] px-2 py-1 rounded text-xs font-black uppercase tracking-wider ${gapColor(row.gap_score)}`}>
                      {row.gap_score}% Gap
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="py-12 text-center text-slate-500 italic">
                  {apiLoading ? 'Collecting data...' : 'No coverage data found for this run.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
