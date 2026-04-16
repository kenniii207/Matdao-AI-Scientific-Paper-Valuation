import Link from 'next/link';
import AppFooter from '@/components/AppFooter';
import AppHeader from '@/components/AppHeader';

export default function UpsellPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader />

      <main className="relative flex-grow pt-12 pb-24 px-6 overflow-hidden">
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-surface-tint/10 rounded-full blur-[120px] -z-10 translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 left-0 w-[420px] h-[420px] bg-primary-fixed/10 rounded-full blur-[110px] -z-10 -translate-x-1/2 translate-y-1/2" />

        <div className="max-w-6xl mx-auto">
          <div className="mb-16 text-center space-y-4">
            <span className="text-primary-fixed text-xs font-label uppercase tracking-[0.2em] font-semibold">
              Optimization Engine
            </span>
            <h1 className="text-5xl md:text-6xl font-headline font-extrabold text-on-surface tracking-tight max-w-3xl mx-auto leading-tight">
              Improve evaluation accuracy
            </h1>
            <p className="text-on-surface-variant max-w-xl mx-auto text-lg font-light leading-relaxed">
              Scale from automated baselines to investment-grade diligence.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {[
              {
                title: 'Automation Review',
                subtitle: 'Layer 1–2',
                body: 'Fast quantitative scan and data-driven pattern matching.',
                features: ['PDF text extraction', 'Metadata enrichment', 'Integrity gate'],
                cta: 'Select Baseline',
              },
              {
                title: 'Expert Review',
                subtitle: 'Layer 1–3',
                body: 'Adds human audit intake and structured rationale capture.',
                features: ['Expert notes', 'Confidence tiering', 'Audit trail'],
                cta: 'Upgrade Tier',
              },
            ].map((tier) => (
              <div
                key={tier.title}
                className="group relative flex flex-col bg-surface-container rounded-lg p-8 border border-white/5 transition-all duration-300 hover:bg-surface-container-high"
              >
                <div className="mb-8">
                  <div className="w-12 h-12 bg-surface-container-highest rounded-md flex items-center justify-center mb-6">
                    <span className="material-symbols-outlined text-primary-fixed">auto_awesome</span>
                  </div>
                  <h3 className="text-2xl font-headline font-bold text-on-surface mb-2">
                    {tier.title}
                  </h3>
                  <p className="text-on-surface-variant text-sm font-body leading-relaxed">
                    {tier.body}
                  </p>
                </div>

                <div className="mt-auto space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
                      <div className="w-3/4 bg-primary-fixed h-full shadow-[0_0_8px_#63f7ff]" />
                    </div>
                    <span className="text-[10px] uppercase font-bold tracking-widest text-on-surface-variant whitespace-nowrap">
                      {tier.subtitle}
                    </span>
                  </div>

                  <ul className="space-y-3 text-sm text-on-surface-variant">
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary-fixed text-xs">
                          check_circle
                        </span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>

                <button className="mt-8 py-3 px-6 rounded-md border border-outline-variant text-sm font-semibold text-on-surface hover:bg-white/5 transition-all active:scale-95">
                  {tier.cta}
                </button>
              </div>
            ))}

            <div className="group relative flex flex-col bg-surface-container-high rounded-lg p-8 border border-primary-fixed/30 overflow-hidden transition-all duration-300 scale-[1.02] shadow-2xl shadow-primary-fixed/5">
              <div className="absolute inset-0 bg-gradient-to-br from-primary-fixed/10 via-transparent to-transparent" />
              <div className="relative z-10">
                <div className="flex justify-between items-start mb-6">
                  <div className="w-12 h-12 bg-primary-container/20 rounded-md flex items-center justify-center">
                    <span className="material-symbols-outlined text-primary-fixed">shield_with_heart</span>
                  </div>
                  <span className="px-3 py-1 bg-primary-fixed/10 border border-primary-fixed/20 text-[10px] font-label font-bold text-primary-fixed rounded-full tracking-wider uppercase">
                    Premium
                  </span>
                </div>
                <h3 className="text-2xl font-headline font-extrabold text-on-surface mb-2">
                  Full Evaluation
                </h3>
                <p className="text-on-surface/80 text-sm font-body leading-relaxed">
                  Complete investment-grade due diligence with deeper forensic analysis.
                </p>
              </div>

              <div className="relative z-10 mt-auto space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="w-full bg-gradient-to-r from-primary-fixed-dim to-primary-fixed h-full shadow-[0_0_12px_#63f7ff]" />
                  </div>
                  <span className="text-[10px] uppercase font-bold tracking-widest text-primary-fixed whitespace-nowrap">
                    Layer 1–4
                  </span>
                </div>
                <ul className="space-y-3 text-sm text-on-surface/90">
                  {['Forensic governance checks', 'Report generation', 'Review workflow'].map((f) => (
                    <li key={f} className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary-fixed text-xs">
                        verified
                      </span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="relative z-10 mt-8">
                <Link
                  href="/submit"
                  className="block text-center w-full py-4 px-6 rounded-md bg-primary-fixed text-on-primary-fixed font-headline font-bold text-sm tracking-wide transition-all active:scale-95 shadow-[0_0_20px_rgba(99,247,255,0.2)] hover:shadow-[0_0_30px_rgba(99,247,255,0.35)]"
                >
                  Let&apos;s Start
                </Link>
              </div>
            </div>
          </div>

          <div className="mt-16 flex justify-center">
            <Link
              href="/submit"
              className="flex items-center gap-3 bg-transparent border border-primary-fixed text-primary-fixed px-10 py-4 rounded-full font-headline font-bold uppercase tracking-widest hover:bg-primary-fixed/5 transition-all duration-300 active:scale-95"
            >
              Back to Upload
              <span className="material-symbols-outlined">arrow_back</span>
            </Link>
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}

