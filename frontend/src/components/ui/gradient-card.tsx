'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const cardVariants = cva(
  'relative flex flex-col justify-between h-full w-full overflow-hidden rounded-2xl p-8 shadow-sm transition-shadow duration-300 hover:shadow-lg border border-white/15',
  {
    variants: {
      gradient: {
        orange: 'bg-gradient-to-br from-orange-100/95 to-amber-200/65',
        gray: 'bg-gradient-to-br from-slate-100/95 to-slate-200/65',
        purple: 'bg-gradient-to-br from-purple-100/95 to-indigo-200/65',
        green: 'bg-gradient-to-br from-emerald-100/95 to-teal-200/65',
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
      <motion.div variants={cardAnimation} initial="rest" whileHover="hover" animate="rest" className="h-full" ref={ref}>
        <div className={cn(cardVariants({ gradient }), className)} {...props}>
          <motion.img
            src={imageUrl}
            alt={`${title} background graphic`}
            variants={imageAnimation}
            transition={{ type: 'spring', stiffness: 340, damping: 18 }}
            className="absolute -right-1/4 -bottom-1/4 w-3/4 opacity-80 pointer-events-none dark:opacity-30"
          />

          <div className="z-10 flex flex-col h-full">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-background/55 px-3 py-1 text-sm font-medium text-foreground/80 backdrop-blur-sm w-fit">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: badgeColor }} />
              {badgeText}
            </div>

            <div className="flex-grow">
              <h3 className="text-2xl font-bold text-foreground mb-2">{title}</h3>
              <p className="text-foreground/70 max-w-xs">{description}</p>
            </div>

            {ctaHref ? (
              <a href={ctaHref} className="group mt-6 inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                {ctaText}
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </a>
            ) : (
              <div className="group mt-6 inline-flex items-center gap-2 text-sm font-semibold text-foreground">
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
