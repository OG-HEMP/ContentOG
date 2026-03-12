'use client';

import { useState } from 'react';
import { apiPost } from '@/lib/api';

export default function NewRunModal({ onClose, onRunStarted }) {
  const [keywords, setKeywords] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const keywordList = keywords
      .split('\n')
      .map((k) => k.strip ? k.strip() : k.trim())
      .filter((k) => k.length > 0);

    if (keywordList.length === 0) {
      setError('Please enter at least one keyword');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await apiPost('/runs', { keywords: keywordList });
      onRunStarted(result.run_id);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to start run');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md overflow-hidden rounded-xl border border-slate-700 bg-slate-900/90 shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="border-b border-slate-700 p-4">
          <h2 className="text-xl font-bold text-white">Start New Discovery</h2>
          <p className="text-sm text-slate-400">Enter seed keywords to begin topic extraction</p>
        </div>

        <form onSubmit={handleSubmit} className="p-4">
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Keywords (One per line)
            </label>
            <textarea
              className="h-32 w-full rounded-lg border border-slate-700 bg-slate-800 p-3 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="e.g. content marketing&#10;topic clusters&#10;SEO strategy"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="mb-4 rounded bg-red-900/30 p-2 text-xs text-red-300 border border-red-500/50">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Dispatching...
                </>
              ) : (
                'Start Discovery'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
