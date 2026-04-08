'use client';

import { useState, useEffect } from 'react';

interface Stats {
  total_papers: number;
  total_scored: number;
  progress_percent: number;
}

export default function ProgressStats() {
  const [stats, setStats] = useState<Stats>({ total_papers: 0, total_scored: 0, progress_percent: 0 });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/papers/stats/summary`);
        const data = await res.json();
        setStats(data);
      } catch (e) {
        console.error(e);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-card p-6 animate-fade-up animate-delay-1 flex gap-8 items-center mt-8">
      <div className="relative w-32 h-32 flex items-center justify-center rounded-full border-4 border-slate-800">
        <svg className="absolute w-full h-full -rotate-90" viewBox="0 0 36 36">
          <path
            className="text-slate-800"
            strokeWidth="3"
            stroke="currentColor"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path
            className="text-indigo-500 drop-shadow-[0_0_8px_rgba(99,102,241,0.8)]"
            strokeDasharray={`${stats.progress_percent}, 100`}
            strokeWidth="3"
            strokeLinecap="round"
            stroke="currentColor"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            style={{ transition: 'stroke-dasharray 1s ease' }}
          />
        </svg>
        <span className="text-2xl font-bold text-white">{stats.progress_percent}%</span>
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="text-2xl font-bold text-white">Analysis Progress</h3>
        <p className="text-slate-400">Total Papers Ingested: <span className="text-white font-medium">{stats.total_papers}</span></p>
        <p className="text-slate-400">Successfully Scored: <span className="text-indigo-400 font-medium">{stats.total_scored}</span></p>
      </div>
    </div>
  );
}
