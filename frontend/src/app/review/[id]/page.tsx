'use client';

import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useMemo, useState } from 'react';
import AppFooter from '@/components/AppFooter';
import AppHeader from '@/components/AppHeader';
import { ErrorBoundary } from '@/components/ErrorBoundary';

interface PageProps {
  params: { id: string };
}

export default function ExpertReviewPage({ params }: PageProps) {
  const paperId = decodeURIComponent(params.id);
  const [submitted, setSubmitted] = useState(false);

  const schema = useMemo(
    () => ({
      title: 'Layer 3 — Expert Review Form',
      type: 'object',
      required: ['reviewerName', 'confidence', 'dim3Notes', 'dim4Notes', 'overallRecommendation'],
      properties: {
        reviewerName: { type: 'string', title: 'Reviewer Name' },
        confidence: { type: 'number', title: 'Reviewer Confidence (0-1)', minimum: 0, maximum: 1, multipleOf: 0.05 },
        dim3Notes: { type: 'string', title: 'Dimension 3 (Market) Notes' },
        dim4Notes: { type: 'string', title: 'Dimension 4 (Moat/IP) Notes' },
        dim5Notes: { type: 'string', title: 'Dimension 5 (Team) Notes' },
        dim8Notes: { type: 'string', title: 'Dimension 8 (Risk) Notes' },
        overallRecommendation: {
          type: 'string',
          title: 'Recommendation',
          enum: ['Proceed', 'Proceed with caution', 'Hold', 'Reject'],
        },
      },
    }),
    []
  );

  const uiSchema = useMemo(
    () => ({
      reviewerName: { 'ui:placeholder': 'Name / handle' },
      dim3Notes: { 'ui:widget': 'textarea', 'ui:options': { rows: 5 } },
      dim4Notes: { 'ui:widget': 'textarea', 'ui:options': { rows: 5 } },
      dim5Notes: { 'ui:widget': 'textarea', 'ui:options': { rows: 4 } },
      dim8Notes: { 'ui:widget': 'textarea', 'ui:options': { rows: 4 } },
      'ui:submitButtonOptions': {
        submitText: 'Submit Expert Review',
        norender: false,
      },
    }),
    []
  );

  return (
    <div className="min-h-screen flex flex-col bg-black">
      <AppHeader />

      <main className="flex-grow px-6 py-12 max-w-4xl mx-auto w-full relative">
        <div className="absolute inset-0 pointer-events-none -z-10">
          <div className="absolute inset-0 bg-black/[0.78]" />
          <div className="absolute top-[-10%] left-[8%] w-[360px] h-[360px] bg-cyan-400/[0.06] rounded-full blur-[130px]" />
          <div className="absolute bottom-[-16%] right-[6%] w-[360px] h-[360px] bg-indigo-500/[0.06] rounded-full blur-[130px]" />
        </div>
        <div className="mb-8 flex items-center justify-between">
          <Link
            href={`/papers/${encodeURIComponent(paperId)}`}
            className="inline-flex items-center gap-2 text-white/60 hover:text-[#97fdff] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <span className="text-xs font-semibold tracking-[0.2em] uppercase text-[#9efbff]">
            Layer 3 Human Audit
          </span>
        </div>

        <section className="workflow-panel rounded-xl p-8">
          <h1 className="text-3xl font-headline font-extrabold mb-2 text-white/90">Expert Review Intake</h1>
          <p className="text-sm text-white/60 mb-6">Paper ID: {paperId}</p>

          {submitted ? (
            <div className="rounded-md border border-primary-fixed/30 bg-primary-fixed/10 px-4 py-3 text-primary-fixed">
              Expert review captured locally for this prototype flow.
            </div>
          ) : null}

          <div className="[&_label]:text-white/80 [&_label]:font-medium [&_input]:bg-black/[0.35] [&_input]:border [&_input]:border-white/[0.24] [&_input]:text-white/85 [&_input]:rounded-md [&_textarea]:bg-black/[0.35] [&_textarea]:border [&_textarea]:border-white/[0.24] [&_textarea]:text-white/85 [&_textarea]:rounded-md [&_select]:bg-black/[0.35] [&_select]:border [&_select]:border-white/[0.24] [&_select]:text-white/85 [&_button[type='submit']]:bg-[#63f7ff] [&_button[type='submit']]:text-[#03272b] [&_button[type='submit']]:font-semibold [&_button[type='submit']]:rounded-md [&_button[type='submit']]:px-4 [&_button[type='submit']]:py-2 [&_button[type='submit']]:hover:bg-[#8cfbff]">
            <ErrorBoundary fallback={
              <div className="p-6 bg-red-500/10 border border-red-500/30 rounded-xl text-center">
                <h3 className="text-xl text-red-400 font-bold mb-2">Form Rendering Failed</h3>
                <p className="text-red-200/80 text-sm mb-4">A critical error occurred while loading the expert review intake form. This usually happens if the schema structure failed to load correctly.</p>
                <button type="button" onClick={() => window.location.reload()} className="px-4 py-2 bg-red-500/20 text-red-200 rounded-md border border-red-500/30 hover:bg-red-500/30 transition-colors">Reload Page</button>
              </div>
            }>
              <Form schema={schema} uiSchema={uiSchema} validator={validator} onSubmit={() => setSubmitted(true)} />
            </ErrorBoundary>
          </div>
        </section>
      </main>

      <AppFooter />
    </div>
  );
}
