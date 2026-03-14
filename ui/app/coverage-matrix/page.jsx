'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import CoverageMatrix from '@/components/CoverageMatrix';

function CoverageMatrixContent() {
  const searchParams = useSearchParams();
  const topicId = searchParams.get('topic_id');
  return <CoverageMatrix topicId={topicId} />;
}

export default function CoverageMatrixPage() {
  return (
    <Suspense fallback={<div className="animate-pulse p-8 text-slate-500">Loading Coverage Analysis...</div>}>
      <CoverageMatrixContent />
    </Suspense>
  );
}
