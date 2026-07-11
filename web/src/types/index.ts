export interface AnalysisReport {
  keyword: string;
  market: string;
  budget: string;
  version?: number;
  verdict: string;
  verdict_color: string;
  grade: string;
  overall_score: number;
  max_score: number;
  score_breakdown: Record<string, number>;
  market_analysis: {
    avg_price: number;
    avg_rating: number;
    avg_reviews: number;
    competitors: any[];
    keyword_summary?: {
      search_volume: number;
      trend: 'rising' | 'stable' | 'falling';
      competition: 'low' | 'medium' | 'high';
      cpc: number;
      opportunity_score: number;
      top_niche_keywords: string[];
    };
    keyword_opportunities?: {
      keyword: string;
      search_volume: number;
      trend: 'rising' | 'stable' | 'falling';
      competition: 'low' | 'medium' | 'high';
      opportunity_score: number;
      cpc: number;
      products: any[];
    }[];
    market_profile: {
      name: string;
      currency: string;
    };
    global_trends?: {
      code: string;
      name: string;
      months: string[];
      values: number[];
      market_size_index: number;
    }[];
    keyword_relationships?: {
      nodes: {
        id: string;
        name: string;
        value: number;
        type: 'root' | 'niche';
        trend?: 'rising' | 'stable' | 'falling';
        competition?: 'low' | 'medium' | 'high';
        opportunity_score?: number;
        segment?: string;
      }[];
      links: { source: string; target: string; value: number }[];
      expansion_suggestions: {
        segment: string;
        keywords: string[];
        avg_score: number;
        rationale: string;
      }[];
    };
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
    breakeven_units: number | null;
  };
  trend_analysis: {
    trend_direction: string;
    series: {
      months: string[];
      values: number[];
      last_year_values: number[];
      forecast_values: number[];
      forecast_months: string[];
    };
    peak_months: number[];
    entry_windows: number[];
    season_narrative: {
      peak_months: string;
      entry_months: string;
      season_desc: string;
      trend_desc: string;
    };
  };
  review_insights: {
    pain_points: string[];
    praised_features: string[];
    opportunities: string[];
  };
  suppliers: any[];
  compliance: {
    certifications: string[];
    risk_level: string;
    estimated_cert_cost: number;
    estimated_cert_time: string;
    category_risks: string[];
    design_patent_risks: string[];
    brand_risks: string[];
    industry_patent_risks: string[];
    market_specific: string[];
    market: string;
  };
  trending_products: any[];
  next_steps: {
    phase: string;
    title: string;
    owner: string;
    tasks: string[];
    value: string;
  }[];
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

export interface AnalysisHistoryItem {
  id: string;
  keyword: string;
  market: string;
  grade: string;
  overall_score: number;
  created_at: string;
}

export interface UserInfo {
  username: string;
  role: string;
}
