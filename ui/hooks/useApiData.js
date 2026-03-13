'use client';

import { useEffect, useState } from 'react';
import { apiGet } from '@/lib/api';

export function useApiData(path, runId, { deps = [], refreshInterval = null } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let controller = new AbortController();
    let timer = null;

    async function load(isManual = true) {
      if (!path) {
        setLoading(false);
        return;
      }
      if (isManual) {
        setLoading(true);
        setError(null);
      }
      
      try {
        const result = await apiGet(path, { runId, signal: controller.signal });
        setData(result);
        
        if (refreshInterval && !controller.signal.aborted) {
          timer = setTimeout(() => load(false), refreshInterval);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err);
          setData(null);
        }
      } finally {
        if (isManual) setLoading(false);
      }
    }

    load();
    
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [path, runId, version, refreshInterval, ...deps]);

  const refresh = () => setVersion((v) => v + 1);

  return { data, loading, error, refresh };
}
