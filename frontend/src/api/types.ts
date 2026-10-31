// DTOs mirroring the FastAPI schemas (backend/app/schemas).

export type TransactionType = 'income' | 'expense';
export type ClassificationStatus = 'PREDICTED' | 'CONFIRMED' | 'MANUALLY_CORRECTED';

export interface CategoryBreakdownItem {
  category_id: number;
  name: string;
  type: TransactionType;
  total: number;
  /** Share of the total for this category's own type, 0-100. */
  pct: number;
}

export interface MonthlySummary {
  month: string; // YYYY-MM
  income: number;
  expense: number;
  net: number;
  by_category: CategoryBreakdownItem[];
}

export interface TrendPoint {
  month: string; // YYYY-MM
  income: number;
  expense: number;
  net: number;
}

export interface Category {
  id: number;
  name: string;
  type: TransactionType;
  is_default: boolean;
  created_at: string;
}

export interface Classification {
  predicted_category_id: number;
  predicted_category: string;
  /** Model probability for the predicted category, 0-1. */
  confidence: number;
  status: ClassificationStatus;
  /** Version tag of the model that produced the prediction, or null. */
  model_version: string | null;
}

export interface TransactionOut {
  id: number;
  amount: number;
  type: TransactionType;
  date: string; // YYYY-MM-DD
  description: string;
  category_id: number;
  category_name: string;
  is_future: boolean;
  classification: Classification | null;
  created_at: string;
  updated_at: string;
}

/** Request body for creating or replacing a transaction (PUT replaces all fields). */
export interface TransactionInput {
  amount: number;
  type: TransactionType;
  date: string; // YYYY-MM-DD
  description: string;
  category_id: number;
}

export interface TransactionPage {
  items: TransactionOut[];
  total: number;
  page: number;
  page_size: number;
}

export interface TransactionQuery {
  from?: string;
  to?: string;
  type?: TransactionType;
  category_id?: number;
  q?: string;
  status?: ClassificationStatus;
  page?: number;
  page_size?: number;
}

export interface ClassMetrics {
  category_id: number;
  name: string;
  /** null when the class had no examples in the test set. */
  precision: number | null;
  recall: number | null;
  f1: number | null;
  support: number;
}

export interface ConfusionMatrix {
  labels: string[];
  /** Rows are actual categories, columns are predicted categories. */
  matrix: number[][];
}

export interface EvaluationMetrics {
  accuracy: number;
  macro_f1: number;
  weighted_f1: number;
  per_class: ClassMetrics[];
  confusion_matrix: ConfusionMatrix;
  n_train: number;
  n_test: number;
  test_size: number;
  seed: number;
  warnings: string[];
}

export interface Evaluation {
  version_tag: string;
  algorithm: string;
  trained_at: string;
  dataset_size: number;
  metrics: EvaluationMetrics;
}

export type Reliability = 'low' | 'medium' | 'high';

export interface ModelMetrics {
  mae: number;
  rmse: number;
  /** Percent; null when every backtest actual was zero. */
  mape: number | null;
  mape_excluded: number;
}

export interface Forecast {
  target_month: string; // YYYY-MM
  selected_model: string;
  reliability: Reliability;
  method: 'empirical_quantile' | 't_approximation';
  optimistic: number;
  baseline: number;
  conservative: number;
  warning: string | null;
  history_start: string; // YYYY-MM
  history_months: number;
  backtest: {
    per_model: Record<string, ModelMetrics>;
    residuals_used: number;
  };
}
