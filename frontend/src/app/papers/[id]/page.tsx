'use client';

import { useState } from 'react';
import { Shield, ArrowLeft, ExternalLink, Activity, Info, FileSearch, CheckCircle2 } from 'lucide-react';
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
  const [showAgencyModal, setShowAgencyModal] = useState(false);

  // Partial data to reflect Phase 2 mock state
  const mockResult = {
    doi,
    total_score: 55.4,
    grade: 'D',
    integrity_gate_triggered: false,
    confidence_tier: 'AUTOMATED_60',
    dimensions: [
      { dimension_id: 2, raw_score: 4.2, automated: true, origin_snippet: 'OpenAlex metadata extraction confirmed stable citation velocity.' },
      { dimension_id: 9, raw_score: 5.0, automated: true, origin_snippet: 'Crossref clean. NIH RePORTER verified PI funding history. No retraction event found.' },
      { dimension_id: 3, raw_score: 0.0, automated: false, origin_snippet: 'NULL. Requires qualitative agency review.' },
    ] as { dimension_id: number; raw_score: number; automated: boolean; origin_snippet?: string }[],
  };

  const gradeClass = `grade-${mockResult.grade}`;

  return (
    <main className="min-h-screen px-6 py-12 max-w-5xl mx-auto">
      {/* Back nav & Confidence Header */}
      <div className="flex items-center justify-between mb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-slate-400 hover:text-indigo-400 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>
        <div className="px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold flex items-center gap-2 animate-fade-up">
          <Activity className="w-3.5 h-3.5" />
          ESTIMATED CONFIDENCE: 60%
        </div>
      </div>

      {/* Main Header Card */}
      <div className="glass-card p-8 mb-8 animate-fade-up">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-mono text-slate-500 mb-2">Paper Identifier</p>
            <h1 className="text-xl font-bold mb-2 text-slate-100">{doi}</h1>
            <div className="flex gap-4">
              <a href="#" className="inline-flex items-center gap-1 text-slate-400 hover:text-indigo-300 text-sm">
                View Source PDF <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
          <div className="text-center bg-slate-900/50 p-4 rounded-2xl border border-slate-700/50">
            <div className={`grade-badge ${gradeClass} text-4xl w-20 h-20 mb-2 shadow-xl shadow-current/10 mx-auto`}>
              {mockResult.grade}
            </div>
            <p className="text-sm font-semibold text-slate-300">
              {mockResult.total_score.toFixed(1)} / 100
            </p>
            <p className="text-xs text-slate-500 mt-1">provisional score</p>
          </div>
        </div>
      </div>

      {/* Integrity Gate Status */}
      <div className={`integrity-indicator mb-8 animate-fade-up animate-delay-1 ${
        mockResult.integrity_gate_triggered ? 'integrity-fail' : 'integrity-pass'
      }`}>
        <Shield className="w-5 h-5 flex-shrink-0" />
        <div>
          <p className="font-semibold text-slate-200">Integrity Gate: PASSED</p>
          <p className="text-xs opacity-80 mt-0.5">Automated screening detected zero ethical breaches or retractions.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Col: Dimension Breakdown */}
        <section className="lg:col-span-2 glass-card p-8 animate-fade-up animate-delay-2">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-400" /> Scoring Breakdown
          </h2>
          <div className="space-y-4">
            {Array.from({ length: 9 }, (_, i) => i + 1).map((dimId) => {
              const dim = mockResult.dimensions.find(d => d.dimension_id === dimId);
              const score = dim?.raw_score ?? 0;
              const pct = (score / 5) * 100;
              const isGov = dimId === 9;
              const isMissing = score === 0;

              return (
                <div
                  key={dimId}
                  className={`p-4 rounded-xl border transition-all ${
                    isMissing ? 'border-slate-800 bg-slate-800/20 opacity-60 grayscale' :
                    isGov ? 'border-red-500/20 bg-red-500/5' : 'border-indigo-500/20 bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-slate-500 w-6">D{dimId}</span>
                      <span className="text-sm font-medium text-slate-300">
                        {DIMENSION_NAMES[dimId]}
                      </span>
                      {isGov && (
                        <span className="text-[10px] font-bold uppercase tracking-wider text-red-500 bg-red-500/10 px-2 py-0.5 rounded-full ring-1 ring-red-500/20">
                          Gate
                        </span>
                      )}
                    </div>
                    <span className={`text-sm font-semibold tabular-nums ${isMissing ? 'text-slate-500' : ''}`}>
                      {isMissing ? 'Pending Data' : `${score.toFixed(1)}/5`}
                    </span>
                  </div>
                  <div className="score-bar">
                    <div
                      className={`score-bar-fill ${isMissing ? 'bg-transparent' : isGov ? 'bg-red-500' : 'bg-indigo-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  {dim?.origin_snippet && (
                    <details className="mt-3 group">
                      <summary className="text-xs text-indigo-400/80 cursor-pointer hover:text-indigo-300 flex items-center gap-1 select-none">
                        <Info className="w-3 h-3 group-open:hidden" /> 
                        <span className="group-open:hidden">Origin Snippet Source</span>
                        <span className="hidden group-open:inline text-slate-500">Close snippet</span>
                      </summary>
                      <pre className="mt-2 text-xs text-slate-400 bg-black/40 p-3 rounded-lg overflow-x-auto border border-slate-800 text-wrap leading-relaxed">
                        {dim.origin_snippet}
                      </pre>
                    </details>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Right Col: Upgrades */}
        <section className="lg:col-span-1 space-y-6 animate-fade-up animate-delay-3">
          <div className="glass-card p-6 border-indigo-500/30 shadow-lg shadow-indigo-500/10">
            <h3 className="font-bold text-lg mb-2 flex items-center gap-2">
              <FileSearch className="w-5 h-5 text-indigo-400" />
              Increase Precision
            </h3>
            <p className="text-sm text-slate-400 mb-6">
              AI automation currently provides ~60% analytical fidelity. Select an upgrade for a human-in-the-loop review.
            </p>
            
            <div className="space-y-4">
              <button 
                onClick={() => setShowAgencyModal(true)}
                className="w-full text-left p-4 rounded-xl border border-slate-700 bg-slate-800/50 hover:bg-slate-800 hover:border-indigo-500 transition-all group"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-indigo-300 group-hover:text-indigo-200">88% Agency Assist</span>
                  <span className="text-xs font-mono bg-slate-900 px-2 py-1 rounded text-slate-400">Standard</span>
                </div>
                <p className="text-xs text-slate-500">Human completion of Missing (NULL) structural metrics.</p>
              </button>

              <button 
                onClick={() => setShowAgencyModal(true)}
                className="w-full text-left p-4 rounded-xl border border-purple-500/30 bg-purple-500/5 hover:bg-purple-500/10 hover:border-purple-500/50 transition-all group relative overflow-hidden"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-purple-300 group-hover:text-purple-200 flex items-center gap-2">
                    100% Expert Audit
                  </span>
                  <span className="text-xs font-mono bg-purple-500/20 text-purple-300 px-2 py-1 rounded">Premium</span>
                </div>
                <p className="text-xs text-purple-300/60 transition-colors group-hover:text-purple-300/80">
                  Full qualitative verification against hallucinations and systemic biases.
                </p>
              </button>
            </div>
          </div>
        </section>
      </div>

      {/* Agency Contact Modal */}
      {showAgencyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-up">
          <div className="glass-card max-w-md w-full p-8 relative border-slate-600 shadow-2xl">
            <div className="w-12 h-12 bg-green-500/10 text-green-400 rounded-full flex items-center justify-center mb-4">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold mb-2">Request Received</h3>
            <p className="text-slate-400 mb-8 text-sm">
              Your request for a higher-tier human review has been securely logged. The MatDAO operational team will reach out to you shortly to initiate the verification protocol.
            </p>
            <button 
              onClick={() => setShowAgencyModal(false)}
              className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-medium transition-colors"
            >
              Close and Return
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
