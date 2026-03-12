'use client';

import { createContext, useContext, useMemo, useState } from 'react';

const RunContext = createContext({
  runId: '',
  setRunId: () => {}
});

export function RunProvider({ children }) {
  const [runId, setRunId] = useState('');
  const value = useMemo(() => ({ runId, setRunId }), [runId]);
  return <RunContext.Provider value={value}>{children}</RunContext.Provider>;
}

export function useRun() {
  return useContext(RunContext);
}
