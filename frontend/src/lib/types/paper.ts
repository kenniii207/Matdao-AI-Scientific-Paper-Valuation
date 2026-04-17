export type PaperStatus = 'pending' | 'processing' | 'complete' | 'error';

export interface Paper {
  doi: string;
  title?: string;
  status: PaperStatus;
}
