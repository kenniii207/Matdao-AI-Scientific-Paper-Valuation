export interface ScoringDimension {
  dimension_id: number;
  dimension_name: string;
  raw_score: number;
  weight?: number;
  automated?: boolean;
  origin_snippet?: string;
}

export interface ScoringDimensionDetail extends ScoringDimension {
  rationale?: string;
}

export interface ScoringResult {
  doi: string;
  dimensions: ScoringDimension[];
  total_score: number;
  grade: string;
  investment_status: string;
  integrity_gate_triggered: boolean;
}

export interface ScoringResponse {
  paper_id: string;
  paper_title?: string;
  doi?: string;
  total_score: number;
  grade: string;
  integrity_gate_triggered: boolean;
  confidence_tier?: string;
  insight?: string;
  investor_fit?: string[];
  warnings?: string[];
  executive_summary?: string;
  investment_recommendation?: string;
  dimensions: ScoringDimensionDetail[];
}

export interface ScoringPendingResponse {
  paper_id: string;
  doi?: string;
  status: string;
  error?: string;
}
