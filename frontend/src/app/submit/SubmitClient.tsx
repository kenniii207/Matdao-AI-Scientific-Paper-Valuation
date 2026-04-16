'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import AppHeader from '@/components/AppHeader';
import AppFooter from '@/components/AppFooter';

type UploadState = 'idle' | 'uploading' | 'error';

function formatDuration(totalSeconds: number) {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  if (minutes > 0) return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
  return `${seconds}s`;
}

export default function SubmitClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const intent = searchParams.get('intent');

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [message, setMessage] = useState<string>('');
  const [uploadStartedAt, setUploadStartedAt] = useState<number | null>(null);
  const [uploadElapsedSeconds, setUploadElapsedSeconds] = useState(0);

  const headline = useMemo(() => {
    if (intent === 'strength') return 'Validate research strength';
    if (intent === 'industry') return 'Find industry / investor fit';
    return 'Upload your research';
  }, [intent]);

  const helper = useMemo(() => {
    if (intent === 'strength')
      return 'Benchmark your work against peer standards and evaluate investability signals.';
    if (intent === 'industry')
      return 'Map research to real-world demand and identify institutional partner interest.';
    return 'We will analyze your work using our 4-layer evaluation pipeline.';
  }, [intent]);

  const primaryIntent = intent === 'evaluate' || !intent;
  const primaryCtaLabel = primaryIntent ? 'Start Prototype Evaluation' : 'Start Analysis';

  useEffect(() => {
    if (uploadState !== 'uploading' || !uploadStartedAt) {
      setUploadElapsedSeconds(0);
      return;
    }
    const timer = setInterval(() => {
      setUploadElapsedSeconds(Math.floor((Date.now() - uploadStartedAt) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [uploadState, uploadStartedAt]);

  const uploadFile = async (file: File) => {
    setUploadState('uploading');
    setUploadStartedAt(Date.now());
    setMessage('Uploading PDF and extracting text...');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${apiUrl}/api/upload`, { method: 'POST', body: formData });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const detail = data?.detail || data?.error || 'Upload failed';
        throw new Error(detail);
      }

      const paperId = data?.paper_id;
      if (!paperId) throw new Error('Server response missing paper_id');

      setMessage('Upload accepted. Evaluation running...');
      router.push(`/papers/${encodeURIComponent(String(paperId))}`);
    } catch (err) {
      setUploadState('error');
      setUploadStartedAt(null);
      setMessage(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-black">
      <AppHeader />

      <main className="flex-grow flex items-center justify-center px-5 sm:px-6 py-10 md:py-16">
        <div className="w-full max-w-4xl text-center">
          <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight text-white/85 mb-2">
            {headline}
          </h1>
          <p className="text-white/35 text-sm md:text-lg mb-8 md:mb-10">{helper}</p>

          <div
            className={`interactive-lift mx-auto w-full max-w-3xl rounded-2xl border px-5 sm:px-6 md:px-10 py-9 md:py-12 transition-colors ${
              uploadState === 'uploading'
                ? 'border-[#6efcff]/40 bg-[#6efcff]/5'
                : 'border-white/15 bg-black/30'
            }`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f) uploadFile(f);
            }}
          >
            <div className="flex flex-col items-center">
              <div className="material-symbols-outlined text-[56px] text-white/50 mb-4">
                description
              </div>

              <div className="text-sm text-white/45 mb-6">Drag &amp; Drop your paper here</div>
              <div className="text-xs text-white/30 mb-6">
                Best results with text-based PDF, under 30MB.
              </div>

              <div className="w-full flex items-center gap-4 mb-7">
                <div className="h-px bg-white/10 flex-1" />
                <div className="text-xs text-white/30">or</div>
                <div className="h-px bg-white/10 flex-1" />
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) uploadFile(f);
                }}
                disabled={uploadState === 'uploading'}
              />

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="focus-glow cta-premium rounded-full border border-white/20 bg-white/5 px-8 py-2.5 text-sm font-medium text-white/70 hover:bg-white/10 disabled:opacity-50"
                disabled={uploadState === 'uploading'}
              >
                {uploadState === 'uploading' ? 'Uploading…' : 'Upload file'}
              </button>

              <div className="mt-8 flex items-center justify-center gap-4 sm:gap-6 text-xs text-white/35">
                <button
                  type="button"
                  className="focus-glow rounded-md px-2 py-1 hover:text-white/60 transition-colors"
                  onClick={() => setMessage('DOI flow not wired yet — upload PDF for now.')}
                >
                  Paste DOI
                </button>
                <div className="h-4 w-px bg-white/10" />
                <button
                  type="button"
                  className="focus-glow rounded-md px-2 py-1 hover:text-white/60 transition-colors"
                  onClick={() => setMessage('Link flow not wired yet — upload PDF for now.')}
                >
                  Paste Link
                </button>
              </div>
            </div>
          </div>

          <div className="mt-8 md:mt-10 flex flex-col items-center gap-4">
            <button
              type="button"
              className={`focus-glow cta-premium rounded-full px-9 sm:px-12 py-4 text-sm font-semibold ${
                primaryIntent
                  ? 'border border-[#6efcff]/45 bg-[#6efcff]/15 text-[#d1feff] shadow-[0_0_20px_rgba(110,252,255,0.24)] hover:bg-[#6efcff]/25'
                  : 'border border-white/20 bg-white/5 text-white/80 hover:bg-white/10'
              }`}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadState === 'uploading'}
            >
              {primaryCtaLabel}
            </button>

            {message ? (
              <div className="space-y-1">
                <div className={uploadState === 'error' ? 'text-error text-sm' : 'text-white/35 text-sm'}>
                  {message}
                </div>
                {uploadState === 'uploading' ? (
                  <div className="text-xs text-[#9bf8ff]">
                    Elapsed: {formatDuration(uploadElapsedSeconds)} · Typical first result in ~45-90s
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="text-white/20 text-xs">Paper intent: {intent || 'evaluate'}</div>
            )}
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}
