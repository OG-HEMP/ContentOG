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
  const { data, loading, error } = useApiData('/coverage', runId);
  const [sortBy, setSortBy] = useState('gap_score');

  const rows = useMemo(() => {
    const topics = data?.topics || [];
    return [...topics].sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0));
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
            {rows.map((row) => (
              <tr key={row.topic_id} className="border-t border-slate-700">
                <td className="py-2">{row.topic_name || row.topic_id}</td>
                <td>{row.your_domain_count || 0}</td>
                <td>{row.competitor_a_count || 0}</td>
                <td>{row.competitor_b_count || 0}</td>
                <td>
                  <span className={`rounded px-2 py-1 ${gapColor(row.gap_score || 0)}`}>{row.gap_score || 0}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
