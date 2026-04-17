'use client';

import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';

type NavigationPulseEvent = CustomEvent<{ x: number; y: number }>;

export default function RoutePulseOverlay() {
  const pulseRef = useRef<HTMLDivElement | null>(null);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    if (reducedMotion) return;

    const handleNavigate = (event: Event) => {
      const target = pulseRef.current;
      if (!target) return;
      const detail = (event as NavigationPulseEvent).detail;
      if (!detail) return;

      gsap.killTweensOf(target);
      gsap.set(target, {
        display: 'block',
        x: detail.x,
        y: detail.y,
        scale: 0.2,
        opacity: 0.55,
      });

      gsap.to(target, {
        scale: 6.8,
        opacity: 0,
        duration: 0.5,
        ease: 'power2.out',
        onComplete: () => {
          gsap.set(target, { display: 'none' });
        },
      });
    };

    window.addEventListener('matdao:navigate', handleNavigate);
    return () => window.removeEventListener('matdao:navigate', handleNavigate);
  }, [reducedMotion]);

  return (
    <div className="pointer-events-none fixed inset-0 z-[70] overflow-hidden">
      <div
        ref={pulseRef}
        className="hidden h-12 w-12 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#8bf9ff]/70 bg-[#63f7ff]/25 will-change-transform"
      />
    </div>
  );
}
