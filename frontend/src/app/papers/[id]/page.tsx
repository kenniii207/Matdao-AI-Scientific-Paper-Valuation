'use client';

import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import anime from 'animejs';
import AppHeader from '@/components/AppHeader';
import { MetricCard } from '@/components/MetricCard';
import AppFooter from '@/components/AppFooter';
import { apiUrl, fetchWithTimeout } from '@/lib/api';
import type { ScoringPendingResponse, ScoringResponse } from '@/lib/types/scoring';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';
import { AnimatedRouteLink } from '@/components/AnimatedRouteLink';
import { WebGLShader } from '@/components/ui/web-gl-shader';

const RESULTS_TIMEOUT_MS = 30_000;
const MAX_TOTAL_POLL_MS = 8 * 60 * 1000;
const MAX_CONSECUTIVE_FAILURES = 14;

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function formatDuration(totalSeconds: number) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  if (minutes > 0) return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
  return `${seconds}s`;
}

export default function PaperResultsPage() {
  const { id } = useParams<{ id: string }>();
  const paperId = String(id);
  const reducedMotion = usePrefersReducedMotion();
  const [data, setData] = useState<ScoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [loadingStatus, setLoadingStatus] = useState('Connecting to backend...');
  const progressFillRef = useRef<HTMLDivElement | null>(null);
  const loadingStageRefs = useRef<Array<HTMLDivElement | null>>([]);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const start = Date.now();
    let consecutiveFailures = 0;

    const fetchOnce = async () => {
      const res = await fetchWithTimeout(
        apiUrl(`/api/scoring/results/${encodeURIComponent(paperId)}`),
        {},
        RESULTS_TIMEOUT_MS,
      );
      if (res.status === 404 || res.status === 202) return null;
      if (!res.ok) throw new Error('Backend error while retrieving result.');

      const json = (await res.json()) as Partial<ScoringResponse> & Partial<ScoringPendingResponse>;
      if (json && typeof json === 'object' && 'status' in json && json.status === 'error') {
        throw new Error(json.error || 'Audit failed.');
      }
      if (!json || typeof json.total_score !== 'number' || !Array.isArray(json.dimensions)) return null;
      return json as ScoringResponse;
    };

    const poll = async () => {
      try {
        const json = await fetchOnce();
        if (cancelled) return;
        if (json) {
          consecutiveFailures = 0;
          setLoadingStatus('Finalizing scorecard...');
          setData(json);
          setLoading(false);
          return;
        }
        setLoadingStatus('Running extraction, enrichment, and scoring pipeline...');
        consecutiveFailures = 0;
      } catch {
        if (cancelled) return;
        consecutiveFailures += 1;
        setLoadingStatus(
          consecutiveFailures >= 2
            ? 'Reconnecting to backend...'
            : 'Waiting for scoring service...',
        );
      }

      if (Date.now() - start > MAX_TOTAL_POLL_MS) {
        setError('Still processing after 8 minutes. Please refresh in a minute.');
        setLoading(false);
        return;
      }
      if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
        setError('Temporary network issue while fetching results. Please retry.');
        setLoading(false);
        return;
      }

      setLoading(true);
      setTimeout(poll, Math.min(6000, 1600 + consecutiveFailures * 420));
    };

    poll();
    return () => {
      cancelled = true;
    };
  }, [paperId]);

  useEffect(() => {
    if (!loading) return;
    setElapsedMs(0);
    const start = Date.now();
    const interval = setInterval(() => setElapsedMs(Date.now() - start), 1000);
    return () => clearInterval(interval);
  }, [loading]);

  const score = useMemo(() => (data ? clamp(Math.round(data.total_score), 0, 100) : 0), [data]);

  const progressPercent = useMemo(() => {
    if (!loading) return 100;
    return clamp(Math.round(15 + (elapsedMs / 120000) * 70), 15, 85);
  }, [elapsedMs, loading]);
  const elapsedSeconds = useMemo(() => Math.floor(elapsedMs / 1000), [elapsedMs]);
  const etaSeconds = useMemo(() => {
    if (!loading) return 0;
    const expectedDuration = 75;
    const byExpectation = expectedDuration - elapsedSeconds;
    const byProgress = Math.round((100 - progressPercent) * 1.15);
    return clamp(Math.max(byExpectation, byProgress), 5, 120 - elapsedSeconds);
  }, [elapsedSeconds, progressPercent, loading]);
  const stageIndex = useMemo(() => {
    if (progressPercent < 38) return 0;
    if (progressPercent < 67) return 1;
    return 2;
  }, [progressPercent]);

  useEffect(() => {
    if (!loading || !progressFillRef.current) return;
    if (reducedMotion) {
      progressFillRef.current.style.transform = `scaleX(${progressPercent / 100})`;
      return;
    }
    anime.remove(progressFillRef.current);
    anime({
      targets: progressFillRef.current,
      scaleX: progressPercent / 100,
      duration: 820,
      easing: 'easeOutCubic',
    });
  }, [progressPercent, loading, reducedMotion]);

  useEffect(() => {
    if (!loading || reducedMotion) return;
    const node = loadingStageRefs.current[stageIndex];
    if (!node) return;
    anime.remove(node);
    anime({
      targets: node,
      scale: [0.96, 1.03, 1],
      duration: 360,
      easing: 'easeOutCubic',
    });
  }, [stageIndex, loading, reducedMotion]);

  const dims = useMemo(() => {
    const arr = data?.dimensions || [];
    return arr
      .slice()
      .sort((a, b) => a.dimension_id - b.dimension_id)
      .map((d) => ({
        ...d,
        percent: clamp(Math.round((d.raw_score / 5) * 100), 0, 100),
      }));
  }, [data]);

  return (
    <div className="min-h-screen flex flex-col bg-transparent relative">
      {isMounted && <WebGLShader />}
      <AppHeader />

      <main className="flex-grow lg:ml-0 p-4 sm:p-6 md:p-8 pt-5 md:pt-6 max-w-7xl mx-auto w-full relative">
        <div className="absolute inset-0 pointer-events-none -z-10">
          <div className="absolute inset-0 bg-black/[0.78]" />
          <div className="absolute top-[-10%] left-[4%] w-[360px] h-[360px] bg-cyan-400/[0.04] rounded-full blur-[130px]" />
          <div className="absolute bottom-[-18%] right-[2%] w-[360px] h-[360px] bg-purple-500/[0.04] rounded-full blur-[130px]" />
        </div>
        <AnimatePresence mode="wait" initial={false}>
          {loading ? (
          <motion.section
            key="loading"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: reducedMotion ? 0 : 0.28, ease: 'easeOut' }}
            className="min-h-[70vh] flex items-center justify-center px-3 sm:px-6"
            data-route-item
          >
            <div className="workflow-panel w-full max-w-3xl text-center rounded-2xl px-6 sm:px-8 py-9" data-route-item>
              <div className="mx-auto mb-5 relative h-20 w-20">
                <motion.div
                  className="absolute inset-0 rounded-full bg-[#7ef9ff]/20 blur-xl"
                  animate={{ scale: [0.88, 1.08, 0.88], opacity: [0.35, 0.75, 0.35] }}
                  transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
                />
                <motion.svg
                  viewBox="0 0 96 96"
                  className="relative h-full w-full"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <motion.circle
                    cx="48"
                    cy="48"
                    r="28"
                    stroke="#8efcff"
                    strokeWidth="3"
                    strokeOpacity="0.86"
                    strokeDasharray="8 8"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 9, repeat: Infinity, ease: 'linear' }}
                    style={{ transformOrigin: '50% 50%' }}
                  />
                  <motion.path
                    d="M22 54L38 40L49 48L63 34L75 40"
                    stroke="#c9fdff"
                    strokeWidth="3.4"
                    strokeLinecap="round"
                    animate={{ pathLength: [0.4, 1, 0.4], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.7, repeat: Infinity, ease: 'easeInOut' }}
                  />
                  <motion.circle
                    cx="49"
                    cy="48"
                    r="4.8"
                    fill="#8efcff"
                    animate={{ scale: [0.85, 1.18, 0.85] }}
                    transition={{ duration: 1.15, repeat: Infinity, ease: 'easeInOut' }}
                  />
                </motion.svg>
              </div>
              <h1 className="font-headline text-4xl md:text-5xl font-extrabold text-white/80 tracking-tight mb-3">
                Analyzing your research
              </h1>
              <p className="text-white/45 text-sm md:text-base mb-8">
                {loadingStatus}
              </p>

              <div className="progress-shimmer w-full max-w-3xl mx-auto h-5 rounded-full border border-white/[0.2] bg-white/[0.08] overflow-hidden">
                <div
                  ref={progressFillRef}
                  className="h-full rounded-full transition-all duration-1000 bg-gradient-to-r from-[#57f3ff] via-[#9ff9ff] to-white shadow-[0_0_20px_rgba(87,243,255,0.45)]"
                  style={{
                    transform: `scaleX(${progressPercent / 100})`,
                    transformOrigin: '0% 50%',
                  }}
                />
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-white/45 max-w-3xl mx-auto">
                <span>{progressPercent}% complete</span>
                <span>Elapsed {formatDuration(elapsedSeconds)}</span>
              </div>
              <div className="mt-2 text-sm text-[#aef9ff]">
                Estimated time remaining: {formatDuration(etaSeconds)}
              </div>

              <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-2.5 md:gap-3 max-w-3xl mx-auto">
                {['Extracting document', 'Matching related work', 'Scoring dimensions'].map((stage, index) => {
                  const isActive = index === stageIndex;
                  const isDone = index < stageIndex;
                  return (
                    <div
                      key={stage}
                      ref={(node) => {
                        loadingStageRefs.current[index] = node;
                      }}
                      className={`rounded-xl border px-4 py-3 text-sm transition-colors ${
                        isDone
                          ? 'border-[#6efcff]/40 bg-[#6efcff]/10 text-[#b8feff]'
                          : isActive
                            ? 'border-white/[0.3] bg-white/[0.12] text-white/80'
                            : 'border-white/[0.12] bg-white/[0.06] text-white/40'
                      }`}
                    >
                      {stage}
                    </div>
                  );
                })}
              </div>

              <div className="mt-10">
                <button
                  className="rounded-full border border-white/[0.24] bg-white/[0.08] px-8 sm:px-10 py-3 text-sm font-semibold text-white/60 cursor-not-allowed"
                  disabled
                >
                  Preparing your result
                </button>
              </div>
            </div>
          </motion.section>
        ) : error ? (
          <motion.section
            key="error"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: reducedMotion ? 0 : 0.24, ease: 'easeOut' }}
            className="min-h-[60vh] flex items-center justify-center p-6"
            data-route-item
          >
            <div className="workflow-panel rounded-xl p-10 max-w-lg text-center">
              <div className="text-error mb-4 text-4xl">⚠️</div>
              <h2 className="font-headline text-xl font-extrabold mb-2">Audit failed</h2>
              <p className="text-white/65 text-sm mb-6">{error}</p>
              <div className="flex gap-3 justify-center">
                <Link
                  href="/submit"
                  className="px-6 py-3 bg-primary-fixed text-on-primary-fixed font-bold rounded-md"
                >
                  Back to upload
                </Link>
                <button
                  type="button"
                  className="px-6 py-3 border border-white/[0.2] rounded-md text-white/70 hover:bg-white/[0.08]"
                  onClick={() => window.location.reload()}
                >
                  Retry
                </button>
              </div>
            </div>
          </motion.section>
        ) : data ? (
          <motion.section
            key="results"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reducedMotion ? 0 : 0.3, ease: 'easeOut' }}
            className="rounded-2xl overflow-hidden border border-white/[0.16] bg-[#0b1120]/[0.92] shadow-[0_24px_46px_rgba(0,0,0,0.4)]"
            data-route-item
          >
            <div className="bg-black/[0.52] backdrop-blur-sm px-6 md:px-10 py-10">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div className="lg:col-span-5 space-y-6">
                  <div className="interactive-lift workflow-panel-muted rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-1">Score:</div>
                    <div className="text-white/90 font-headline font-extrabold text-5xl">
                      {score} <span className="text-white/40 text-2xl">/ 100</span>
                    </div>
                    <div className="text-white/45 text-sm mt-3">
                      Confidence: {data.confidence_tier || 'automated analysis'}
                    </div>
                  </div>

                  <div className="interactive-lift workflow-panel-muted rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-3">Executive Summary:</div>
                    <div className="text-white/50 text-sm leading-relaxed">
                      {data.executive_summary || 'Summary not available for this run.'}
                    </div>
                  </div>

                  <div className="interactive-lift workflow-panel-muted rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-3">Investment Recommendation:</div>
                    <div className="inline-flex items-center rounded-full border border-[#6efcff]/40 bg-[#6efcff]/10 px-3 py-1 text-xs font-semibold text-[#b3feff]">
                      {data.investment_recommendation || data.grade || 'Pending'}
                    </div>
                  </div>

                  <div className="interactive-lift workflow-panel-muted rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-3">Insight:</div>
                    <div className="text-white/50 text-sm leading-relaxed">
                      {data.insight ||
                        (data.integrity_gate_triggered
                          ? 'Governance integrity gate triggered. Total score forced to 0.'
                          : 'Automated analysis complete. Open dimension details for evidence.')}
                    </div>
                  </div>

                  <div className="interactive-lift workflow-panel-muted rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-3">Investor Fit:</div>
                    <ul className="space-y-2 text-white/60 text-sm">
                      {(data.investor_fit?.length
                        ? data.investor_fit
                        : ['Early-stage deep tech investors', 'Corporate R&D collaboration']
                      ).map((t) => (
                        <li key={t} className="flex items-center gap-2">
                          <span className="text-[#6efcff]">✓</span>
                          {t}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="interactive-lift workflow-panel-muted rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-3">Warnings:</div>
                    <ul className="space-y-2 text-white/60 text-sm">
                      {((data.warnings?.length
                        ? data.warnings
                        : data.integrity_gate_triggered
                          ? ['Governance risk flagged (Dim 9)', 'Score forced to 0']
                          : ['Insufficient risk detail from current extraction', 'Validate external market signals with Layer 3 review'])
                      ).map((t) => (
                        <li key={t} className="flex items-center gap-2">
                          <span className="text-yellow-300">⚠</span>
                          {t}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="lg:col-span-7">
                  <div className="interactive-lift workflow-panel-muted rounded-xl p-5 md:p-6">
                    <motion.div 
                      className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
                      initial="hidden"
                      animate="show"
                      variants={{
                        hidden: { opacity: 0 },
                        show: {
                          opacity: 1,
                          transition: { staggerChildren: 0.1 }
                        }
                      }}
                    >
                      {dims.map((d) => (
                        <motion.div
                          key={d.dimension_id}
                          variants={{
                            hidden: { opacity: 0, y: 30, scale: 0.95 },
                            show: { opacity: 1, y: 0, scale: 1, transition: { type: 'spring', stiffness: 200, damping: 20 } }
                          }}
                        >
                          <MetricCard 
                            id={d.dimension_id}
                            name={d.dimension_name}
                            percent={d.percent}
                            rawScore={d.raw_score}
                            rationale={d.rationale}
                            snippet={d.origin_snippet}
                          />
                        </motion.div>
                      ))}
                    </motion.div>

                    <div className="mt-8 md:mt-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 sm:gap-6">
                      <div className="text-white/35 text-sm">
                        We need more information to improve accuracy
                      </div>
                      <AnimatedRouteLink
                        href="/upsell"
                        className="focus-glow cta-premium inline-flex items-center justify-center gap-2 rounded-xl border border-[#6efcff]/30 bg-[#6efcff]/10 px-5 py-3 text-sm font-semibold text-white/80 hover:bg-[#6efcff]/15"
                      >
                        Improve Accuracy <span aria-hidden>→</span>
                      </AnimatedRouteLink>
                    </div>
                  </div>

                  <div className="mt-6 text-white/30 text-xs">
                    Paper: {data.paper_title || 'Untitled'} • DOI: {data.doi || paperId}
                  </div>
                </div>
              </div>
            </div>
          </motion.section>
        ) : null}
        </AnimatePresence>
      </main>

      <AppFooter />
    </div>
  );
}
