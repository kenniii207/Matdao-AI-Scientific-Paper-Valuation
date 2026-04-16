'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

interface DimensionScore {
  dimension_id: number;
  dimension_name: string;
  raw_score: number;
  rationale: string;
  origin_snippet: string;
}

export default function PaperAuditPage() {
  const { id } = useParams();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
        const res = await fetch(`${apiUrl}/api/scoring/results/${id}`);
        if (!res.ok) throw new Error('Result not found or not yet processed.');
        const json = await res.json();
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Analysis retrieval failed.');
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
  }, [id]);

  if (loading) return (
    <div className="min-h-screen bg-[#131313] flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-2 border-[#97fdff] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-[#b8b8b8] font-mono text-xs uppercase tracking-widest">Retrieving Neural Audit...</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-[#131313] flex items-center justify-center p-6">
      <div className="glass-card p-12 text-center max-w-md">
        <div className="text-red-400 mb-6 text-4xl">⚠️</div>
        <h2 className="tech-display text-xl font-bold mb-2">Audit Synchronization Failed</h2>
        <p className="text-[#b8b8b8] text-sm mb-8">{error}</p>
        <button onClick={() => router.push('/submit')} className="px-8 py-3 bg-[#97fdff] text-[#131313] font-bold rounded">
          BACK TO SUBMISSION
        </button>
      </div>
    </div>
  );

  const stats = [
    { label: 'GRADE', value: data.grade, color: `var(--grade-${data.grade?.toLowerCase()})` },
    { label: 'SCORE', value: `${Math.round(data.total_score)}/100`, color: 'var(--accent)' },
    { label: 'INTEGRITY', value: data.integrity_gate_triggered ? 'UNSAFE' : 'SECURE', color: data.integrity_gate_triggered ? 'var(--grade-f)' : 'var(--grade-a)' },
    { label: 'FIDELITY', value: data.confidence_tier || 'AUTOMATED', color: '#b8b8b8' }
  ];

  return (
    <div className="min-h-screen bg-[#131313] text-[#e8e8e8] p-6 lg:p-12 font-sans selection:bg-[#97fdff]/30">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="px-2 py-0.5 bg-[#97fdff]/10 text-[#97fdff] text-[10px] font-mono border border-[#97fdff]/20">PROTOCOL {id?.slice(0, 8)}</span>
              <span className="text-xs text-[#b8b8b8] font-mono uppercase tracking-tighter cursor-pointer hover:text-white transition-colors" onClick={() => router.push('/submit')}>{"← Back"}</span>
            </div>
            <h1 className="tech-display text-3xl font-bold tracking-tight text-white uppercase break-all">
              {data.paper_title || 'Untitled Research Protocol'}
            </h1>
          </div>
          
          <div className="flex gap-2">
            {stats.map((s, i) => (
              <div key={i} className="glass-card px-6 py-4 min-w-[120px]">
                <div className="text-[10px] font-mono text-[#b8b8b8] uppercase mb-1">{s.label}</div>
                <div className="text-lg font-black tracking-tighter" style={{ color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>
        </header>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Scoring Grid */}
          <div className="lg:col-span-2 space-y-6">
            <h2 className="tech-display text-sm font-bold text-[#b8b8b8] uppercase tracking-widest mb-4 flex items-center gap-3">
               9-Dimension Scientific Audit
               <div className="h-[1px] flex-1 bg-white/10" />
            </h2>
            
            <div className="grid md:grid-cols-1 gap-4">
              {data.dimensions.map((dim: any, idx: number) => (
                <div key={dim.dimension_id} className="glass-card p-6 overflow-hidden relative group">
                  <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                    <span className="text-6xl font-black">0{dim.dimension_id}</span>
                  </div>
                  
                  <div className="flex justify-between items-start mb-4 relative z-10">
                    <div>
                      <h3 className="text-lg font-bold text-white flex items-center gap-2">
                         <span className="text-[#97fdff] font-mono text-xs">0{dim.dimension_id}</span>
                         {dim.dimension_name}
                      </h3>
                      <div className="flex gap-1 mt-1">
                        {[1,2,3,4,5].map(s => (
                          <div key={s} className={`w-3 h-1 rounded-full ${s <= dim.raw_score ? 'bg-[#97fdff]' : 'bg-white/10'}`} />
                        ))}
                      </div>
                    </div>
                    <div className="text-2xl font-black text-[#97fdff] font-mono">
                      {dim.raw_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="space-y-4 relative z-10">
                    <div className="p-3 bg-white/5 border-l-2 border-[#97fdff]/50">
                       <h4 className="text-[10px] uppercase font-mono text-[#97fdff] mb-1">AI Rationale</h4>
                       <p className="text-sm text-[#e8e8e8] leading-snug">{dim.rationale}</p>
                    </div>

                    {dim.origin_snippet && (
                      <div className="p-3 bg-black/40 rounded border border-white/5">
                        <h4 className="text-[10px] uppercase font-mono text-[#b8b8b8] mb-1 flex justify-between">
                          Origin Snippet (Evidence)
                          <span className="text-[#97fdff]/40">verified_source</span>
                        </h4>
                        <p className="text-xs text-[#b8b8b8] italic line-clamp-3 hover:line-clamp-none transition-all cursor-zoom-in">
                          "{dim.origin_snippet}"
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sidebar - Context & Actions */}
          <div className="space-y-8">
            <section className="glass-card p-6">
              <h3 className="tech-display text-xs font-bold text-[#97fdff] uppercase tracking-widest mb-6">INTEGRITY REPORT</h3>
              
              <div className="space-y-4">
                <div className={`p-4 rounded border ${data.integrity_gate_triggered ? 'bg-red-500/10 border-red-500/20' : 'bg-green-500/10 border-green-500/20'}`}>
                   <div className="flex items-center gap-3 mb-2">
                     <div className={`w-3 h-3 rounded-full ${data.integrity_gate_triggered ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`} />
                     <span className="text-xs font-bold uppercase tracking-tight">Dim 9: Governance</span>
                   </div>
                   <p className="text-xs text-[#b8b8b8]">
                     {data.integrity_gate_triggered 
                      ? "CRITICAL: Potential fraud, plagiarism, or retraction detected. Investment grade forced to 0." 
                      : "No immediate governance risks detected. The paper follows standard ethical guidelines."}
                   </p>
                </div>

                <div className="p-4 rounded border bg-white/5 border-white/5">
                   <h4 className="text-[10px] font-mono uppercase text-[#b8b8b8] mb-1">Source Model</h4>
                   <p className="text-xs font-bold">Falcon-OCR 300M + GLM-4 Synthesis</p>
                </div>
              </div>
            </section>

            <section className="glass-card p-6">
              <h3 className="tech-display text-xs font-bold text-[#b8b8b8] uppercase tracking-widest mb-6">NEXT ACTIONS</h3>
              <div className="grid gap-3">
                <button className="w-full py-4 bg-white text-black font-bold uppercase tracking-widest text-xs hover:bg-[#97fdff] transition-all">
                  Generate PDF Report
                </button>
                <button className="w-full py-4 border border-white/10 font-bold uppercase tracking-widest text-xs hover:bg-white/5 transition-all text-[#b8b8b8]">
                  Submit to DAO Council
                </button>
              </div>
            </section>

            <section className="p-6 border border-dashed border-white/10 rounded">
               <p className="text-[10px] font-mono text-[#b8b8b8] uppercase text-center">
                 Automated Scientific Due Diligence <br/> 
                 Powered by MatDAO Protocol v0.1
               </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
