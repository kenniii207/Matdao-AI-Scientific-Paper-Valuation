import { create } from 'zustand';
import type { ScoringResult } from '@/lib/types/scoring';

interface ScoringStore {
  results: Record<string, ScoringResult>;
  currentResult: ScoringResult | null;
  setResult: (doi: string, result: ScoringResult) => void;
  setCurrentResult: (result: ScoringResult | null) => void;
}

export const useScoringStore = create<ScoringStore>((set) => ({
  results: {},
  currentResult: null,
  setResult: (doi, result) =>
    set((state) => ({
      results: { ...state.results, [doi]: result },
    })),
  setCurrentResult: (result) => set({ currentResult: result }),
}));
