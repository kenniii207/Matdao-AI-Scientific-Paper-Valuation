'use client'; // Error components must be Client Components

import { useEffect } from 'react';
import Link from 'next/link';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Global application error caught by error.tsx:', error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-black p-6">
      <div className="workflow-panel rounded-xl p-10 border-red-500/[0.2] max-w-lg text-center shadow-[0_0_40px_rgba(255,0,0,0.1)]">
        <div className="text-red-400 mb-4 text-4xl">⚠️</div>
        <h2 className="font-headline text-2xl font-extrabold text-white mb-2">Platform Error</h2>
        <p className="text-white/60 text-sm mb-6">
          A critical rendering or extraction error occurred in this view.
          {error.message && <span className="block mt-3 p-2 bg-black/50 border border-white/10 rounded text-xs opacity-70 font-mono break-all">{error.message}</span>}
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/"
            className="px-6 py-3 bg-white/10 text-white font-bold rounded-lg border border-white/20 hover:bg-white/20 transition-colors"
          >
            Return Home
          </Link>
          <button
            type="button"
            className="px-6 py-3 bg-red-500/20 text-red-200 font-bold rounded-lg border border-red-500/30 hover:bg-red-500/30 transition-colors"
            onClick={() => reset()}
          >
            Try Again
          </button>
        </div>
      </div>
    </div>
  );
}
