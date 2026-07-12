import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { generateMockReport } from '../../services/mockData';
import type { AnalysisReport } from '../../types';

const REPORT_VERSION = 2;

export interface SearchParams {
  keyword: string;
  market: string;
  budget: string;
}

interface UIState {
  sidebarCollapsed: boolean;
  mobileMenuOpen: boolean;
  theme: 'light' | 'dark';
  pageTitle: string;
  currentReport: AnalysisReport | null;
  lastSearch: SearchParams;
}

const savedReport = (() => {
  try {
    const raw = localStorage.getItem('current_report');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AnalysisReport;
    if (parsed.version === REPORT_VERSION) return parsed;
    // 旧版本报告自动迁移：保留搜索参数，重新生成完整数据
    if (parsed.keyword && parsed.market && parsed.budget) {
      const migrated = generateMockReport(parsed.keyword, parsed.market, parsed.budget);
      localStorage.setItem('current_report', JSON.stringify(migrated));
      return migrated;
    }
    return null;
  } catch {
    return null;
  }
})();

const savedSearch = (() => {
  try {
    const raw = localStorage.getItem('last_search');
    return raw ? (JSON.parse(raw) as SearchParams) : null;
  } catch {
    return null;
  }
})();

const initialState: UIState = {
  sidebarCollapsed: false,
  mobileMenuOpen: false,
  theme: 'light', // 参赛版本固定浅色主题，保证自定义 CSS 视觉统一
  pageTitle: '',
  currentReport: savedReport,
  lastSearch: savedSearch || { keyword: '', market: 'US', budget: '5000-10000' },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
    },
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.sidebarCollapsed = action.payload;
    },
    toggleMobileMenu: (state) => {
      state.mobileMenuOpen = !state.mobileMenuOpen;
    },
    setMobileMenuOpen: (state, action: PayloadAction<boolean>) => {
      state.mobileMenuOpen = action.payload;
    },
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', state.theme);
    },
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload;
      localStorage.setItem('theme', state.theme);
    },
    setPageTitle: (state, action: PayloadAction<string>) => {
      state.pageTitle = action.payload;
    },
    setCurrentReport: (state, action: PayloadAction<AnalysisReport | null>) => {
      state.currentReport = action.payload;
    },
    setLastSearch: (state, action: PayloadAction<SearchParams>) => {
      state.lastSearch = action.payload;
    },
  },
});

export const { toggleSidebar, setSidebarCollapsed, toggleMobileMenu, setMobileMenuOpen, toggleTheme, setTheme, setPageTitle, setCurrentReport, setLastSearch } =
  uiSlice.actions;
export default uiSlice.reducer;
