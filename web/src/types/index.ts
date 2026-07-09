export interface AnalysisReport {
  keyword: string;
  market: string;
  budget: string;
  verdict: string;
  grade: string;
  overall_score: number;
  max_score: number;
  score_breakdown: Record<string, number>;
  market_analysis: {
    avg_price: number;
    avg_rating: number;
    avg_reviews: number;
    competitors: any[];
    market_profile: any;
  };
  profit_analysis: {
    selling_price: number;
    unit_cost: number;
    total_cost_per_unit: number;
    gross_profit_per_unit: number;
    gross_margin: number;
    gross_margin_pct: string;
    cost_breakdown: Record<string, number>;
    cost_breakdown_pct: Record<string, string>;
    roi_scenarios: Record<string, any>;
    breakeven_units: number;
  };
  trend_analysis: any;
  review_insights: any;
  suppliers: any[];
  compliance: any;
  trending_products: any[];
  next_steps: any[];
}

export interface ProfitResult {
  selling_price: number;
  unit_cost: number;
  total_cost_per_unit: number;
  gross_profit_per_unit: number;
  gross_margin: number;
  gross_margin_pct: string;
  cost_breakdown: Record<string, number>;
  cost_breakdown_pct: Record<string, string>;
  roi_scenarios: Record<string, any>;
  breakeven_units: number | null;
  suggestions: string[];
}

export interface UserInfo {
  username: string;
  role: string;
}
