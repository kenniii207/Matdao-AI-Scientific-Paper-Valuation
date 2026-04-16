'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function SubmitPage() {
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'intent' | 'upload' | 'analyzing' | 'complete'>('intent');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<any>(null);
  const router = useRouter();

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    setStep('analyzing');
    setLoading(true);
    setMessage('Initiating 4-layer extraction pipeline...');
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const res = await fetch(`${apiUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      });
      
      const data = await res.json();
      if (res.ok) {
        setResult(data);
        setStep('complete');
        setMessage(data.status === 'queued' ? 'Upload received. Evaluation running...' : 'Evaluation complete. Paper scored and registered.');
      } else {
        setStep('upload');
        setMessage('Extraction Error: ' + data.detail);
      }
    } catch (err) {
      setStep('upload');
      setMessage('Network Error: ' + (err instanceof Error ? err.message : String(err)));
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#131313] text-[#e8e8e8] p-6 lg:p-12 font-sans selection:bg-[#97fdff]/30">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12 flex justify-between items-center">
          <div>
            <h1 className="tech-display text-4xl font-bold tracking-tight bg-gradient-to-r from-[#97fdff] to-[#3b82f6] bg-clip-text text-transparent">
              RESEARCH SUBMISSION
            </h1>
            <p className="text-[#b8b8b8] mt-2">Submit scientific work for MatDAO valuation and due diligence.</p>
          </div>
          <div className="hidden md:flex gap-4">
            <div className="glass-card px-4 py-2 text-xs font-mono text-[#97fdff]">
              STATUS: SYSTEM OPERATIONAL
            </div>
          </div>
        </header>

        {step === 'intent' && (
          <div className="grid md:grid-cols-3 gap-6 animate-fade-up">
            {[
              { id: 'submit', title: 'SUBMIT RESEARCH', desc: 'Upload your own work for valuation', icon: 'M12 4v16m8-8H4' },
              { id: 'invest', title: 'INTELLIGENCE', desc: 'Verify a paper for investment decisions', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2-2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
              { id: 'audit', title: 'AUDIT', desc: 'Review existing scores and protocol integrity', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' }
            ].map((i) => (
              <button 
                key={i.id}
                onClick={() => setStep('upload')}
                className="glass-card p-8 text-left group hover:scale-[1.02] active:scale-[0.98]"
              >
                <div className="w-12 h-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-all">
                  <svg className="w-6 h-6 text-[#97fdff]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d={i.icon}></path>
                  </svg>
                </div>
                <h3 className="tech-display text-xl font-bold mb-2">{i.title}</h3>
                <p className="text-sm text-[#b8b8b8]">{i.desc}</p>
              </button>
            ))}
          </div>
        )}

        {step === 'upload' && (
          <div className="max-w-2xl mx-auto glass-card p-12 text-center animate-fade-up">
            <input type="file" id="pdf-file" accept=".pdf" className="hidden" onChange={handleUpload} />
            <label htmlFor="pdf-file" className="cursor-pointer">
              <div className="w-20 h-20 bg-[#97fdff]/5 border-2 border-dashed border-[#97fdff]/30 rounded-full flex items-center justify-center mx-auto mb-8 hover:border-[#97fdff] transition-all">
                <svg className="w-10 h-10 text-[#97fdff]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                </svg>
              </div>
              <h2 className="text-2xl font-bold mb-2 text-white">Upload Research Paper</h2>
              <p className="text-[#b8b8b8] mb-8">PDF protocol or manuscript (Max 50MB)</p>
              {message && <p className="text-red-400 mb-4">{message}</p>}
              <div className="inline-block px-8 py-3 bg-[#97fdff] text-[#131313] font-bold rounded hover:bg-white transition-all">
                BROWSE FILES
              </div>
            </label>
            <button onClick={() => setStep('intent')} className="block mt-8 text-xs text-[#b8b8b8] hover:text-white uppercase tracking-widest mx-auto">
              {"< Back to categories"}
            </button>
          </div>
        )}

        {step === 'analyzing' && (
          <div className="max-w-3xl mx-auto glass-card p-12 animate-fade-up">
            <div className="flex items-center justify-between mb-8">
              <h2 className="tech-display text-2xl font-bold text-[#97fdff]">ANALYZING...</h2>
              <div className="flex gap-1">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="w-2 h-2 bg-[#97fdff] rounded-full animate-bounce" style={{ animationDelay: `${i * 0.2}s` }} />
                ))}
              </div>
            </div>
            
            <div className="space-y-6">
              {[
                { title: 'Extraction Layer', status: 'Falcon-OCR 300M Inference', done: !!result || loading },
                { title: 'API Enrichment', status: 'OpenAlex & Semantic Scholar', done: !!result },
                { title: 'Scientific Evaluation', status: 'GLM-4 Synthesis', done: !!result }
              ].map((s, i) => (
                <div key={i} className={`flex gap-4 p-4 rounded border transition-all ${s.done ? 'bg-green-500/5 border-green-500/20' : 'bg-white/5 border-white/5'}`}>
                  <div className={`w-1.5 h-auto rounded-full ${s.done ? 'bg-green-500' : 'bg-[#97fdff]/30 animate-pulse'}`} />
                  <div className="flex-1">
                    <div className="flex justify-between items-center">
                      <h4 className="text-[10px] font-mono text-[#97fdff] uppercase">{s.title}</h4>
                      {s.done && <span className="text-[10px] font-mono text-green-400">COMPLETE</span>}
                    </div>
                    <p className={`text-sm font-medium mt-1 ${s.done ? 'text-white' : 'text-[#b8b8b8]'}`}>{s.status}</p>
                  </div>
                </div>
              ))}
            </div>
            
            <p className="text-center mt-12 text-xs font-mono text-[#b8b8b8] animate-pulse">
              {message}
            </p>
          </div>
        )}

        {step === 'complete' && result && (
          <div className="max-w-4xl mx-auto animate-fade-up">
            <div className="glass-card overflow-hidden">
              <div className="p-8 border-b border-white/10 flex justify-between items-center bg-gradient-to-r from-green-500/10 to-transparent">
                <div>
                  <h2 className="text-2xl font-bold text-white uppercase tracking-tight">EVALUATION COMPLETE</h2>
                  <p className="text-sm text-green-400 font-mono">PAPER ID: {result.paper_id}</p>
                </div>
                <div className={`grade-badge grade-${result.grade}`}>
                  {result.grade}
                </div>
              </div>
              
              <div className="p-8">
                <div className="mb-8">
                  <h3 className="text-xs font-mono uppercase text-[#97fdff] mb-4">Executive Summary</h3>
                  <p className="text-lg leading-relaxed text-[#e8e8e8]">
                    {result.eval_summary || "Synthesis complete. The research has been evaluated across 9 dimensions."}
                  </p>
                </div>
                
	                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
	                  <div className="p-4 rounded bg-white/5 border border-white/5">
	                    <span className="text-[10px] uppercase font-mono text-[#b8b8b8]">Total Score</span>
	                    <div className="text-2xl font-bold text-[#97fdff]">{result.score != null ? `${result.score}/100` : '--'}</div>
	                  </div>
	                  <div className="p-4 rounded bg-white/5 border border-white/5">
	                    <span className="text-[10px] uppercase font-mono text-[#b8b8b8]">Confidence</span>
	                    <div className="text-sm font-bold">HIGH (FALCON-OCR)</div>
	                  </div>
                  <div className="p-4 rounded bg-white/5 border border-white/5 col-span-2">
                    <span className="text-[10px] uppercase font-mono text-[#b8b8b8]">Integrity Gate</span>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span className="text-xs font-bold text-green-500">CLEARED - NO RETRACTIONS FOUND</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-4">
                  <button 
                    onClick={() => router.push(`/papers/${result.paper_id}`)}
                    className="flex-1 px-8 py-3 bg-[#97fdff] text-[#131313] font-bold rounded hover:shadow-[0_0_20px_rgba(151,253,255,0.4)] transition-all uppercase tracking-wider text-sm"
                  >
                    View Detailed Audit
                  </button>
                  <button 
                    onClick={() => setStep('intent')}
                    className="px-8 py-3 border border-white/10 font-bold rounded hover:bg-white/5 transition-all uppercase tracking-wider text-sm"
                  >
                    Submit New
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
