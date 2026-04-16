'use client';

import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useMemo, useState } from 'react';

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
    <main className="min-h-screen px-6 py-12 max-w-4xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <Link
          href={`/papers/${encodeURIComponent(paperId)}`}
          className="inline-flex items-center gap-2 text-slate-400 hover:text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>
        <span className="text-xs font-semibold tracking-[0.1em] uppercase text-primary">Layer 3 Human Audit</span>
      </div>

      <section className="glass-card p-8">
        <h1 className="text-3xl font-semibold mb-2">Expert Review Intake</h1>
        <p className="text-sm text-slate-400 mb-6">Paper ID: {paperId}</p>

        {submitted ? (
          <div className="rounded-md border border-primary/40 bg-primary/10 px-4 py-3 text-primary">
            Expert review was captured locally for this prototype flow.
          </div>
        ) : null}

        <div className="[&_label]:text-slate-300 [&_input]:bg-black/20 [&_input]:border [&_input]:border-outline_variant/40 [&_input]:rounded-md [&_textarea]:bg-black/20 [&_textarea]:border [&_textarea]:border-outline_variant/40 [&_textarea]:rounded-md [&_select]:bg-black/20 [&_select]:border [&_select]:border-outline_variant/40 [&_button[type='submit']]:bg-gradient-to-br [&_button[type='submit']]:from-primary_container [&_button[type='submit']]:to-primary [&_button[type='submit']]:text-black [&_button[type='submit']]:font-semibold [&_button[type='submit']]:rounded-sm [&_button[type='submit']]:px-4 [&_button[type='submit']]:py-2">
          <Form
            schema={schema}
            uiSchema={uiSchema}
            validator={validator}
            onSubmit={() => setSubmitted(true)}
          />
        </div>
      </section>
    </main>
  );
}
