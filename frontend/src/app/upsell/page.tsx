import Link from 'next/link';
import AppFooter from '@/components/AppFooter';
import AppHeader from '@/components/AppHeader';

export default function UpsellPage() {
  return (
    <div className="min-h-screen flex flex-col bg-black">
      <AppHeader />

      <main className="flex-grow flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-6xl text-center">
          <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight text-white/85 mb-12">
            Improve your evaluation accuracy
          </h1>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch max-w-5xl mx-auto">
            <div className="rounded-2xl border border-white/20 bg-white/5 p-7 text-left">
              <div className="text-lg font-semibold text-white/80 mb-2">Automation Review</div>
              <div className="text-sm text-white/45 mb-5">
                Baseline evaluation using automated analysis from your research paper and global
                databases.
              </div>
              <ul className="text-sm text-white/45 space-y-2 list-disc pl-5">
                <li>Layer 1: Paper analysis</li>
                <li>Layer 2: Data enrichment via APIs</li>
              </ul>
            </div>

            <div className="rounded-2xl border border-white/10 bg-[#122a44] p-7 text-left">
              <div className="text-lg font-semibold text-white/90 mb-2">Expert Review</div>
              <div className="text-sm text-white/60 mb-5">
                Enhanced evaluation combining automated analysis with structured input and domain
                expertise.
              </div>
              <ul className="text-sm text-white/60 space-y-2 list-disc pl-5">
                <li>Layer 1 + 2: Automated analysis</li>
                <li>Layer 3: Structured business input</li>
              </ul>
            </div>

            <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-[#0e6f84] to-[#0a4e5f] p-7 text-left">
              <div className="text-lg font-semibold text-white mb-2">Full Evaluation</div>
              <div className="text-sm text-white/80 mb-5">
                Complete, investment-grade due diligence for high-stakes decisions and real-world
                execution.
              </div>
              <ul className="text-sm text-white/80 space-y-2 list-disc pl-5">
                <li>Layer 1 + 2 + 3: Full structured data</li>
                <li>Layer 4: Expert-level due diligence</li>
              </ul>
            </div>
          </div>

          <div className="mt-14">
            <Link
              href="/submit"
              className="inline-flex items-center justify-center rounded-full border border-white/20 bg-white/5 px-12 py-4 text-sm font-semibold text-white/80 hover:bg-white/10 transition-colors"
            >
              Let&apos;s Start
            </Link>
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}
