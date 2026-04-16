'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import AppHeader from '@/components/AppHeader';
import AppFooter from '@/components/AppFooter';
import { apiUrl, fetchWithTimeout } from '@/lib/api';

type Dimension = {
  dimension_id: number;
  dimension_name: string;
  raw_score: number; // 1..5
  rationale?: string;
  origin_snippet?: string;
};

type ScoringResponse = {
  paper_id: string;
  paper_title?: string;
  doi?: string;
  total_score: number;
  grade: string;
  integrity_gate_triggered: boolean;
  confidence_tier?: string;
  insight?: string;
  investor_fit?: string[];
  warnings?: string[];
  executive_summary?: string;
  investment_recommendation?: string;
  dimensions: Dimension[];
};

type ScoringPendingResponse = {
  paper_id: string;
  doi?: string;
  status: string;
  error?: string;
};

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
  const [data, setData] = useState<ScoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [loadingStatus, setLoadingStatus] = useState('Connecting to backend...');

  useEffect(() => {
    let cancelled = false;
    const start = Date.now();
    let consecutiveFailures = 0;

    const fetchOnce = async () => {
      const res = await fetchWithTimeout(
        apiUrl(`/api/scoring/results/${encodeURIComponent(paperId)}`),
        {},
        15000,
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
      } catch (e) {
        if (cancelled) return;
        consecutiveFailures += 1;
        setLoadingStatus(
          consecutiveFailures >= 2
            ? 'Reconnecting to backend...'
            : 'Waiting for scoring service...',
        );
      }

      if (Date.now() - start > 180_000) {
        setError('Still processing after 3 minutes. Please refresh in a minute.');
        setLoading(false);
        return;
      }
      if (consecutiveFailures >= 8) {
        setError('Temporary network issue while fetching results. Please retry.');
        setLoading(false);
        return;
      }

      setLoading(true);
      setTimeout(poll, Math.min(3500, 1400 + consecutiveFailures * 350));
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
    // UX progress curve; real compute happens on backend.
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
    <div className="min-h-screen flex flex-col">
      <AppHeader />

      <main className="flex-grow lg:ml-0 p-4 sm:p-6 md:p-8 pt-5 md:pt-6 max-w-7xl mx-auto w-full">
        {loading ? (
          <section className="min-h-[70vh] flex items-center justify-center px-3 sm:px-6">
            <div className="w-full max-w-3xl text-center">
              <h1 className="font-headline text-4xl md:text-5xl font-extrabold text-white/80 tracking-tight mb-3">
                Analyzing your research
              </h1>
              <p className="text-white/45 text-sm md:text-base mb-8">
                {loadingStatus}
              </p>

              <div className="progress-shimmer w-full max-w-3xl mx-auto h-5 rounded-full border border-white/15 bg-white/5 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000 bg-gradient-to-r from-[#57f3ff] via-[#9ff9ff] to-white shadow-[0_0_20px_rgba(87,243,255,0.45)]"
                  style={{ width: `${progressPercent}%` }}
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
                      className={`rounded-xl border px-4 py-3 text-sm transition-colors ${
                        isDone
                          ? 'border-[#6efcff]/40 bg-[#6efcff]/10 text-[#b8feff]'
                          : isActive
                            ? 'border-white/30 bg-white/10 text-white/80'
                            : 'border-white/10 bg-white/5 text-white/40'
                      }`}
                    >
                      {stage}
                    </div>
                  );
                })}
              </div>

              <div className="mt-10">
                <button
                  className="rounded-full border border-white/20 bg-white/5 px-8 sm:px-10 py-3 text-sm font-semibold text-white/60 cursor-not-allowed"
                  disabled
                >
                  Preparing your result
                </button>
              </div>
            </div>
          </section>
        ) : error ? (
          <section className="min-h-[60vh] flex items-center justify-center p-6">
            <div className="bg-surface-container rounded-xl p-10 border border-outline-variant/15 max-w-lg text-center">
              <div className="text-error mb-4 text-4xl">⚠️</div>
              <h2 className="font-headline text-xl font-extrabold mb-2">Audit failed</h2>
              <p className="text-on-surface-variant text-sm mb-6">{error}</p>
              <div className="flex gap-3 justify-center">
                <Link
                  href="/submit"
                  className="px-6 py-3 bg-primary-fixed text-on-primary-fixed font-bold rounded-md"
                >
                  Back to upload
                </Link>
                <button
                  type="button"
                  className="px-6 py-3 border border-outline-variant/20 rounded-md text-on-surface-variant hover:bg-white/5"
                  onClick={() => window.location.reload()}
                >
                  Retry
                </button>
              </div>
            </div>
          </section>
        ) : data ? (
          <section className="rounded-2xl overflow-hidden border border-white/10 bg-[#0b1020]">
            <div className="bg-black/70 backdrop-blur-sm px-6 md:px-10 py-10">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div className="lg:col-span-5 space-y-6">
                  <div className="interactive-lift border border-white/10 bg-black/30 rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-1">Score:</div>
                    <div className="text-white/90 font-headline font-extrabold text-5xl">
                      {score} <span className="text-white/40 text-2xl">/ 100</span>
                    </div>
                    <div className="text-white/45 text-sm mt-3">
                      Confidence: {data.confidence_tier || 'automated analysis'}
                    </div>
                  </div>

                  <div className="interactive-lift border border-white/10 bg-black/30 rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-3">Executive Summary:</div>
                    <div className="text-white/50 text-sm leading-relaxed">
                      {data.executive_summary || 'Summary not available for this run.'}
                    </div>
                  </div>

                  <div className="interactive-lift border border-white/10 bg-black/30 rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-3">Investment Recommendation:</div>
                    <div className="inline-flex items-center rounded-full border border-[#6efcff]/40 bg-[#6efcff]/10 px-3 py-1 text-xs font-semibold text-[#b3feff]">
                      {data.investment_recommendation || data.grade || 'Pending'}
                    </div>
                  </div>

                  <div className="interactive-lift border border-white/10 bg-black/30 rounded-xl p-5 md:p-6">
                    <div className="text-white/60 text-sm mb-3">Insight:</div>
                    <div className="text-white/50 text-sm leading-relaxed">
                      {data.insight ||
                        (data.integrity_gate_triggered
                          ? 'Governance integrity gate triggered. Total score forced to 0.'
                          : 'Automated analysis complete. Open dimension details for evidence.')}
                    </div>
                  </div>

                  <div className="interactive-lift border border-white/10 bg-black/30 rounded-xl p-5 md:p-6">
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

                  <div className="interactive-lift border border-white/10 bg-black/30 rounded-xl p-5 md:p-6">
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
                  <div className="interactive-lift border border-white/10 bg-black/25 rounded-xl p-5 md:p-6">
                    <div className="space-y-5">
                      {dims.map((d) => (
                        <div key={d.dimension_id} className="grid grid-cols-12 gap-3 items-center">
                          <div className="col-span-6 sm:col-span-5 text-white/55 text-sm">
                            {d.dimension_name}
                          </div>
                          <div className="col-span-5 sm:col-span-6 h-2 rounded-full bg-white/10 overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-[#6efcff] to-[#00dce5] shadow-[0_0_10px_rgba(110,252,255,0.35)]"
                              style={{ width: `${d.percent}%` }}
                            />
                          </div>
                          <div className="col-span-1 text-right text-white/55 text-sm tabular-nums">
                            {d.percent}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="mt-8 md:mt-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 sm:gap-6">
                      <div className="text-white/35 text-sm">
                        We need more information to improve accuracy
                      </div>
                      <Link
                        href="/upsell"
                        className="focus-glow cta-premium inline-flex items-center justify-center gap-2 rounded-xl border border-[#6efcff]/30 bg-[#6efcff]/10 px-5 py-3 text-sm font-semibold text-white/80 hover:bg-[#6efcff]/15"
                      >
                        Improve Accuracy <span aria-hidden>→</span>
                      </Link>
                    </div>
                  </div>

                  <div className="mt-6 text-white/30 text-xs">
                    Paper: {data.paper_title || 'Untitled'} • DOI: {data.doi || paperId}
                  </div>
                </div>
              </div>
            </div>
          </section>
        ) : null}
      </main>

      <AppFooter />
    </div>
  );
}
