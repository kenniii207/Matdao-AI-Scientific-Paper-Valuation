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
  dimensions: Dimension[];
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

  useEffect(() => {
    let cancelled = false;
    const start = Date.now();

    const fetchOnce = async () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const res = await fetch(`${apiUrl}/api/scoring/results/${encodeURIComponent(paperId)}`);
      if (res.status === 404) return null;
      if (!res.ok) throw new Error('Backend error while retrieving result.');
      return (await res.json()) as ScoringResponse;
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

  const score = useMemo(() => (data ? clamp(Math.round(data.total_score), 0, 100) : 0), [data]);

  const progressPercent = useMemo(() => {
    if (!loading) return 100;
    // Fake progress curve for UX; real compute happens on backend.
    const t = Date.now() % 120000;
    return clamp(Math.round(15 + (t / 120000) * 70), 15, 85);
  }, [loading]);

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
          <section className="min-h-[70vh] flex items-center justify-center px-6 relative overflow-hidden">
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              <div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full opacity-10 blur-[120px]"
                style={{ background: 'radial-gradient(circle, #00dce5 0%, transparent 70%)' }}
              />
            </div>

            <div className="w-full max-w-2xl text-center z-10">
              <div className="mb-12">
                <span className="font-headline text-xs uppercase tracking-[0.3em] text-primary-fixed opacity-60 mb-4 block">
                  System status: Active
                </span>
                <h1 className="font-headline text-4xl md:text-5xl font-extrabold text-on-surface tracking-tighter mb-4">
                  Analyzing your research
                </h1>
                <p className="font-body text-on-surface-variant text-lg max-w-md mx-auto leading-relaxed">
                  Extracting text, enriching metadata, and generating 9-dimension scorecard.
                </p>
              </div>

              <div className="w-full bg-surface-container-highest h-6 rounded-full overflow-hidden mb-12 relative">
                <div
                  className="absolute left-0 top-0 h-full bg-white rounded-full transition-all duration-1000 ease-in-out shadow-[0_0_25px_rgba(255,255,255,0.35)]"
                  style={{ width: `${progressPercent}%` }}
                >
                  <div className="w-full h-full opacity-50 bg-gradient-to-r from-transparent via-primary-fixed/30 to-transparent" />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-6 mb-14">
                <div className="text-left">
                  <p className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant mb-1">
                    Status
                  </p>
                  <p className="font-headline text-sm font-bold text-on-surface">Synthesizing</p>
                </div>
                <div className="text-center">
                  <p className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant mb-1">
                    Completion
                  </p>
                  <p className="font-headline text-sm font-bold text-primary-fixed">
                    {progressPercent}%
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant mb-1">
                    Paper ID
                  </p>
                  <p className="font-headline text-sm font-bold text-on-surface">
                    {paperId.slice(0, 8)}
                  </p>
                </div>
              </div>

              <div className="flex flex-col items-center gap-5">
                <button
                  className="px-10 py-4 bg-primary-container text-on-primary-fixed font-headline font-bold rounded-full opacity-50 cursor-not-allowed"
                  disabled
                >
                  See the result
                </button>
                <div className="flex items-center gap-2 text-on-surface-variant opacity-40">
                  <span className="material-symbols-outlined text-sm animate-pulse">sync</span>
                  <span className="text-xs font-medium uppercase tracking-tighter font-body">
                    Generating final report...
                  </span>
                </div>
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
          <>
            <aside className="h-full w-64 fixed left-0 top-0 pt-24 bg-surface-container-lowest hidden lg:block">
              <div className="flex flex-col gap-4 p-6">
                <div className="mb-6 px-4">
                  <p className="text-primary-fixed text-xs font-headline uppercase tracking-widest mb-1">
                    Project
                  </p>
                  <p className="text-on-surface-variant text-[10px] uppercase tracking-[0.2em]">
                    {data.doi || paperId}
                  </p>
                </div>
                <nav className="space-y-2">
                  {[
                    { label: 'Overview', icon: 'dashboard' },
                    { label: 'Analysis', icon: 'analytics', active: true },
                    { label: 'Review', icon: 'rate_review', href: `/review/${paperId}` },
                  ].map((item) => (
                    <Link
                      key={item.label}
                      href={item.href || '#'}
                      className={[
                        'flex items-center gap-3 p-3 rounded-sm ease-in-out duration-200',
                        item.active
                          ? 'bg-surface-container text-primary-fixed border-r-4 border-primary-fixed'
                          : 'text-on-surface-variant/60 hover:bg-surface-container/50',
                      ].join(' ')}
                    >
                      <span className="material-symbols-outlined">{item.icon}</span>
                      <span className="text-xs font-headline uppercase tracking-widest">
                        {item.label}
                      </span>
                    </Link>
                  ))}
                </nav>
                <Link
                  href="/upsell"
                  className="mt-8 mx-4 bg-primary-container text-on-primary-fixed py-3 rounded-sm text-[10px] font-bold uppercase tracking-widest hover:brightness-110 transition-all text-center"
                >
                  Improve Accuracy
                </Link>
              </div>
            </aside>

            <div className="lg:ml-64">
              <header className="mb-12">
                <h1 className="text-4xl font-extrabold font-headline tracking-tight text-on-surface mb-2">
                  Results Summary
                </h1>
                <p className="text-on-surface-variant font-body">
                  Paper: {data.paper_title || 'Untitled'} • Grade {data.grade}
                </p>
              </header>

              <div className="grid grid-cols-1 xl:grid-cols-12 gap-10 items-start">
                <div className="xl:col-span-5 space-y-8">
                  <section className="bg-surface-container rounded-xl p-8 border border-outline-variant/15 relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-4 opacity-10">
                      <span className="material-symbols-outlined text-6xl">verified</span>
                    </div>
                    <div className="flex justify-between items-end mb-6">
                      <div>
                        <p className="text-primary-fixed text-xs font-headline uppercase tracking-[0.2em] mb-2">
                          Project Score
                        </p>
                        <h2 className="text-7xl font-extrabold font-headline tracking-tighter text-on-surface">
                          {score}{' '}
                          <span className="text-2xl text-on-surface-variant font-medium">/ 100</span>
                        </h2>
                      </div>
                      <div className="text-right">
                        <p className="text-on-surface-variant text-[10px] font-headline uppercase tracking-widest mb-1">
                          Confidence
                        </p>
                        <p className="text-primary-fixed text-2xl font-bold font-headline">
                          {data.confidence_tier || 'AUTOMATED'}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-4 pt-6 border-t border-outline-variant/10">
                      <p className="text-on-surface-variant text-sm leading-relaxed">
                        {data.integrity_gate_triggered
                          ? 'Integrity gate triggered. Total score forced to 0 for governance risk.'
                          : 'Evaluation completed. Review dimension breakdown and evidence snippets.'}
                      </p>
                    </div>
                  </section>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <section className="bg-surface-container rounded-xl p-6 border border-outline-variant/15">
                      <div className="flex items-center gap-2 mb-4">
                        <span className="material-symbols-outlined text-primary-fixed">groups</span>
                        <h3 className="text-xs font-headline uppercase tracking-widest text-primary-fixed">
                          Investor Fit
                        </h3>
                      </div>
                      <ul className="space-y-3">
                        {['Early-stage deep tech', 'Corporate R&D'].map((t) => (
                          <li key={t} className="flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary-fixed" />
                            <span className="text-xs text-on-surface">{t}</span>
                          </li>
                        ))}
                      </ul>
                    </section>

                    <section className="bg-surface-container rounded-xl p-6 border border-outline-variant/15">
                      <div className="flex items-center gap-2 mb-4">
                        <span
                          className={[
                            'material-symbols-outlined',
                            data.integrity_gate_triggered ? 'text-error' : 'text-primary-fixed',
                          ].join(' ')}
                        >
                          warning
                        </span>
                        <h3
                          className={[
                            'text-xs font-headline uppercase tracking-widest',
                            data.integrity_gate_triggered ? 'text-error' : 'text-primary-fixed',
                          ].join(' ')}
                        >
                          Warnings
                        </h3>
                      </div>
                      <ul className="space-y-3">
                        {(data.integrity_gate_triggered
                          ? ['Governance risk flagged (Dim 9)', 'Score forced to 0']
                          : ['No critical governance flags detected']
                        ).map((t) => (
                          <li key={t} className="flex items-center gap-2">
                            <span
                              className={[
                                'w-1.5 h-1.5 rounded-full',
                                data.integrity_gate_triggered ? 'bg-error' : 'bg-primary-fixed',
                              ].join(' ')}
                            />
                            <span className="text-xs text-on-surface">{t}</span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  </div>
                </div>

                <div className="xl:col-span-7">
                  <section className="bg-surface-container rounded-xl p-8 border border-outline-variant/15">
                    <div className="flex justify-between items-center mb-10">
                      <h3 className="text-xs font-headline uppercase tracking-[0.2em] text-on-surface-variant">
                        9-Dimension Breakdown
                      </h3>
                      <span className="material-symbols-outlined text-on-surface-variant">hub</span>
                    </div>

                    <div className="space-y-8">
                      {dims.map((d) => (
                        <div key={d.dimension_id} className="group">
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-xs font-headline tracking-wide text-on-surface group-hover:text-primary-fixed transition-colors">
                              {d.dimension_id}. {d.dimension_name}
                            </span>
                            <span className="text-xs font-bold text-primary-fixed">{d.percent}</span>
                          </div>
                          <div className="h-1 w-full bg-surface-container-highest rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-primary-fixed-dim to-primary-fixed shadow-[0_0_8px_rgba(99,247,255,0.35)]"
                              style={{ width: `${d.percent}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>

                  <footer className="mt-14 flex justify-center pb-10">
                    <Link
                      href="/upsell"
                      className="flex items-center gap-3 bg-transparent border border-primary-fixed text-primary-fixed px-12 py-4 rounded-full font-headline font-bold uppercase tracking-widest hover:bg-primary-fixed/5 transition-all duration-300 active:scale-95"
                    >
                      Improve Accuracy
                      <span className="material-symbols-outlined">trending_up</span>
                    </Link>
                  </footer>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </main>

      <AppFooter />
    </div>
  );
}
