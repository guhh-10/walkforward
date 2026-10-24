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

export interface TransactionOut {
  id: number;
  amount: number;
  type: TransactionType;
  date: string; // YYYY-MM-DD
  description: string;
  category_id: number;
  category_name: string;
  is_future: boolean;
  classification: unknown; // typed in the classification stage
  created_at: string;
  updated_at: string;
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
