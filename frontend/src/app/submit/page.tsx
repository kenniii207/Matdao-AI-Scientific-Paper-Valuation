import { Suspense } from 'react';
import SubmitClient from './SubmitClient';

function SubmitLoadingFallback() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-6" aria-busy="true" aria-live="polite">
      <div className="w-full max-w-3xl rounded-2xl border border-white/10 bg-white/[0.03] p-6 sm:p-8">
        <div className="h-5 w-40 rounded-md bg-white/10 animate-pulse mb-5" />
        <div className="h-3 w-2/3 rounded bg-white/10 animate-pulse mb-8" />
        <div className="space-y-3">
          <div className="h-12 rounded-xl bg-white/10 animate-pulse" />
          <div className="h-12 rounded-xl bg-white/10 animate-pulse" />
          <div className="h-12 rounded-xl bg-white/10 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

export default function SubmitPage() {
  return (
    <Suspense fallback={<SubmitLoadingFallback />}>
      <SubmitClient />
    </Suspense>
  );
}
