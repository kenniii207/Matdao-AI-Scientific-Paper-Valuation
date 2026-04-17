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
  intent?: 'evaluate' | 'strength' | 'industry';
  badgeText: string;
  badgeColor: string;
  title: string;
  description: string;
  ctaText: string;
  ctaHref?: string;
  imageUrl: string;
}

type CardGradient = NonNullable<GradientCardProps['gradient']>;
type CardIntent = NonNullable<GradientCardProps['intent']>;

const vectorPalette: Record<CardGradient, { stroke: string; fill: string; glow: string }> = {
  orange: {
    stroke: 'rgba(255, 196, 143, 0.98)',
    fill: 'rgba(255, 203, 156, 0.24)',
    glow: 'rgba(255, 171, 97, 0.42)',
  },
  gray: {
    stroke: 'rgba(183, 244, 255, 0.98)',
    fill: 'rgba(141, 219, 246, 0.22)',
    glow: 'rgba(110, 252, 255, 0.4)',
  },
  purple: {
    stroke: 'rgba(199, 178, 255, 0.98)',
    fill: 'rgba(181, 162, 255, 0.23)',
    glow: 'rgba(167, 123, 255, 0.4)',
  },
  green: {
    stroke: 'rgba(162, 255, 221, 0.98)',
    fill: 'rgba(137, 236, 201, 0.22)',
    glow: 'rgba(93, 248, 205, 0.38)',
  },
};

const gradientToIntent: Record<CardGradient, CardIntent> = {
  orange: 'evaluate',
  gray: 'strength',
  purple: 'industry',
  green: 'evaluate',
};

const GradientCard = React.forwardRef<HTMLDivElement, GradientCardProps>(
  ({ className, gradient, intent, badgeText, badgeColor, title, description, ctaText, ctaHref, imageUrl, ...props }, ref) => {
    const resolvedGradient = (gradient ?? 'gray') as CardGradient;
    const resolvedIntent = intent ?? gradientToIntent[resolvedGradient];
    const vector = vectorPalette[resolvedGradient];

    const cardAnimation = {
      rest: { scale: 1, y: 0 },
      hover: { scale: 1.015, y: -4 },
    };

    const backgroundImageAnimation = {
      rest: { scale: 1, rotate: 0 },
      hover: { scale: 1.08, rotate: 0 },
    };

    const vectorWrapAnimation = {
      rest: { y: 20, scale: 0.9, opacity: 0.66, rotate: -6 },
      hover: { y: 0, scale: 1.05, opacity: 1, rotate: 0 },
    };

    const vectorPathAnimation = {
      rest: { pathLength: 0.62, opacity: 0.74 },
      hover: { pathLength: 1, opacity: 1 },
    };

    const renderIntentVector = () => {
      if (resolvedIntent === 'strength') {
        return (
          <motion.svg
            viewBox="0 0 220 220"
            className="relative h-full w-full drop-shadow-[0_0_14px_rgba(0,0,0,0.35)]"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {[0, 1, 2, 3].map((idx) => (
              <motion.rect
                key={idx}
                x={46 + idx * 34}
                y={122 - idx * 20}
                width="20"
                height={28 + idx * 20}
                rx="6"
                fill={vector.fill}
                stroke={vector.stroke}
                strokeWidth="2.6"
                variants={{ rest: { scaleY: 0.86 }, hover: { scaleY: 1.08 } }}
                transition={{ type: 'spring', stiffness: 220, damping: 16, delay: idx * 0.04 }}
                style={{ transformOrigin: '50% 100%' }}
              />
            ))}
            <motion.path
              d="M36 166C72 148 110 130 182 92"
              stroke={vector.stroke}
              strokeWidth="4.2"
              strokeLinecap="round"
              variants={vectorPathAnimation}
              transition={{ duration: 0.46, ease: 'easeOut' }}
            />
          </motion.svg>
        );
      }

      if (resolvedIntent === 'industry') {
        return (
          <motion.svg
            viewBox="0 0 220 220"
            className="relative h-full w-full drop-shadow-[0_0_14px_rgba(0,0,0,0.35)]"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <motion.path
              d="M42 162L90 122L130 142L178 94"
              stroke={vector.stroke}
              strokeWidth="4.6"
              strokeLinecap="round"
              variants={vectorPathAnimation}
              transition={{ duration: 0.45, ease: 'easeOut' }}
            />
            {[{ x: 42, y: 162, r: 10 }, { x: 90, y: 122, r: 13 }, { x: 130, y: 142, r: 9 }, { x: 178, y: 94, r: 16 }].map((node, idx) => (
              <motion.circle
                key={`${node.x}-${node.y}`}
                cx={node.x}
                cy={node.y}
                r={node.r}
                fill={vector.fill}
                stroke={vector.stroke}
                strokeWidth="2.8"
                variants={{ rest: { scale: 0.9 }, hover: { scale: 1.12 } }}
                transition={{ type: 'spring', stiffness: 220, damping: 16, delay: idx * 0.05 }}
              />
            ))}
          </motion.svg>
        );
      }

      return (
        <motion.svg
          viewBox="0 0 220 220"
          className="relative h-full w-full drop-shadow-[0_0_14px_rgba(0,0,0,0.35)]"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <motion.circle
            cx="124"
            cy="104"
            r="34"
            stroke={vector.stroke}
            strokeWidth="4.6"
            variants={vectorPathAnimation}
            transition={{ duration: 0.45, ease: 'easeOut' }}
          />
          {[0, 1, 2].map((idx) => (
            <motion.circle
              key={idx}
              cx={72 + idx * 40}
              cy={154 - (idx % 2) * 28}
              r={idx === 1 ? 11 : 8}
              fill={vector.fill}
              stroke={vector.stroke}
              strokeWidth="2.6"
              variants={{ rest: { scale: 0.88 }, hover: { scale: 1.1 } }}
              transition={{ type: 'spring', stiffness: 220, damping: 16, delay: idx * 0.05 }}
            />
          ))}
          <motion.path
            d="M78 150L102 126L126 150L148 122"
            stroke={vector.stroke}
            strokeWidth="3.6"
            strokeLinecap="round"
            variants={vectorPathAnimation}
            transition={{ duration: 0.52, ease: 'easeOut' }}
          />
        </motion.svg>
      );
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
            variants={backgroundImageAnimation}
            transition={{ type: 'spring', stiffness: 340, damping: 18 }}
            className="absolute inset-0 h-full w-full object-cover pointer-events-none opacity-[0.72]"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-black/[0.1] via-black/[0.44] to-black/[0.84] pointer-events-none" />

          <motion.div
            variants={vectorWrapAnimation}
            transition={{ type: 'spring', stiffness: 240, damping: 18 }}
            className="absolute -right-3 -bottom-3 h-36 w-36 pointer-events-none z-[1]"
          >
            <div
              className="absolute inset-0 rounded-full blur-2xl"
              style={{ backgroundColor: vector.glow }}
            />
            {renderIntentVector()}
          </motion.div>

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
