'use client';

import { useEffect, useState } from 'react';
import { apiGet } from '@/lib/api';

export function useApiData(path, runId, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await apiGet(path, { runId, signal: controller.signal });
        setData(result);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err);
          setData(null);
        }
      } finally {
        setLoading(false);
      }
    }

    load();
    return () => controller.abort();
  }, [path, runId, ...deps]);

  return { data, loading, error };
}
