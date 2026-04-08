import Dropzone from '@/components/Dropzone';
import ProgressStats from '@/components/ProgressStats';

export default function Home() {
  return (
    <main className="min-h-screen relative overflow-hidden flex flex-col items-center justify-center p-6">
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-indigo-600/20 rounded-full blur-[100px] -z-10 mix-blend-screen animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[120px] -z-10 mix-blend-screen" />
      
      <div className="max-w-4xl w-full z-10 flex flex-col">
        <h1 className="text-5xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400 mb-6 text-center tracking-tight">
          MatDAO Engine
        </h1>
        <p className="text-slate-400 text-lg text-center mb-12 max-w-2xl mx-auto font-medium">
          Automated Scientific Due Diligence. Upload research papers to begin the 4-layer extraction and 9-dimension scoring pipeline.
        </p>

        <Dropzone />
        <ProgressStats />
      </div>
    </main>
  );
}
