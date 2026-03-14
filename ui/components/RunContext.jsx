'use client';

import { createContext, useContext, useMemo, useState } from 'react';
import { useApiData } from '@/hooks/useApiData';

const RunContext = createContext({
  runId: '',
  setRunId: () => {},
  currentRun: null,
});

export function RunProvider({ children }) {
  const [runId, setRunId] = useState('');
  const { data: runs } = useApiData('/runs');
  const currentRun = (Array.isArray(runs) ? runs : runs?.runs)?.find(r => String(r.id) === String(runId)) ?? null;
  const value = useMemo(() => ({ runId, setRunId, currentRun }), [runId, currentRun]);
  return <RunContext.Provider value={value}>{children}</RunContext.Provider>;
}

export function useRun() {
  return useContext(RunContext);
}
