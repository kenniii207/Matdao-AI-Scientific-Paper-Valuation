'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import gsap from 'gsap';
import AppFooter from '@/components/AppFooter';
import AppHeader from '@/components/AppHeader';
import { AnimatedRouteLink } from '@/components/AnimatedRouteLink';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';
import { TypeAnimation } from 'react-type-animation';
import { GradientCard } from '@/components/ui/gradient-card';
import { LiquidButton } from '@/components/ui/liquid-glass-button';

const ShaderBackground = dynamic(
  () => import('@/components/ui/shader-background'),
  { ssr: false }
);

type IntentCard = {
  intent: 'evaluate' | 'strength' | 'industry';
  href: string;
  badgeText: string;
  badgeColor: string;
  title: string;
  description: string;
  ctaText: string;
  gradient: 'orange' | 'gray' | 'purple' | 'green';
  imageUrl: string;
};

export default function Home() {
  const [activeIntent, setActiveIntent] = useState<string | null>(null);
  const heroRef = useRef<HTMLDivElement | null>(null);
  const reducedMotion = usePrefersReducedMotion();
  const router = useRouter();

  const cards = useMemo<IntentCard[]>(
    () => [
      {
        intent: 'evaluate',
        href: '/submit?intent=evaluate',
        badgeText: 'Prototype pick',
        badgeColor: '#f59e0b',
        title: 'Evaluate my research',
        description: 'Run structured due diligence from extraction to integrity gate with evidence traces.',
        ctaText: 'Start evaluation',
        gradient: 'orange',
        imageUrl:
          'https://images.unsplash.com/photo-1581092335397-9583eb92d232?auto=format&fit=crop&w=900&q=80',
      },
      {
        intent: 'strength',
        href: '/submit?intent=strength',
        badgeText: 'Signal check',
        badgeColor: '#64748b',
        title: "See my research's strength",
        description: 'Benchmark quality, defensibility, and investment confidence against market expectations.',
        ctaText: 'Benchmark now',
        gradient: 'gray',
        imageUrl:
          'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80',
      },
      {
        intent: 'industry',
        href: '/submit?intent=industry',
        badgeText: 'Market fit',
        badgeColor: '#8b5cf6',
        title: 'Find industry/investor fit',
        description: 'Match your paper with demand signals, investor interest, and strategic partner pathways.',
        ctaText: 'Map demand',
        gradient: 'purple',
        imageUrl:
          'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
      },
    ],
    []
  );

  useEffect(() => {
    if (reducedMotion || !heroRef.current) return;
    const ctx = gsap.context(() => {
      const timeline = gsap.timeline({ defaults: { ease: 'power2.out' } });
      timeline
        .from('.landing-intro', { y: 18, autoAlpha: 0, duration: 0.34 })
        .from('.landing-title', { y: 16, autoAlpha: 0, duration: 0.38 }, '-=0.18')
        .from('.landing-subcopy', { y: 12, autoAlpha: 0, duration: 0.32 }, '-=0.2')
        .from('.landing-card', { y: 20, autoAlpha: 0, duration: 0.42, stagger: 0.08 }, '-=0.06')
        .from('.landing-cta', { y: 12, autoAlpha: 0, duration: 0.3 }, '-=0.22');
    }, heroRef);
    return () => ctx.revert();
  }, [reducedMotion]);

  const navigateWithPulse = (href: string, eventTarget?: HTMLElement | null) => {
    const rect = eventTarget?.getBoundingClientRect();
    if (typeof window !== 'undefined' && rect) {
      window.dispatchEvent(
        new CustomEvent('matdao:navigate', {
          detail: {
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2,
          },
        })
      );
    }
    window.setTimeout(() => router.push(href), reducedMotion ? 0 : 170);
  };

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden bg-black/10">
      <div className="relative z-20">
        <AppHeader />
      </div>

      {!reducedMotion ? <ShaderBackground /> : null}

      <main className="flex-grow z-10 relative px-5 sm:px-6 py-12 md:py-16">
        <div className="absolute inset-0 pointer-events-none z-[-1]">
          {/* Subtle vignette or blur can be kept, but fully transparent center to let shader show */ }
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/30" />
          <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[900px] h-[900px] bg-cyan-300/10 rounded-full blur-[150px]" />
          <div className="absolute bottom-[-18%] right-[4%] w-[560px] h-[560px] bg-indigo-500/10 rounded-full blur-[160px]" />
        </div>

        <div ref={heroRef} className="relative z-10 w-full max-w-6xl mx-auto">
          <div className="text-center mb-8 md:mb-10" data-route-item>
            <p className="landing-intro mb-4 inline-flex items-center rounded-full border border-[#6efcff]/35 bg-[#6efcff]/10 px-4 py-1 text-[11px] uppercase tracking-[0.18em] text-[#c5fdff]">
              4-Layer Scientific Due Diligence
            </p>
            <h1 className="landing-title font-headline text-4xl md:text-6xl font-extrabold tracking-tight text-white/95 mb-3 flex flex-col items-center justify-center min-h-[90px] md:min-h-[120px]">
              <span>Select your <TypeAnimation
                sequence={[
                  'intention',
                  3000,
                  'direction',
                  3000,
                  'strategy',
                  3000,
                  'pathway',
                  3000,
                ]}
                wrapper="span"
                speed={50}
                repeat={Infinity}
                className="text-[#89fdff]"
              /></span>
            </h1>
            <p className="landing-subcopy text-white/70 font-body max-w-2xl mx-auto text-sm md:text-lg">
              Start from one pathway and we&apos;ll guide you from evidence extraction to decision-ready scoring.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 mb-12 md:mb-14" data-route-item>
            {cards.map((card) => (
              <button
                key={card.intent}
                type="button"
                className={`landing-card group text-left focus-glow rounded-2xl ${
                  activeIntent && activeIntent !== card.intent ? 'opacity-70' : 'opacity-100'
                }`}
                onMouseEnter={() => setActiveIntent(card.intent)}
                onFocus={() => setActiveIntent(card.intent)}
                onMouseLeave={() => setActiveIntent((prev) => (prev === card.intent ? null : prev))}
                onBlur={() => setActiveIntent((prev) => (prev === card.intent ? null : prev))}
                onClick={(e) => navigateWithPulse(card.href, e.currentTarget)}
              >
                <GradientCard
                  badgeText={card.badgeText}
                  badgeColor={card.badgeColor}
                  title={card.title}
                  description={card.description}
                  ctaText={card.ctaText}
                  gradient={card.gradient}
                  imageUrl={card.imageUrl}
                  className={`h-[260px] md:h-[280px] transition-all duration-500 ease-out delay-75 ${
                    activeIntent === card.intent
                      ? 'ring-1 ring-[#89fdff]/30 shadow-[0_8px_32px_rgba(110,252,255,0.08)]'
                      : 'ring-1 ring-white/5'
                  }`}
                />
              </button>
            ))}
          </div>

          <div className="flex flex-col items-center gap-5" data-route-item>
            <AnimatedRouteLink
              href={activeIntent ? `/submit?intent=${encodeURIComponent(activeIntent)}` : '/submit'}
              className="landing-cta inline-flex"
            >
              <LiquidButton size="xl" className="text-white border rounded-full px-10">
                {activeIntent ? `Continue with ${activeIntent}` : 'Start Prototype Evaluation'}
              </LiquidButton>
            </AnimatedRouteLink>

            <div className="grid w-full max-w-3xl grid-cols-1 sm:grid-cols-3 gap-3 text-left">
              {[
                { label: 'Layer 1', text: 'NLP extraction from paper evidence' },
                { label: 'Layer 2', text: 'API enrichment from trusted sources' },
                { label: 'Integrity Gate', text: 'Dim9 = 1 forces total score to 0' },
              ].map((item) => (
                <div key={item.label} className="rounded-xl border border-white/15 bg-white/[0.04] px-4 py-3 text-xs text-white/70 backdrop-blur-sm">
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#b8fcff]">{item.label}</div>
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
