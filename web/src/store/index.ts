import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    ui: uiReducer,
  },
});

// 持久化最近报告与搜索条件，刷新或跨页导航不丢失
let prevUi = store.getState().ui;
store.subscribe(() => {
  const nextUi = store.getState().ui;
  if (nextUi.currentReport !== prevUi.currentReport) {
    if (nextUi.currentReport) {
      localStorage.setItem('current_report', JSON.stringify(nextUi.currentReport));
    } else {
      localStorage.removeItem('current_report');
    }
  }
  if (nextUi.lastSearch !== prevUi.lastSearch) {
    localStorage.setItem('last_search', JSON.stringify(nextUi.lastSearch));
  }
  prevUi = nextUi;
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
