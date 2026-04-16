'use client';

import Link from 'next/link';
import AppFooter from '@/components/AppFooter';
import AppHeader from '@/components/AppHeader';

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden">
      <AppHeader />

      <main className="flex-grow flex flex-col items-center justify-center px-6 py-16 relative bg-black">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-b from-black via-black to-black" />
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[760px] h-[760px] bg-white/5 rounded-full blur-[140px]" />
        </div>

        <div className="w-full max-w-6xl z-10">
          <div className="text-center mb-14">
            <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight text-on-surface mb-3">
              Let us know your intention
            </h1>
            <p className="text-on-surface/40 font-body max-w-xl mx-auto text-base md:text-lg">
              Select objective that best matches your current research phase.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10 mb-14 place-items-center">
            {[
              {
                href: '/submit?intent=evaluate',
                title: 'Evaluate my research',
                subtitle: 'Get a structured analysis',
                badge: 'Prototype pick',
                featured: true,
                img:
                  'https://lh3.googleusercontent.com/aida-public/AB6AXuCzQaUkDkntfzTO-mUoBbPeAB6rHEPnn2qm12gP_CVDfspRVSYthP4I8XOoXa5d_Z-mt8fvxxDhakwKY7sCGp2XWCX_OQo4DrmfNvN43rht9fcBHzE_lvnTAcLE-FbJaLdy8YnBFaQqSnjU_JPJ6PZsdui84ecePiiXq2Y6_DQ8TlKrLuobdhcUSaQZB99DIbnxhws3NLFIrNxKF7dYgDPOaXWTwQAEIcIbm3iC73YcmRw_N3cE2cG20CE1LXNNul0RDy8t751GIaxV',
              },
              {
                href: '/submit?intent=strength',
                title: "See my research's strength",
                subtitle: 'Benchmark your research',
                featured: false,
                img:
                  'https://lh3.googleusercontent.com/aida-public/AB6AXuDcl_ULqgmwjkZEQDo_Xz4qBLsVoxrqfl3daLHqKPdhf4-XZrwoktlHBbygSNy_4cu9_5LdnVV1TfJfjfm1H2y0YlNkeRKqMeH6FQ_qEyS7naZXAGui6YBUS3wGDp1gLKffS9Sm6tTiw-XhlXXHn8BUbfmGJTPHJd3ogzlCpIET0JfDarPzw5pwXJjobKId3L9dido5gtovXc_RcI2w1SF7p1dtkzc4_iueTaCjs-fZI9OBWrJMJG1tckA8xY15j1PCZCVexeHHRGYW',
              },
              {
                href: '/submit?intent=industry',
                title: 'Find industry/investor',
                subtitle: 'Match research with real demand',
                featured: false,
                img:
                  'https://lh3.googleusercontent.com/aida-public/AB6AXuClHus9jfMYaSOO2J4U5HSTgh3aaNUutWCwSaAlsMBGNGN1r_w2fIRuTXj1iDQmcqZaRaa7GIZClUY23gYsrWEN8hZdgAA6nhUseTNiodRI3Mf-nEhb-iWJWf70R-mtO0opsucKQEPkymgGoLrya0-WWKKxT8a0OTmol8P_OkAUGxUKViNE-oqbUqQizIuoh1S8hkBALgIPegyR_zXtOxLOXfeeuIWbhsRo9x1zUfLp2agzAfCblejEuq3NBrdeFnndLB7LCdxIRT8c',
              },
            ].map((c) => (
              <Link key={c.title} href={c.href} className="group w-[270px] md:w-[290px]">
                <div
                  className={`relative h-[220px] rounded-2xl overflow-hidden border bg-black/40 transition-all duration-300 ${
                    c.featured
                      ? 'border-[#6efcff]/45 shadow-[0_0_28px_rgba(110,252,255,0.2)] group-hover:shadow-[0_0_36px_rgba(110,252,255,0.3)]'
                      : 'border-white/10 group-hover:border-white/20'
                  }`}
                  style={{
                    backgroundImage: `url(${c.img})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                  }}
                >
                  {c.featured && c.badge ? (
                    <div className="absolute top-3 left-3 rounded-full border border-[#6efcff]/50 bg-black/60 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#c5feff]">
                      {c.badge}
                    </div>
                  ) : null}
                  <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-black/10" />
                  <div className="absolute inset-0 bg-black/10" />
                  <div className="absolute bottom-0 left-0 right-0 p-5">
                    <div className={`text-sm font-semibold ${c.featured ? 'text-[#dcfeff]' : 'text-white'}`}>
                      {c.title}
                    </div>
                    <div className="text-xs text-white/50 mt-1">{c.subtitle}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          <div className="flex flex-col items-center">
            <Link
              href="/submit"
              className="rounded-full border border-[#6efcff]/45 bg-[#6efcff]/15 px-12 py-4 text-sm font-semibold text-[#d4feff] hover:bg-[#6efcff]/25 transition-colors shadow-[0_0_20px_rgba(110,252,255,0.2)]"
            >
              Start Prototype Evaluation
            </Link>
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}
