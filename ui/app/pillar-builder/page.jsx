'use client';

import { useRun } from '@/components/RunContext';
import { useApiData } from '@/hooks/useApiData';

export default function PillarBuilderPage() {
  const { runId } = useRun();
  const { data, loading, error } = useApiData('/strategies', runId);

  return (
    <section className="panel p-4">
      <h2 className="mb-3 text-lg font-semibold">Pillar Builder</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-300">API unavailable</p>}
      <div className="space-y-4">
        {(data?.strategies || []).map((item) => (
          <article key={item.topic_id} className="rounded border border-slate-700 p-3">
            <h3 className="font-medium">{item.topic || item.topic_id}</h3>
            <p className="mt-1 text-sm text-slate-300">{item.pillar_outline || 'No outline yet.'}</p>
            <textarea className="mt-2 w-full rounded bg-slate-800 p-2" rows={5} defaultValue={item.pillar_outline || ''} />
            <div className="mt-2 flex gap-2">
              <button className="rounded bg-indigo-600 px-3 py-1 text-sm">Save Strategy</button>
              <button className="rounded bg-slate-700 px-3 py-1 text-sm">Export Brief</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
