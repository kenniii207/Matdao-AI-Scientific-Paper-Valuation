import AppFooter from '@/components/AppFooter';
import AppHeader from '@/components/AppHeader';
 
const EXTERNAL_EVAL_URL =
  'https://v0-matdao-platform.vercel.app?_vercel_share=5y6zhqZWEIIRGrUG1ahDUqf8M84AJQ5F';

export default function UpsellPage() {
  const tierBase =
    'workflow-panel-muted rounded-2xl p-7 text-left interactive-lift transition-colors';

  return (
    <div className="min-h-screen flex flex-col bg-black">
      <AppHeader />

      <main className="flex-grow flex items-center justify-center px-6 py-16 relative" data-route-item>
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-black/[0.78]" />
          <div className="absolute top-[-10%] left-[8%] w-[420px] h-[420px] bg-cyan-400/[0.06] rounded-full blur-[150px]" />
          <div className="absolute bottom-[-18%] right-[8%] w-[420px] h-[420px] bg-indigo-500/[0.06] rounded-full blur-[150px]" />
        </div>
        <div className="w-full max-w-6xl text-center relative z-10" data-route-item>
          <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight text-white/88 mb-12" data-route-item>
            Improve your evaluation accuracy
          </h1>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch max-w-5xl mx-auto" data-route-item>
            <div className={tierBase}>
              <div className="text-lg font-semibold text-white/80 mb-2">Automation Review</div>
              <div className="text-sm text-white/58 mb-5">
                Baseline evaluation using automated analysis from your research paper and global
                databases.
              </div>
              <ul className="text-sm text-white/58 space-y-2 list-disc pl-5">
                <li>Layer 1: Paper analysis</li>
                <li>Layer 2: Data enrichment via APIs</li>
              </ul>
            </div>

            <div className={`${tierBase} border-[#8fdbff]/[0.3] bg-[#122a44]/[0.76]`}>
              <div className="text-lg font-semibold text-white/90 mb-2">Expert Review</div>
              <div className="text-sm text-white/70 mb-5">
                Enhanced evaluation combining automated analysis with structured input and domain
                expertise.
              </div>
              <ul className="text-sm text-white/70 space-y-2 list-disc pl-5">
                <li>Layer 1 + 2: Automated analysis</li>
                <li>Layer 3: Structured business input</li>
              </ul>
            </div>

            <div className={`${tierBase} border-[#8efcff]/[0.34] bg-gradient-to-b from-[#0e6f84]/[0.84] to-[#0a4e5f]/[0.82]`}>
              <div className="text-lg font-semibold text-white mb-2">Full Evaluation</div>
              <div className="text-sm text-white/86 mb-5">
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
            <a
              href={EXTERNAL_EVAL_URL}
              className="inline-flex items-center justify-center rounded-full border border-white/[0.24] bg-white/[0.08] px-12 py-4 text-sm font-semibold text-white/84 hover:bg-white/[0.14] transition-colors"
            >
              Continue to Full Evaluation
            </a>
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}
