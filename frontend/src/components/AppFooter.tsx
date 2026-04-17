import { AnimatedRouteLink } from '@/components/AnimatedRouteLink';

export default function AppFooter() {
  return (
    <footer className="mt-auto py-10 border-t border-white/[0.1] bg-black/[0.36] backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-6 md:px-8 flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] font-label uppercase tracking-widest text-white/50">
        <div>© 2026 MatDAO Precision Research</div>
        <div className="flex gap-6">
          <AnimatedRouteLink className="hover:text-[#b6fcff] transition-colors" href="/">
            Methodology
          </AnimatedRouteLink>
          <AnimatedRouteLink className="hover:text-[#b6fcff] transition-colors" href="/">
            Privacy
          </AnimatedRouteLink>
          <AnimatedRouteLink className="hover:text-[#b6fcff] transition-colors" href="/upsell">
            Accuracy Tiers
          </AnimatedRouteLink>
        </div>
      </div>
    </footer>
  );
}
