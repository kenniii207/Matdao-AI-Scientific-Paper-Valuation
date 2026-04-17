'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

interface MetricCardProps {
  id: number;
  name: string;
  percent: number;
  rawScore: number;
  rationale?: string;
  snippet?: string;
}

export function MetricCard({ id, name, percent, rationale, snippet }: MetricCardProps) {
  const [expanded, setExpanded] = useState(false);

  // SVG parameters
  const size = 64;
  const strokeWidth = 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Determine stroke color by score
  const getStrokeColor = (p: number) => {
    if (p >= 80) return 'stroke-[#6efcff]';
    if (p >= 60) return 'stroke-[#00dce5]';
    if (p >= 40) return 'stroke-yellow-400';
    return 'stroke-red-500';
  };

  return (
    <motion.div
      layout
      style={{ willChange: 'transform' }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.99 }}
      transition={{ duration: 0.2 }}
      className="interactive-lift border border-white/10 bg-black/40 backdrop-blur-md rounded-xl p-5 md:p-6 w-full flex flex-col justify-center cursor-pointer shadow-[0_4px_24px_rgba(0,0,0,0.2)] hover:border-white/20 hover:bg-black/50"
      onClick={() => setExpanded(!expanded)}
    >
      <motion.div layout className="flex items-center justify-between gap-4">
        <div className="flex-1">
          <motion.h3 layout className="text-white/80 text-sm md:text-base font-semibold">
            {name}
          </motion.h3>
          <motion.div layout className="text-[#6efcff]/80 text-xs mt-1 uppercase tracking-wider font-semibold">
            Score: {percent}/100
          </motion.div>
        </div>

        {/* Animated Circular Progress */}
        <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
          <svg width={size} height={size} className="transform -rotate-90">
            {/* Background ring */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke="rgba(255,255,255,0.1)"
              strokeWidth={strokeWidth}
              fill="transparent"
            />
            {/* Progress ring */}
            <motion.circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              className={cn("transition-colors duration-500", getStrokeColor(percent))}
              strokeWidth={strokeWidth}
              fill="transparent"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: circumference - (percent / 100) * circumference }}
              transition={{ duration: 1.2, ease: "easeOut", delay: 0.1 }}
              strokeLinecap="round"
            />
          </svg>
          <motion.div layout className="absolute inset-0 flex items-center justify-center font-bold text-sm text-white drop-shadow-md">
            {percent}
          </motion.div>
        </div>
      </motion.div>

      {/* Accordion Expansion */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            layout
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="mt-6 pt-5 border-t border-white/10 flex flex-col gap-4">
              {rationale && (
                <div>
                  <h4 className="text-white/40 text-xs uppercase tracking-wider font-bold mb-1">Automated Rationale</h4>
                  <p className="text-white/70 text-sm leading-relaxed whitespace-pre-wrap">{rationale}</p>
                </div>
              )}
              {snippet && snippet !== '{}' && (
                <div>
                  <h4 className="text-white/40 text-xs uppercase tracking-wider font-bold mb-1">Origin Evidence</h4>
                  <p className="text-white/50 text-xs leading-relaxed font-mono bg-black/50 border border-white/10 rounded-md p-3 max-h-40 overflow-y-auto w-full break-words">
                    {snippet}
                  </p>
                </div>
              )}
              {(!rationale && (!snippet || snippet === '{}')) && (
                <div className="text-white/40 text-sm italic">
                  No automated rationale or evidence recovered for this dimension.
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div layout className="w-full flex justify-center mt-3 -mb-2">
        <motion.div 
          animate={{ rotate: expanded ? 180 : 0 }} 
          transition={{ duration: 0.2 }}
          className="text-white/30"
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
