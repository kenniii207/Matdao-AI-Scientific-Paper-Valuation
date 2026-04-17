'use client';

import anime from 'animejs';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { forwardRef, MouseEvent, useRef, type ComponentProps } from 'react';
import type { UrlObject } from 'url';
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion';

type AnimatedRouteLinkProps = ComponentProps<typeof Link> & {
  transitionDelayMs?: number;
};

function resolveHrefString(href: string | UrlObject): string {
  if (typeof href === 'string') return href;
  const pathname = href.pathname || '';
  const query = href.query
    ? `?${new URLSearchParams(
        Object.entries(href.query).reduce<Record<string, string>>((acc, [k, v]) => {
          if (v === undefined) return acc;
          acc[k] = String(v);
          return acc;
        }, {})
      ).toString()}`
    : '';
  const hash = href.hash ? `#${href.hash}` : '';
  return `${pathname}${query}${hash}`;
}

export const AnimatedRouteLink = forwardRef<HTMLAnchorElement, AnimatedRouteLinkProps>(
  function AnimatedRouteLink({ href, onClick, transitionDelayMs = 220, ...props }, ref) {
    const router = useRouter();
    const anchorRef = useRef<HTMLAnchorElement | null>(null);
    const reducedMotion = usePrefersReducedMotion();

    const assignRef = (node: HTMLAnchorElement | null) => {
      anchorRef.current = node;
      if (!ref) return;
      if (typeof ref === 'function') {
        ref(node);
      } else {
        ref.current = node;
      }
    };

    const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
      onClick?.(event);
      if (event.defaultPrevented) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;

      event.preventDefault();
      const hrefValue = resolveHrefString(href);
      const rect = anchorRef.current?.getBoundingClientRect();

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

      if (reducedMotion) {
        router.push(hrefValue);
        return;
      }

      if (anchorRef.current) {
        anime.remove(anchorRef.current);
        anime({
          targets: anchorRef.current,
          scale: [1, 0.97, 1.015],
          duration: transitionDelayMs,
          easing: 'easeInOutQuad',
        });
      }

      window.setTimeout(() => router.push(hrefValue), transitionDelayMs);
    };

    return <Link ref={assignRef} href={href} {...props} onClick={handleClick} />;
  }
);
