'use client';

import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import gsap from 'gsap';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';
import type { ReactNode } from 'react';

export default function RouteTransitionShell({ children }: { children: ReactNode }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const pathname = usePathname();
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    if (reducedMotion) return;
    if (!containerRef.current) return;

    const ctx = gsap.context(() => {
      const targets = containerRef.current?.querySelectorAll('[data-route-item]');
      if (!targets || targets.length === 0) {
        gsap.fromTo(
          containerRef.current,
          { autoAlpha: 0.65 },
          { autoAlpha: 1, duration: 0.34, ease: 'power1.out' }
        );
        return;
      }
      const limitedTargets = Array.from(targets).slice(0, 14);

      gsap.fromTo(
        limitedTargets,
        { autoAlpha: 0, y: 18 },
        {
          autoAlpha: 1,
          y: 0,
          duration: 0.52,
          ease: 'power2.out',
          stagger: 0.06,
          clearProps: 'all',
        }
      );
    }, containerRef);

    return () => ctx.revert();
  }, [pathname, reducedMotion]);

  return <div ref={containerRef}>{children}</div>;
}
