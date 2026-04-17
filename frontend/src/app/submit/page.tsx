import { Suspense } from 'react';
import SubmitClient from './SubmitClient';

export default function SubmitPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black" aria-busy="true" aria-live="polite" />}>
      <SubmitClient />
    </Suspense>
  );
}
