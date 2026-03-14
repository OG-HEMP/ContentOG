import { useSearchParams } from 'next/navigation';
import CoverageMatrix from '@/components/CoverageMatrix';

export default function CoverageMatrixPage() {
  const searchParams = useSearchParams();
  const topicId = searchParams.get('topic_id');
  return <CoverageMatrix topicId={topicId} />;
}
