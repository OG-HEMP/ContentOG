'use client';

import Sidebar from '@/components/Sidebar';
import Topbar from '@/components/Topbar';
import TopicPanel from '@/components/TopicPanel';
import { RunProvider } from '@/components/RunContext';

export default function AppShell({ children }) {
  return (
    <RunProvider>
      <div className="min-h-screen p-4">
        <Topbar />
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-2">
            <Sidebar />
          </div>
          <main className="col-span-7">{children}</main>
          <div className="col-span-3">
            <TopicPanel />
          </div>
        </div>
      </div>
    </RunProvider>
  );
}
