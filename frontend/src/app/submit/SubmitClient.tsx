'use client';

import anime from 'animejs';
import gsap from 'gsap';
import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useRouter, useSearchParams } from 'next/navigation';
import AppHeader from '@/components/AppHeader';
import AppFooter from '@/components/AppFooter';
import { apiUrl, fetchWithTimeout } from '@/lib/api';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';
import { WebGLShader } from '@/components/ui/web-gl-shader';
import { LoadingScreen } from '@/components/ui/loading-screen';

type UploadState = 'idle' | 'uploading' | 'error';
type UploadPhase = 'idle' | 'uploading' | 'processing' | 'finalizing' | 'error';

type UploadApiResponse = {
  paper_id?: string | number;
  detail?: string;
  error?: string;
};

const UPLOAD_TIMEOUT_MS = 90_000;
const MAX_UPLOAD_ATTEMPTS = 3;

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

function UploadVector({
  phase,
  intent,
}: {
  phase: UploadPhase;
  intent: string | null;
}) {
  const accent = intent === 'industry' ? '#b594ff' : intent === 'strength' ? '#95f1ff' : '#78fbff';
  const isBusy = phase === 'uploading' || phase === 'processing' || phase === 'finalizing';

  return (
    <div className="relative h-24 w-24">
      <motion.div
        className="absolute inset-0 rounded-full blur-xl"
        style={{ backgroundColor: `${accent}33` }}
        animate={isBusy ? { scale: [0.9, 1.08, 0.9], opacity: [0.35, 0.75, 0.35] } : { scale: 1, opacity: 0.45 }}
        transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.svg
        viewBox="0 0 120 120"
        className="relative h-full w-full"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <motion.circle
          cx="60"
          cy="60"
          r="35"
          stroke={accent}
          strokeWidth="3"
          strokeOpacity="0.85"
          strokeDasharray="10 8"
          animate={isBusy ? { rotate: 360 } : { rotate: 0 }}
          transition={{ duration: 9, repeat: Infinity, ease: 'linear' }}
          style={{ transformOrigin: '50% 50%' }}
        />
        <motion.path
          d={intent === 'industry' ? 'M30 72L50 48L66 61L91 40' : intent === 'strength' ? 'M28 78L45 78L45 60L58 60L58 49L72 49L72 40L90 40' : 'M30 66C40 52 50 45 62 45C74 45 84 53 90 66'}
          stroke={accent}
          strokeWidth="4"
          strokeLinecap="round"
          animate={isBusy ? { pathLength: [0.45, 1, 0.45], opacity: [0.55, 1, 0.55] } : { pathLength: 0.78, opacity: 0.8 }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.circle
          cx="60"
          cy="60"
          r="6"
          fill={accent}
          animate={isBusy ? { scale: [0.85, 1.15, 0.85] } : { scale: 1 }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
        />
      </motion.svg>
    </div>
  );
}

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
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

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
      for (let attempt = 1; attempt <= MAX_UPLOAD_ATTEMPTS; attempt += 1) {
        try {
          res = await fetchWithTimeout(apiUrl('/api/upload'), { method: 'POST', body: formData }, UPLOAD_TIMEOUT_MS);
          const parsed: unknown = await res.json().catch(() => ({}));
          data = isUploadApiResponse(parsed) ? parsed : {};
          break;
        } catch (err) {
          lastError = err instanceof Error ? err : new Error(String(err));
          if (attempt < MAX_UPLOAD_ATTEMPTS) {
            setMessage(`Connecting to backend... retrying upload (${attempt + 1}/${MAX_UPLOAD_ATTEMPTS}).`);
            await new Promise((resolve) => setTimeout(resolve, attempt * 1200));
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
    <div className="min-h-screen flex flex-col bg-transparent relative">
      {isMounted && <WebGLShader />}
      <AppHeader />

      <main className="flex-grow flex items-center justify-center px-5 sm:px-6 py-10 md:py-16 relative">
        <div className="absolute inset-0 pointer-events-none z-0">
          <div className="absolute inset-0 bg-black/[0.78]" />
          <div className="absolute top-[-14%] left-[10%] w-[420px] h-[420px] bg-cyan-400/[0.04] rounded-full blur-[135px]" />
          <div className="absolute bottom-[-20%] right-[8%] w-[420px] h-[420px] bg-indigo-500/[0.04] rounded-full blur-[145px]" />
        </div>
        <div ref={shellRef} className="w-full max-w-4xl text-center relative z-10">
          <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight text-white/85 mb-2" data-route-item data-submit-item>
            {headline}
          </h1>
          <p className="text-white/35 text-sm md:text-lg mb-8 md:mb-10" data-route-item data-submit-item>{helper}</p>

          <div
            className={`interactive-lift mx-auto w-full max-w-3xl rounded-2xl px-5 sm:px-6 md:px-10 py-9 md:py-12 transition-colors ${
              uploadState === 'uploading'
                ? 'workflow-panel border-[#8efcff]/40 bg-[#0d1f2f]/[0.84]'
                : 'workflow-panel'
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
              <div className="relative mb-4">
                <UploadVector phase={uploadPhase} intent={intent} />
                <div className="material-symbols-outlined absolute inset-0 flex items-center justify-center text-[34px] text-white/72">
                  description
                </div>
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
                  <div className="mt-4 rounded-md border border-white/10 bg-black/35 px-3 py-2">
                    <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.15em] text-white/45 mb-2">
                      <span>Vector pipeline</span>
                      <span>{uploadPhase.toUpperCase()}</span>
                    </div>
                    <div className="relative h-8 overflow-hidden">
                      <motion.div
                        className="absolute inset-y-0 left-0 w-10 rounded-full bg-[#8efcff]/35 blur-md"
                        animate={{ x: ['-20%', '260%'] }}
                        transition={{ duration: 1.25, ease: 'easeInOut', repeat: Infinity }}
                      />
                      <svg viewBox="0 0 320 28" className="relative h-full w-full" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M6 20L60 20L93 8L143 8L182 20L220 20L258 11L314 11" stroke="#8efcff" strokeOpacity="0.75" strokeWidth="2.2" strokeLinecap="round" />
                      </svg>
                    </div>
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
                className="focus-glow cta-premium rounded-full border border-white/[0.24] bg-white/[0.08] px-8 py-2.5 text-sm font-medium text-white/[0.78] hover:bg-white/[0.14] disabled:opacity-50"
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
                  ? 'border border-[#6efcff]/45 bg-[#6efcff]/[0.13] text-[#d1feff] shadow-[0_0_20px_rgba(110,252,255,0.18)] hover:bg-[#6efcff]/20'
                  : 'border border-white/[0.24] bg-white/[0.08] text-white/80 hover:bg-white/[0.14]'
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
