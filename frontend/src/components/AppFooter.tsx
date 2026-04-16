import Link from 'next/link';

export default function AppFooter() {
  return (
    <footer className="mt-auto py-10 border-t border-outline-variant/10">
      <div className="max-w-7xl mx-auto px-6 md:px-8 flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] font-label uppercase tracking-widest text-on-surface-variant/50">
        <div>© 2026 MatDAO Precision Research</div>
        <div className="flex gap-6">
          <Link className="hover:text-primary-fixed transition-colors" href="/">
            Methodology
          </Link>
          <Link className="hover:text-primary-fixed transition-colors" href="/">
            Privacy
          </Link>
          <Link className="hover:text-primary-fixed transition-colors" href="/upsell">
            Accuracy Tiers
          </Link>
        </div>
      </div>
    </footer>
  );
}

