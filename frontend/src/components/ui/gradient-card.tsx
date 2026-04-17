'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const cardVariants = cva(
  'relative flex flex-col justify-between h-full w-full overflow-hidden rounded-2xl p-8 border border-[#c8f9ff]/[0.28] backdrop-blur-sm shadow-[0_14px_36px_rgba(0,0,0,0.42)] transition-shadow duration-300 hover:shadow-[0_20px_42px_rgba(0,0,0,0.48)]',
  {
    variants: {
      gradient: {
        orange: 'bg-gradient-to-br from-[#24170d]/[0.96] via-[#2a1a0d]/[0.95] to-[#2f1d0e]/[0.93]',
        gray: 'bg-gradient-to-br from-[#131a25]/[0.96] via-[#192232]/[0.95] to-[#1d2739]/[0.93]',
        purple: 'bg-gradient-to-br from-[#1b1328]/[0.96] via-[#231a34]/[0.95] to-[#2b1f40]/[0.93]',
        green: 'bg-gradient-to-br from-[#12241f]/[0.96] via-[#17302a]/[0.95] to-[#1a3a33]/[0.93]',
      },
    },
    defaultVariants: {
      gradient: 'gray',
    },
  }
);

export interface GradientCardProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {
  badgeText: string;
  badgeColor: string;
  title: string;
  description: string;
  ctaText: string;
  ctaHref?: string;
  imageUrl: string;
}

const GradientCard = React.forwardRef<HTMLDivElement, GradientCardProps>(
  ({ className, gradient, badgeText, badgeColor, title, description, ctaText, ctaHref, imageUrl, ...props }, ref) => {
    const cardAnimation = {
      rest: { scale: 1, y: 0 },
      hover: { scale: 1.015, y: -4 },
    };

    const imageAnimation = {
      rest: { scale: 1, rotate: 0 },
      hover: { scale: 1.06, rotate: 2 },
    };

    return (
      <motion.div 
        variants={cardAnimation} 
        initial="rest" 
        whileHover="hover" 
        animate="rest" 
        className="h-full" 
        ref={ref}
        transition={{ type: 'spring', stiffness: 100, damping: 20 }}
      >
        <div className={cn(cardVariants({ gradient }), className)} {...props}>
          <motion.img
            src={imageUrl}
            alt={`${title} background graphic`}
            variants={imageAnimation}
            transition={{ type: 'spring', stiffness: 340, damping: 18 }}
            className="absolute -right-1/4 -bottom-1/4 w-3/4 opacity-35 pointer-events-none mix-blend-screen dark:opacity-25"
          />

          <div className="z-10 flex flex-col h-full">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/40 px-3 py-1 text-sm font-medium text-white/80 backdrop-blur-sm w-fit">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: badgeColor }} />
              {badgeText}
            </div>

            <div className="flex-grow">
              <h3 className="text-2xl font-bold text-white/92 mb-2">{title}</h3>
              <p className="text-white/64 max-w-xs">{description}</p>
            </div>

            {ctaHref ? (
              <a href={ctaHref} className="group mt-6 inline-flex items-center gap-2 text-sm font-semibold text-white/84">
                {ctaText}
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </a>
            ) : (
              <div className="group mt-6 inline-flex items-center gap-2 text-sm font-semibold text-white/84">
                {ctaText}
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </div>
            )}
          </div>
        </div>
      </motion.div>
    );
  }
);
GradientCard.displayName = 'GradientCard';

export { GradientCard, cardVariants };
