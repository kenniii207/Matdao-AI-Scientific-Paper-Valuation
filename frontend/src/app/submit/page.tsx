import { Suspense } from 'react';
import SubmitClient from './SubmitClient';

export default function SubmitPage() {
  return (
    <Suspense fallback={null}>
      <SubmitClient />
    </Suspense>
  );
}

