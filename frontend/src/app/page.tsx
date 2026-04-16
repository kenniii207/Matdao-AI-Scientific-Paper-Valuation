'use client';

import Link from 'next/link';
import AppFooter from '@/components/AppFooter';
import AppHeader from '@/components/AppHeader';

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden">
      <AppHeader />

      <main className="flex-grow flex flex-col items-center justify-center px-6 py-12 relative">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[680px] h-[680px] bg-surface-tint/10 rounded-full blur-[140px] pointer-events-none" />

        <div className="w-full max-w-6xl z-10">
          <div className="text-center mb-16">
            <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight text-on-surface mb-4">
              Let us know your intention
            </h1>
            <p className="text-on-surface-variant font-body max-w-xl mx-auto text-lg">
              Select objective that best matches current research phase to receive tailored analytical
              insights.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 mb-16">
            <Link
              href="/submit?intent=evaluate"
              className="md:col-span-4 group cursor-pointer transition-all duration-300 active:scale-[0.99]"
            >
              <div className="bg-surface-container rounded-xl overflow-hidden border border-outline-variant/15 hover:border-primary-fixed/30 h-full flex flex-col">
                <div className="h-40 overflow-hidden relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary-fixed/15 via-transparent to-transparent" />
                  <div className="absolute inset-0 bg-gradient-to-t from-surface-container to-transparent" />
                </div>
                <div className="p-8 flex-grow">
                  <span className="uppercase tracking-widest text-primary-fixed text-[10px] font-bold mb-3 block">
                    Process
                  </span>
                  <h3 className="font-headline text-xl font-bold text-on-surface mb-2">
                    Evaluate my research
                  </h3>
                  <p className="text-on-surface-variant text-sm font-body leading-relaxed">
                    Structured analysis of findings, methodology, and potential gaps.
                  </p>
                </div>
              </div>
            </Link>

            <Link
              href="/submit?intent=strength"
              className="md:col-span-4 group cursor-pointer transition-all duration-300 card-active active:scale-[0.99]"
            >
              <div className="bg-surface-container rounded-xl overflow-hidden border border-primary-fixed/40 h-full flex flex-col relative shadow-[0_0_40px_rgba(0,220,229,0.06)]">
                <div className="h-40 overflow-hidden relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary-fixed/25 via-transparent to-transparent" />
                  <div className="absolute inset-0 bg-gradient-to-t from-surface-container to-transparent" />
                  <div className="absolute top-4 right-4 bg-primary-fixed text-on-primary-fixed text-[10px] font-bold px-2 py-1 rounded-sm uppercase tracking-tighter">
                    Recommended
                  </div>
                </div>
                <div className="p-8 flex-grow">
                  <span className="uppercase tracking-widest text-primary-fixed text-[10px] font-bold mb-3 block">
                    Validation
                  </span>
                  <h3 className="font-headline text-xl font-bold text-on-surface mb-2">
                    See my research&apos;s strength
                  </h3>
                  <p className="text-on-surface-variant text-sm font-body leading-relaxed">
                    Benchmark against peer work and evaluate market viability.
                  </p>
                </div>
              </div>
            </Link>

            <Link
              href="/submit?intent=industry"
              className="md:col-span-4 group cursor-pointer transition-all duration-300 active:scale-[0.99]"
            >
              <div className="bg-surface-container rounded-xl overflow-hidden border border-outline-variant/15 hover:border-primary-fixed/30 h-full flex flex-col">
                <div className="h-40 overflow-hidden relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary-fixed/10 via-transparent to-transparent" />
                  <div className="absolute inset-0 bg-gradient-to-t from-surface-container to-transparent" />
                </div>
                <div className="p-8 flex-grow">
                  <span className="uppercase tracking-widest text-primary-fixed text-[10px] font-bold mb-3 block">
                    Network
                  </span>
                  <h3 className="font-headline text-xl font-bold text-on-surface mb-2">
                    Find industry / investor
                  </h3>
                  <p className="text-on-surface-variant text-sm font-body leading-relaxed">
                    Identify partners and investors aligned with your sector.
                  </p>
                </div>
              </div>
            </Link>
          </div>

          <div className="flex flex-col items-center">
            <Link
              href="/submit"
              className="bg-primary-fixed text-on-primary-fixed font-headline font-bold text-lg px-12 py-4 rounded-full hover:bg-primary-container transition-all duration-300 shadow-[0_0_20px_rgba(99,247,255,0.2)] active:scale-95"
            >
              Start Evaluation
            </Link>
            <p className="mt-6 text-on-surface-variant text-xs font-label uppercase tracking-widest opacity-60">
              Step 1 of 4 • Technical Scoping
            </p>
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}
