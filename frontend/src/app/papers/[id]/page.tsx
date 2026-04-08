'use client';

import { Shield, ArrowLeft, ExternalLink } from 'lucide-react';
import Link from 'next/link';

const DIMENSION_NAMES: Record<number, string> = {
  1: 'Return on Research Investment (RORI)',
  2: 'Scientific Quality & Rigor',
  3: 'Market Size & Scalability',
  4: 'Competitive Moat & IP Defensibility',
  5: 'Team Quality & Track Record',
  6: 'Societal Impact & ESG Alignment',
  7: 'Research Pipeline & Portfolio Risk',
  8: 'Risk & Uncertainty Profile',
  9: 'Governance & Transparency',
};

interface PageProps {
  params: { id: string };
}

export default function PaperDetailPage({ params }: PageProps) {
  const doi = decodeURIComponent(params.id);

  // Placeholder — will be populated from API
  const mockResult = {
    doi,
    total_score: 0,
    grade: '—',
    integrity_gate_triggered: false,
    dimensions: [] as { dimension_id: number; raw_score: number; origin_snippet?: string }[],
  };

  const gradeClass = `grade-${mockResult.grade}`;

  return (
    <main className="min-h-screen px-6 py-12 max-w-5xl mx-auto">
      {/* Back nav */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-slate-400 hover:text-indigo-400 mb-8 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </Link>

      {/* Paper header */}
      <div className="glass-card p-8 mb-8 animate-fade-up">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-mono text-slate-500 mb-2">DOI</p>
            <h1 className="text-2xl font-bold mb-2">{doi}</h1>
            <a
              href={`https://doi.org/${doi}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-sm"
            >
              View on publisher site <ExternalLink className="w-3 h-3" />
            </a>
          </div>
          <div className="text-center">
            <div className={`grade-badge ${gradeClass} text-3xl w-16 h-16`}>
              {mockResult.grade}
            </div>
            <p className="text-xs text-slate-500 mt-2">
              {mockResult.total_score.toFixed(1)}/100
            </p>
          </div>
        </div>
      </div>

      {/* Integrity Gate Status */}
      <div className={`integrity-indicator mb-8 animate-fade-up animate-delay-1 ${
        mockResult.integrity_gate_triggered ? 'integrity-fail' : 'integrity-pass'
      }`}>
        <Shield className="w-5 h-5" />
        {mockResult.integrity_gate_triggered
          ? 'INTEGRITY GATE TRIGGERED — Total score forced to 0. Retraction or ethical breach detected.'
          : 'Integrity Gate: PASSED — No retractions or ethical breaches detected.'}
      </div>

      {/* 9-Dimension Breakdown */}
      <section className="glass-card p-8 animate-fade-up animate-delay-2">
        <h2 className="text-xl font-semibold mb-6">Dimension Breakdown</h2>
        <div className="space-y-4">
          {Array.from({ length: 9 }, (_, i) => i + 1).map((dimId) => {
            const dim = mockResult.dimensions.find(d => d.dimension_id === dimId);
            const score = dim?.raw_score ?? 0;
            const pct = (score / 5) * 100;
            const isGov = dimId === 9;

            return (
              <div
                key={dimId}
                className={`p-4 rounded-xl border ${
                  isGov ? 'border-red-500/20 bg-red-500/5' : 'border-slate-700/30 bg-slate-800/20'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-slate-500 w-6">D{dimId}</span>
                    <span className="text-sm font-medium text-slate-300">
                      {DIMENSION_NAMES[dimId]}
                    </span>
                    {isGov && (
                      <span className="text-[10px] font-bold uppercase tracking-wider text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">
                        Gate
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-semibold tabular-nums">
                    {score > 0 ? score.toFixed(1) : '—'}/5
                  </span>
                </div>
                <div className="score-bar">
                  <div
                    className={`score-bar-fill ${isGov ? 'bg-red-500' : 'bg-indigo-500'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                {dim?.origin_snippet && (
                  <details className="mt-2">
                    <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-400">
                      View origin snippet
                    </summary>
                    <pre className="mt-1 text-xs text-slate-600 bg-slate-900 p-2 rounded overflow-x-auto">
                      {dim.origin_snippet}
                    </pre>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
