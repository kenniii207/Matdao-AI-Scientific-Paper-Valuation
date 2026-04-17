'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import gsap from 'gsap';
import AppFooter from '@/components/AppFooter';
import AppHeader from '@/components/AppHeader';
import { AnimatedRouteLink } from '@/components/AnimatedRouteLink';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';

export default function Home() {
  const [activeIntent, setActiveIntent] = useState<string | null>(null);
  const heroRef = useRef<HTMLDivElement | null>(null);
  const reducedMotion = usePrefersReducedMotion();
  const cards = useMemo(
    () => [
      {
        intent: 'evaluate',
        href: '/submit?intent=evaluate',
        title: 'Evaluate my research',
        subtitle: 'Get a structured analysis',
        badge: 'Prototype pick',
        featured: true,
        img:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCzQaUkDkntfzTO-mUoBbPeAB6rHEPnn2qm12gP_CVDfspRVSYthP4I8XOoXa5d_Z-mt8fvxxDhakwKY7sCGp2XWCX_OQo4DrmfNvN43rht9fcBHzE_lvnTAcLE-FbJaLdy8YnBFaQqSnjU_JPJ6PZsdui84ecePiiXq2Y6_DQ8TlKrLuobdhcUSaQZB99DIbnxhws3NLFIrNxKF7dYgDPOaXWTwQAEIcIbm3iC73YcmRw_N3cE2cG20CE1LXNNul0RDy8t751GIaxV',
      },
      {
        intent: 'strength',
        href: '/submit?intent=strength',
        title: "See my research's strength",
        subtitle: 'Benchmark your research',
        featured: false,
        img:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDcl_ULqgmwjkZEQDo_Xz4qBLsVoxrqfl3daLHqKPdhf4-XZrwoktlHBbygSNy_4cu9_5LdnVV1TfJfjfm1H2y0YlNkeRKqMeH6FQ_qEyS7naZXAGui6YBUS3wGDp1gLKffS9Sm6tTiw-XhlXXHn8BUbfmGJTPHJd3ogzlCpIET0JfDarPzw5pwXJjobKId3L9dido5gtovXc_RcI2w1SF7p1dtkzc4_iueTaCjs-fZI9OBWrJMJG1tckA8xY15j1PCZCVexeHHRGYW',
      },
      {
        intent: 'industry',
        href: '/submit?intent=industry',
        title: 'Find industry/investor',
        subtitle: 'Match research with real demand',
        featured: false,
        img:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuClHus9jfMYaSOO2J4U5HSTgh3aaNUutWCwSaAlsMBGNGN1r_w2fIRuTXj1iDQmcqZaRaa7GIZClUY23gYsrWEN8hZdgAA6nhUseTNiodRI3Mf-nEhb-iWJWf70R-mtO0opsucKQEPkymgGoLrya0-WWKKxT8a0OTmol8P_OkAUGxUKViNE-oqbUqQizIuoh1S8hkBALgIPegyR_zXtOxLOXfeeuIWbhsRo9x1zUfLp2agzAfCblejEuq3NBrdeFnndLB7LCdxIRT8c',
      },
    ],
    []
  );

  useEffect(() => {
    if (reducedMotion || !heroRef.current) return;
    const ctx = gsap.context(() => {
      const timeline = gsap.timeline({ defaults: { ease: 'power2.out' } });
      timeline
        .from('.landing-intro', { y: 22, autoAlpha: 0, duration: 0.45 })
        .from('.landing-subcopy', { y: 16, autoAlpha: 0, duration: 0.4 }, '-=0.2')
        .from('.landing-card', { y: 20, duration: 0.42, stagger: 0.08 }, '-=0.08')
        .from('.landing-cta', { y: 14, autoAlpha: 0, duration: 0.34 }, '-=0.26')
        .from('.landing-strip', { y: 14, autoAlpha: 0, duration: 0.32 }, '-=0.2');
    }, heroRef);
    return () => ctx.revert();
  }, [reducedMotion]);

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden">
      <AppHeader />

      <main className="flex-grow flex flex-col items-center justify-center px-5 sm:px-6 py-12 md:py-16 relative bg-black">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-b from-black via-black to-black" />
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[760px] h-[760px] bg-white/5 rounded-full blur-[140px]" />
          <div className="floating-aurora absolute top-[18%] left-[16%] w-[260px] h-[260px] bg-[#6efcff]/10 rounded-full blur-[90px]" />
          <div className="floating-aurora floating-aurora-delay absolute bottom-[12%] right-[14%] w-[300px] h-[300px] bg-cyan-400/10 rounded-full blur-[95px]" />
        </div>

        <div ref={heroRef} className="w-full max-w-6xl z-10">
          <div className="text-center mb-10 md:mb-14" data-route-item>
            <p className="landing-intro mb-4 inline-flex items-center rounded-full border border-[#6efcff]/35 bg-[#6efcff]/10 px-4 py-1 text-[11px] uppercase tracking-[0.18em] text-[#c5fdff]">
              4-Layer Scientific Due Diligence
            </p>
            <h1 className="font-headline text-4xl md:text-5xl font-extrabold tracking-tight text-on-surface mb-3">
              Let us know your intention
            </h1>
            <p className="landing-subcopy text-on-surface/40 font-body max-w-xl mx-auto text-base md:text-lg">
              Select objective that best matches your current research phase.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-10 mb-12 md:mb-14 place-items-center">
            {cards.map((c) => (
              <AnimatedRouteLink
                key={c.title}
                href={c.href}
                className={`landing-card group w-full max-w-[320px] md:w-[290px] focus-glow rounded-2xl transition-opacity ${
                  activeIntent && activeIntent !== c.intent ? 'opacity-75' : 'opacity-100'
                }`}
                onMouseEnter={() => setActiveIntent(c.intent)}
                onFocus={() => setActiveIntent(c.intent)}
                onMouseLeave={() => setActiveIntent((prev) => (prev === c.intent ? null : prev))}
                onBlur={() => setActiveIntent((prev) => (prev === c.intent ? null : prev))}
                onClick={() => setActiveIntent(c.intent)}
              >
                <div
                  className={`intent-card relative h-[210px] md:h-[220px] rounded-2xl overflow-hidden border bg-black/40 ${
                    c.featured || activeIntent === c.intent ? 'intent-card--active' : 'intent-card--idle'
                  }`}
                  style={{
                    backgroundImage: `url(${c.img})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                  }}
                >
                  <div className="intent-card__shine" />
                  <div className={`intent-card__pulse ${activeIntent === c.intent ? 'opacity-100' : 'opacity-0'}`} />
                  {c.featured && c.badge ? (
                    <div className="absolute top-3 left-3 rounded-full border border-[#6efcff]/50 bg-black/60 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#c5feff] backdrop-blur">
                      {c.badge}
                    </div>
                  ) : null}
                  <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-black/10" />
                  <div className="absolute inset-0 bg-black/10" />
                  <div className="absolute bottom-0 left-0 right-0 p-5">
                    <div
                      className={`text-sm md:text-[15px] font-semibold ${
                        c.featured || activeIntent === c.intent ? 'text-[#e9feff]' : 'text-white/95'
                      }`}
                    >
                      {c.title}
                    </div>
                    <div
                      className={`text-xs mt-1 ${
                        c.featured || activeIntent === c.intent ? 'text-[#b6edf0]' : 'text-white/60'
                      }`}
                    >
                      {c.subtitle}
                    </div>
                  </div>
                </div>
              </AnimatedRouteLink>
            ))}
          </div>

          <div className="flex flex-col items-center" data-route-item>
            <AnimatedRouteLink
              href={activeIntent ? `/submit?intent=${encodeURIComponent(activeIntent)}` : '/submit'}
              className="landing-cta cta-premium focus-glow rounded-full border border-[#6efcff]/45 bg-[#6efcff]/15 px-10 sm:px-12 py-4 text-sm font-semibold text-[#d4feff] hover:bg-[#6efcff]/25 shadow-[0_0_20px_rgba(110,252,255,0.2)]"
            >
              {activeIntent ? `Start ${activeIntent} flow` : 'Start Prototype Evaluation'}
            </AnimatedRouteLink>
            <div className="landing-strip mt-6 grid w-full max-w-3xl grid-cols-1 sm:grid-cols-3 gap-3 text-left">
              {[
                { label: 'Layer 1', text: 'NLP extraction from paper evidence' },
                { label: 'Layer 2', text: 'API enrichment from trusted sources' },
                { label: 'Integrity', text: 'Dim9 fail triggers score reset to 0' },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-xs text-white/55"
                >
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b8fcff]">
                    {item.label}
                  </div>
                  <div>{item.text}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <AppFooter />
    </div>
  );
}
