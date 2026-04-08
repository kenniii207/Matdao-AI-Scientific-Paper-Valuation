import { create } from 'zustand';

interface DimensionScore {
  dimension_id: number;
  dimension_name: string;
  raw_score: number;
  weight: number;
  origin_snippet?: string;
  automated: boolean;
}

interface ScoringResult {
  doi: string;
  dimensions: DimensionScore[];
  total_score: number;
  grade: string;
  investment_status: string;
  integrity_gate_triggered: boolean;
}

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
