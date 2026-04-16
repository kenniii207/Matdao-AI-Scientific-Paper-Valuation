'use client';

import { useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import AppHeader from '@/components/AppHeader';
import AppFooter from '@/components/AppFooter';

type UploadState = 'idle' | 'uploading' | 'error';

export default function SubmitClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const intent = searchParams.get('intent');

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [message, setMessage] = useState<string>('');

  const headline = useMemo(() => {
    if (intent === 'strength') return 'Validate research strength';
    if (intent === 'industry') return 'Find industry / investor fit';
    return 'Upload your research';
  }, [intent]);

  const helper = useMemo(() => {
    if (intent === 'strength')
      return 'Benchmark your work against peer standards and evaluate investability signals.';
    if (intent === 'industry')
      return 'Map research to real-world demand and identify institutional partner interest.';
    return 'We will analyze your work using our 4-layer evaluation pipeline.';
  }, [intent]);

  const uploadFile = async (file: File) => {
    setUploadState('uploading');
    setMessage('Uploading PDF and extracting text...');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${apiUrl}/api/upload`, { method: 'POST', body: formData });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const detail = data?.detail || data?.error || 'Upload failed';
        throw new Error(detail);
      }

      const paperId = data?.paper_id;
      if (!paperId) throw new Error('Server response missing paper_id');

      setMessage('Upload accepted. Evaluation running...');
      router.push(`/papers/${encodeURIComponent(String(paperId))}`);
    } catch (err) {
      setUploadState('error');
      setMessage(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader />

      <main className="max-w-7xl mx-auto px-6 md:px-8 pt-10 pb-24 grid grid-cols-1 lg:grid-cols-12 gap-12 w-full">
        <div className="lg:col-span-4 flex flex-col justify-start pt-10">
          <h1 className="font-headline font-extrabold text-5xl text-primary tracking-tight leading-tight mb-4">
            {headline}
          </h1>
          <p className="text-on-surface-variant text-lg leading-relaxed max-w-sm">{helper}</p>

          <div className="mt-12 space-y-6">
            <div className="flex items-center gap-4 text-sm font-label uppercase tracking-widest text-primary-fixed">
              <span className="h-[1px] w-8 bg-primary-fixed" />
              Protocol Specs
            </div>
            <ul className="space-y-4">
              {[
                'Automated Peer-Review Synthesis',
                'Citation Integrity Mapping',
                'Cross-Domain Evaluation',
              ].map((t) => (
                <li key={t} className="flex gap-3 items-start">
                  <span className="material-symbols-outlined text-primary-fixed-dim text-sm mt-1">
                    check_circle
                  </span>
                  <span className="text-on-surface-variant text-sm italic">{t}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="lg:col-span-8">
          <div className="bg-surface-container p-8 lg:p-12 rounded-xl border border-outline-variant/15 relative overflow-hidden">
            <div className="absolute -top-24 -right-24 w-72 h-72 bg-surface-tint/10 blur-[90px] rounded-full" />

            <div className="relative z-10 flex flex-col gap-10">
              <div
                className={[
                  'min-h-[360px] flex flex-col items-center justify-center p-8 transition-all border border-dashed rounded-xl',
                  'border-primary-fixed/30 hover:bg-surface-container-high/20',
                ].join(' ')}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const f = e.dataTransfer.files?.[0];
                  if (f) uploadFile(f);
                }}
              >
                <div className="mb-6 bg-surface-container-highest w-20 h-20 rounded-full flex items-center justify-center border border-outline-variant/20">
                  <span className="material-symbols-outlined text-primary-fixed text-4xl">
                    upload_file
                  </span>
                </div>

                <h3 className="font-headline text-xl text-primary font-semibold mb-2">
                  Drag &amp; drop your paper here
                </h3>
                <p className="text-on-surface-variant text-sm mb-6">
                  PDF up to 50MB (born-digital preferred; scanned PDFs require OCR key)
                </p>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) uploadFile(f);
                  }}
                  disabled={uploadState === 'uploading'}
                />

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-primary-container text-on-primary-fixed px-8 py-3 rounded-md font-bold text-sm tracking-tight hover:brightness-110 active:scale-[0.99] transition-all flex items-center gap-2"
                  disabled={uploadState === 'uploading'}
                >
                  <span>{uploadState === 'uploading' ? 'Uploading…' : 'Upload file'}</span>
                  <span className="material-symbols-outlined text-base">add</span>
                </button>

                {message ? (
                  <p
                    className={[
                      'mt-6 text-sm',
                      uploadState === 'error' ? 'text-error' : 'text-on-surface-variant',
                    ].join(' ')}
                  >
                    {message}
                  </p>
                ) : null}
              </div>

              <div className="flex flex-col md:flex-row items-center gap-6 justify-between">
                <div className="flex gap-6">
                  <button
                    type="button"
                    className="flex items-center gap-2 text-primary-fixed hover:text-white transition-colors text-xs font-label uppercase tracking-widest group"
                    onClick={() => setMessage('DOI flow not wired yet — upload PDF for now.')}
                  >
                    <span className="material-symbols-outlined text-sm group-hover:scale-110 transition-transform">
                      database
                    </span>
                    Paste DOI
                  </button>
                  <button
                    type="button"
                    className="flex items-center gap-2 text-primary-fixed hover:text-white transition-colors text-xs font-label uppercase tracking-widest group"
                    onClick={() => setMessage('Link flow not wired yet — upload PDF for now.')}
                  >
                    <span className="material-symbols-outlined text-sm group-hover:scale-110 transition-transform">
                      link
                    </span>
                    Paste Link
                  </button>
                </div>

                <div className="h-[1px] flex-grow bg-outline-variant/10 hidden md:block" />

                <button
                  type="button"
                  className="w-full md:w-auto bg-on-surface-variant/15 text-on-surface px-10 py-4 rounded-md font-bold text-base tracking-tighter hover:bg-primary-fixed/10 transition-colors flex items-center justify-center gap-3"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadState === 'uploading'}
                >
                  Start Evaluation
                  <span className="material-symbols-outlined">bolt</span>
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            {[
              {
                icon: 'security',
                title: 'Encrypted',
                body: 'Transport encrypted; secrets stay on backend.',
              },
              {
                icon: 'memory',
                title: 'Neural Core',
                body: 'Gemini evaluation + integrity gate enforcement.',
              },
              {
                icon: 'history_edu',
                title: 'Audit Trail',
                body: 'Origin snippets stored per dimension.',
              },
            ].map((c) => (
              <div
                key={c.title}
                className="bg-surface-container-low p-6 rounded-lg border border-outline-variant/10"
              >
                <div className="text-primary-fixed mb-2">
                  <span className="material-symbols-outlined text-lg">{c.icon}</span>
                </div>
                <div className="text-xs font-label uppercase tracking-widest text-on-surface mb-1">
                  {c.title}
                </div>
                <div className="text-xs text-on-surface-variant">{c.body}</div>
              </div>
            ))}
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}

