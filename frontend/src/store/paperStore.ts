import { create } from 'zustand';
import type { Paper } from '@/lib/types/paper';

interface PaperStore {
  papers: Paper[];
  currentPaper: Paper | null;
  isLoading: boolean;
  addPaper: (doi: string) => void;
  setCurrentPaper: (paper: Paper | null) => void;
  setLoading: (loading: boolean) => void;
}

export const usePaperStore = create<PaperStore>((set) => ({
  papers: [],
  currentPaper: null,
  isLoading: false,
  addPaper: (doi) =>
    set((state) => ({
      papers: [...state.papers, { doi, status: 'pending' }],
    })),
  setCurrentPaper: (paper) => set({ currentPaper: paper }),
  setLoading: (loading) => set({ isLoading: loading }),
}));
