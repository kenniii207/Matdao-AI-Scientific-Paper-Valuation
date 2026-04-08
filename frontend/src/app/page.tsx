'use client';

import { useState } from 'react';
import { Search, FileText, Shield, TrendingUp, AlertTriangle } from 'lucide-react';

const DIMENSION_NAMES = [
  'Return on Research Investment',
  'Scientific Quality & Rigor',
  'Market Size & Scalability',
  'Competitive Moat & IP',
  'Team Quality & Track Record',
  'Societal Impact & ESG',
  'Research Pipeline Risk',
  'Risk & Uncertainty Profile',
  'Governance & Transparency',
];

export default function DashboardPage() {
  const [doi, setDoi] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!doi.trim()) return;
    setIsLoading(true);
    try {
      const res = await fetch('/api/papers/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doi: doi.trim() }),
      });
      const data = await res.json();
      console.log('Evaluation submitted:', data);
    } catch (err) {
      console.error('Submission failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen px-6 py-12 max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-16 animate-fade-up">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            MatDAO
          </h1>
        </div>
        <p className="text-slate-400 text-lg ml-[52px]">
          Automated Scientific Due Diligence Platform
        </p>
      </header>

      {/* Paper Submission */}
      <section className="glass-card p-8 mb-12 animate-fade-up animate-delay-1" id="paper-submit">
        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-400" />
          Evaluate a Research Paper
        </h2>
        <form onSubmit={handleSubmit} className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            <input
              id="doi-input"
              type="text"
              value={doi}
              onChange={(e) => setDoi(e.target.value)}
              placeholder="Enter DOI (e.g., 10.1038/s41586-020-2649-2)"
              className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all"
            />
          </div>
          <button
            id="submit-btn"
            type="submit"
            disabled={isLoading || !doi.trim()}
            className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-xl hover:from-indigo-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:shadow-lg hover:shadow-indigo-500/20"
          >
            {isLoading ? 'Evaluating...' : 'Evaluate'}
          </button>
        </form>
      </section>

      {/* Overview Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 animate-fade-up animate-delay-2">
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-green-400" />
            </div>
            <span className="text-slate-400 text-sm font-medium">Papers Evaluated</span>
          </div>
          <p className="text-3xl font-bold">0</p>
        </div>
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center">
              <Shield className="w-4 h-4 text-indigo-400" />
            </div>
            <span className="text-slate-400 text-sm font-medium">Integrity Checks</span>
          </div>
          <p className="text-3xl font-bold">0</p>
        </div>
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-red-400" />
            </div>
            <span className="text-slate-400 text-sm font-medium">Retractions Caught</span>
          </div>
          <p className="text-3xl font-bold">0</p>
        </div>
      </section>

      {/* 9-Dimension Overview */}
      <section className="glass-card p-8 animate-fade-up animate-delay-3" id="dimensions-overview">
        <h2 className="text-xl font-semibold mb-6">9-Dimension Scoring Rubric</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {DIMENSION_NAMES.map((name, i) => (
            <div
              key={i}
              className={`p-4 rounded-xl border transition-all hover:scale-[1.02] ${
                i === 8
                  ? 'border-red-500/30 bg-red-500/5 hover:border-red-500/50'
                  : 'border-slate-700/50 bg-slate-800/30 hover:border-indigo-500/30'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-slate-500">D{i + 1}</span>
                {i === 8 && (
                  <span className="text-[10px] font-bold uppercase tracking-wider text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">
                    Integrity Gate
                  </span>
                )}
              </div>
              <p className="text-sm font-medium text-slate-300">{name}</p>
              <div className="score-bar mt-3">
                <div className="score-bar-fill bg-slate-600" style={{ width: '0%' }} />
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
