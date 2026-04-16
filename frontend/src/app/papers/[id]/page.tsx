'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import AppHeader from '@/components/AppHeader';
import AppFooter from '@/components/AppFooter';

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

export default function PaperResultsPage() {
  const { id } = useParams<{ id: string }>();
  const paperId = String(id);
  const [data, setData] = useState<ScoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const start = Date.now();

    const fetchOnce = async () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const res = await fetch(`${apiUrl}/api/scoring/results/${encodeURIComponent(paperId)}`);
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
          setData(json);
          setLoading(false);
          return;
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
        return;
      }

      if (Date.now() - start > 120_000) {
        setError('Still processing. Please refresh in a minute.');
        setLoading(false);
        return;
      }

      setLoading(true);
      setTimeout(poll, 2000);
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

      <main className="flex-grow lg:ml-0 p-6 md:p-8 pt-6 max-w-7xl mx-auto w-full">
        {loading ? (
          <section className="min-h-[70vh] flex items-center justify-center px-6">
            <div className="w-full max-w-3xl text-center">
              <h1 className="font-headline text-4xl md:text-5xl font-extrabold text-white/80 tracking-tight mb-10">
                Analyzing your research
              </h1>

              <div className="w-full max-w-3xl mx-auto h-5 rounded-full border border-white/15 bg-white/5 overflow-hidden">
                <div
                  className="h-full bg-white rounded-full transition-all duration-1000"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              <div className="mt-10">
                <button
                  className="rounded-full border border-white/20 bg-white/5 px-10 py-3 text-sm font-semibold text-white/60 cursor-not-allowed"
                  disabled
                >
                  See the result
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
          <section
            className="rounded-2xl overflow-hidden border border-white/10"
            style={{
              backgroundImage: 'url(/figma/results-bg.png)',
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }}
          >
            <div className="bg-black/70 backdrop-blur-sm px-6 md:px-10 py-10">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div className="lg:col-span-5 space-y-6">
                  <div className="border border-white/10 bg-black/30 rounded-xl p-6">
                    <div className="text-white/60 text-sm mb-1">Score:</div>
                    <div className="text-white/90 font-headline font-extrabold text-5xl">
                      {score} <span className="text-white/40 text-2xl">/ 100</span>
                    </div>
                    <div className="text-white/45 text-sm mt-3">
                      Confidence: {data.confidence_tier || 'automated analysis'}
                    </div>
                  </div>

                  <div className="border border-white/10 bg-black/30 rounded-xl p-6">
                    <div className="text-white/60 text-sm mb-3">Insight:</div>
                    <div className="text-white/50 text-sm leading-relaxed">
                      {data.insight ||
                        (data.integrity_gate_triggered
                          ? 'Governance integrity gate triggered. Total score forced to 0.'
                          : 'Automated analysis complete. Open dimension details for evidence.')}
                    </div>
                  </div>

                  <div className="border border-white/10 bg-black/30 rounded-xl p-6">
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

                  <div className="border border-white/10 bg-black/30 rounded-xl p-6">
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
                  <div className="border border-white/10 bg-black/25 rounded-xl p-6">
                    <div className="space-y-5">
                      {dims.map((d) => (
                        <div key={d.dimension_id} className="grid grid-cols-12 gap-3 items-center">
                          <div className="col-span-5 text-white/55 text-sm">
                            {d.dimension_name}
                          </div>
                          <div className="col-span-6 h-2 rounded-full bg-white/10 overflow-hidden">
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

                    <div className="mt-10 flex items-center justify-between gap-6">
                      <div className="text-white/35 text-sm">
                        We need more information to improve accuracy
                      </div>
                      <Link
                        href="/upsell"
                        className="inline-flex items-center gap-2 rounded-xl border border-[#6efcff]/30 bg-[#6efcff]/10 px-5 py-3 text-sm font-semibold text-white/80 hover:bg-[#6efcff]/15 transition-colors"
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
