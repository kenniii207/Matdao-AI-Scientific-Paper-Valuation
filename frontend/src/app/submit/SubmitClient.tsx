'use client';

import anime from 'animejs';
import gsap from 'gsap';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import AppHeader from '@/components/AppHeader';
import AppFooter from '@/components/AppFooter';
import { apiUrl, fetchWithTimeout } from '@/lib/api';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';

type UploadState = 'idle' | 'uploading' | 'error';
type UploadPhase = 'idle' | 'uploading' | 'processing' | 'finalizing' | 'error';

type UploadApiResponse = {
  paper_id?: string | number;
  detail?: string;
  error?: string;
};

const isUploadApiResponse = (value: unknown): value is UploadApiResponse => {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  if ('paper_id' in candidate && typeof candidate.paper_id !== 'string' && typeof candidate.paper_id !== 'number') {
    return false;
  }
  if ('detail' in candidate && typeof candidate.detail !== 'string') {
    return false;
  }
  if ('error' in candidate && typeof candidate.error !== 'string') {
    return false;
  }
  return true;
};

export default function SubmitClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const intent = searchParams.get('intent');
  const reducedMotion = usePrefersReducedMotion();

  const shellRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadStageRef = useRef<HTMLDivElement | null>(null);
  const phaseRefs = useRef<Array<HTMLDivElement | null>>([]);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [uploadPhase, setUploadPhase] = useState<UploadPhase>('idle');
  const [message, setMessage] = useState<string>('');

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
  const uploadPhaseIndex =
    uploadPhase === 'uploading' ? 1 : uploadPhase === 'processing' ? 2 : uploadPhase === 'finalizing' ? 3 : 0;
  const uploadProgress = uploadPhase === 'uploading' ? 34 : uploadPhase === 'processing' ? 73 : uploadPhase === 'finalizing' ? 100 : 0;

  useEffect(() => {
    if (reducedMotion || !shellRef.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '[data-submit-item]',
        { y: 16, autoAlpha: 0 },
        { y: 0, autoAlpha: 1, duration: 0.45, ease: 'power2.out', stagger: 0.07 }
      );
    }, shellRef);
    return () => ctx.revert();
  }, [reducedMotion]);

  useEffect(() => {
    if (reducedMotion || uploadState !== 'uploading' || !uploadStageRef.current) return;
    const stageNode = uploadStageRef.current;
    anime.remove(stageNode);
    const pulse = anime({
      targets: stageNode,
      scale: [1, 1.008, 1],
      opacity: [1, 0.92, 1],
      duration: 900,
      easing: 'easeInOutSine',
      loop: true,
    });
    return () => {
      pulse.pause();
      anime.remove(stageNode);
    };
  }, [uploadState, reducedMotion]);

  useEffect(() => {
    if (reducedMotion || uploadState !== 'uploading' || uploadPhaseIndex <= 0) return;
    const activeNode = phaseRefs.current[uploadPhaseIndex - 1];
    if (!activeNode) return;
    anime.remove(activeNode);
    anime({
      targets: activeNode,
      scale: [0.96, 1.035, 1],
      duration: 380,
      easing: 'easeOutCubic',
    });
  }, [uploadPhaseIndex, uploadState, reducedMotion]);

  const uploadFile = async (file: File) => {
    setUploadState('uploading');
    setUploadPhase('uploading');
    setMessage('Uploading PDF and extracting text...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      let res: Response | null = null;
      let data: UploadApiResponse = {};
      let lastError: Error | null = null;
      for (let attempt = 1; attempt <= 2; attempt += 1) {
        try {
          res = await fetchWithTimeout(apiUrl('/api/upload'), { method: 'POST', body: formData }, 35000);
          const parsed: unknown = await res.json().catch(() => ({}));
          data = isUploadApiResponse(parsed) ? parsed : {};
          break;
        } catch (err) {
          lastError = err instanceof Error ? err : new Error(String(err));
          if (attempt < 2) {
            setMessage('Connecting to backend... retrying upload once.');
            await new Promise((resolve) => setTimeout(resolve, 900));
          }
        }
      }
      if (!res) throw lastError || new Error('Unable to reach backend service.');

      if (!res.ok) {
        const detail = data?.detail || data?.error || 'Upload failed';
        throw new Error(detail);
      }

      const paperId = data?.paper_id;
      if (!paperId) throw new Error('Server response missing paper_id');

      setUploadPhase('processing');
      setMessage('Upload accepted. Running extraction and scoring checks...');
      await new Promise((resolve) => setTimeout(resolve, 500));
      setUploadPhase('finalizing');
      setMessage('Packaging result view...');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('matdao:navigate', {
            detail: { x: window.innerWidth / 2, y: window.innerHeight / 2 },
          })
        );
      }
      await new Promise((resolve) => setTimeout(resolve, reducedMotion ? 110 : 320));
      router.push(`/papers/${encodeURIComponent(String(paperId))}`);
    } catch (err) {
      setUploadState('error');
      setUploadPhase('error');
      setMessage(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-black">
      <AppHeader />

      <main className="flex-grow flex items-center justify-center px-5 sm:px-6 py-10 md:py-16">
        <div ref={shellRef} className="w-full max-w-4xl text-center">
          <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight text-white/85 mb-2" data-route-item data-submit-item>
            {headline}
          </h1>
          <p className="text-white/35 text-sm md:text-lg mb-8 md:mb-10" data-route-item data-submit-item>{helper}</p>

          <div
            className={`interactive-lift mx-auto w-full max-w-3xl rounded-2xl border px-5 sm:px-6 md:px-10 py-9 md:py-12 transition-colors ${
              uploadState === 'uploading'
                ? 'border-[#6efcff]/40 bg-[#6efcff]/5'
                : 'border-white/15 bg-black/30'
            }`}
            data-route-item
            data-submit-item
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

              {uploadState === 'uploading' ? (
                <div
                  ref={uploadStageRef}
                  className="w-full max-w-xl upload-stage rounded-xl border border-[#6efcff]/30 bg-[#6efcff]/10 px-4 py-4 mb-6 will-change-transform"
                >
                  <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.16em] text-[#b7fbff]/85">
                    <span>Pipeline Active</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="mt-3 upload-track progress-shimmer rounded-full">
                    <div className="upload-track-fill transition-[width] duration-500 ease-out" style={{ width: `${uploadProgress}%` }} />
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-white/55">
                    {['Upload', 'Process', 'Finalize'].map((phase, idx) => (
                      <div
                        key={phase}
                        ref={(node) => {
                          phaseRefs.current[idx] = node;
                        }}
                        className={`rounded-md border px-2 py-2 text-center transition-colors ${
                          uploadPhaseIndex > idx
                            ? 'border-[#6efcff]/45 bg-[#6efcff]/14 text-[#c9fdff]'
                            : 'border-white/10 bg-black/30'
                        }`}
                      >
                        {phase}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  <div className="text-sm text-white/45 mb-6">Drag &amp; Drop your paper here</div>
                  <div className="text-xs text-white/30 mb-6">Best results with text-based PDF, under 30MB.</div>
                </>
              )}

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
                {uploadState === 'uploading' ? 'Processing…' : 'Upload file'}
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
              data-route-item
              data-submit-item
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
              <div className={uploadState === 'error' ? 'text-error text-sm' : 'text-white/35 text-sm'}>
                {message}
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
