'use client';

import { useState } from 'react';

export default function Dropzone() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    setLoading(true);
    setMessage('Uploading & parsing...');
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setMessage('Upload successful: ' + data.mock_doi);
      } else {
        setMessage('Error: ' + data.detail);
      }
    } catch (err) {
      setMessage('Error: ' + (err instanceof Error ? err.message : String(err)));
    }
    setLoading(false);
  };

  return (
    <div className="glass-card p-8 flex flex-col items-center justify-center animate-fade-up">
      <div className="border-2 border-dashed border-indigo-500/30 rounded-xl p-10 w-full text-center hover:border-indigo-400 transition-colors">
        <input 
          type="file" 
          accept=".pdf" 
          className="hidden" 
          id="pdf-upload" 
          onChange={onFileChange}
          disabled={loading}
        />
        <label htmlFor="pdf-upload" className="cursor-pointer flex flex-col items-center gap-4">
          <svg className="w-12 h-12 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
          <span className="text-xl font-medium text-slate-200">
            {loading ? 'Processing through GLM-OCR adapter...' : 'Drop research PDF here or click to browse'}
          </span>
          <span className="text-sm text-slate-400">PDFs up to 50MB</span>
        </label>
      </div>
      {message && <p className="mt-4 text-indigo-300 font-medium">{message}</p>}
    </div>
  );
}
