'use client';

import { useState, useRef } from 'react';
import { Shield, Upload, FileText, Briefcase, Zap, AlertTriangle } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
  const router = useRouter();
  const [persona, setPersona] = useState<'RESEARCHER' | 'INVESTOR'>('INVESTOR');
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      
      if (res.ok && data.mock_doi) {
        // Reroute to the new paper URL passing the DOI surrogate
        // Note: encoding the slash because DOIs contain slashes.
        const encodedDoi = encodeURIComponent(data.mock_doi);
        router.push(`/papers/${encodedDoi}`);
      } else {
        alert(data.detail || 'Upload failed');
      }
    } catch (err) {
      console.error('Submission failed:', err);
      alert('Network error during upload');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <main className="min-h-screen px-6 py-12 max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-12 animate-fade-up flex justify-between items-end">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              MatDAO
            </h1>
          </div>
          <p className="text-slate-400 text-lg ml-[52px]">
            Automated Scientific Due Diligence Platform
          </p>
        </div>
        
        {/* Persona Toggle */}
        <div className="flex bg-slate-800/50 p-1 rounded-xl border border-slate-700/50">
          <button
            onClick={() => setPersona('RESEARCHER')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              persona === 'RESEARCHER' 
                ? 'bg-slate-700 text-white shadow-sm' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" /> Researcher
            </div>
          </button>
          <button
            onClick={() => setPersona('INVESTOR')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              persona === 'INVESTOR' 
                ? 'bg-indigo-500 text-white shadow-sm shadow-indigo-500/20' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4" /> Investor
            </div>
          </button>
        </div>
      </header>

      {/* Main Action Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-12">
        {/* Left Col: Upload */}
        <section className="lg:col-span-8 animate-fade-up animate-delay-1">
          <div 
            className={`glass-card p-12 h-full flex flex-col items-center justify-center text-center border-2 border-dashed transition-all ${
              dragActive ? 'border-indigo-500 bg-indigo-500/5 scale-[1.01]' : 'border-slate-700/50 hover:border-slate-600'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {isUploading ? (
              <div className="flex flex-col items-center gap-4">
                <div className="w-16 h-16 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                <div>
                  <h3 className="text-xl font-semibold mb-1">Evaluating Research Document</h3>
                  <p className="text-slate-400 text-sm">GLM-OCR neural extraction running... (~3 sec for MVP)</p>
                </div>
              </div>
            ) : (
              <>
                <div className="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center mb-6 shadow-xl">
                  <Upload className="w-8 h-8 text-indigo-400" />
                </div>
                <h2 className="text-2xl font-bold mb-3">
                  Upload PDF to Begin Analysis
                </h2>
                <p className="text-slate-400 mb-8 max-w-md">
                  {persona === 'RESEARCHER' 
                    ? "Upload your preprint or final draft to evaluate market fit, IP moat, and catch structural flaws before investor review."
                    : "Upload a dense scientific paper to automatically extract ROI potential, Team Quality, and ESG risks."}
                </p>
                <input 
                  type="file" 
                  accept=".pdf" 
                  className="hidden" 
                  ref={fileInputRef}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) handleFileUpload(e.target.files[0]);
                  }}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-xl hover:from-indigo-500 hover:to-purple-500 transition-all hover:shadow-lg hover:shadow-indigo-500/20 flex items-center gap-2"
                >
                  <FileText className="w-5 h-5" /> Select Local File
                </button>
              </>
            )}
          </div>
        </section>

        {/* Right Col: Process Explanation */}
        <section className="lg:col-span-4 flex flex-col gap-4 animate-fade-up animate-delay-2">
          <div className="glass-card p-6 border-indigo-500/20 bg-indigo-500/5">
            <h3 className="font-semibold text-indigo-400 flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4" /> 60% Automated Extent
            </h3>
            <p className="text-sm text-slate-400">
              The AI layer instantly processes structure, citations (Dimension 2), and runs the Integrity Gate cross-checks (Dimension 9).
            </p>
          </div>
          <div className="glass-card p-6">
            <h3 className="font-semibold text-slate-300 flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4" /> 88% Agency Assisted
            </h3>
            <p className="text-sm text-slate-400">
              Human-in-the-loop completion for Market Size and Defensibility parameters that the AI could not definitively measure.
            </p>
          </div>
          <div className="glass-card p-6">
            <h3 className="font-semibold text-slate-300 mb-2">100% Expert Audit</h3>
            <p className="text-sm text-slate-400">
              Full qualitative synthesis and manual override of any systemic biases or hallucinated signals by MatDAO experts.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
