import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { AnalysisReport } from '../../types';

export interface SearchParams {
  keyword: string;
  market: string;
  budget: string;
}

interface UIState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  pageTitle: string;
  currentReport: AnalysisReport | null;
  lastSearch: SearchParams;
}

const initialState: UIState = {
  sidebarCollapsed: false,
  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  pageTitle: '',
  currentReport: null,
  lastSearch: { keyword: '', market: 'US', budget: '5000-10000' },
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

export const { toggleSidebar, setSidebarCollapsed, toggleTheme, setTheme, setPageTitle, setCurrentReport, setLastSearch } =
  uiSlice.actions;
export default uiSlice.reducer;
