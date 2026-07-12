import { useCallback, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { analysisApi } from '../services/api';
import { generateMockReport } from '../services/mockData';
import { setCurrentReport, setLastSearch, type SearchParams } from '../store/slices/uiSlice';
import type { RootState } from '../store';
import type { AnalysisHistoryItem, AnalysisReport } from '../types';

const REPORT_HISTORY_KEY = 'xuanpin_report_history';

export function getReportHistory(): AnalysisHistoryItem[] {
  try {
    const raw = localStorage.getItem(REPORT_HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveReportToHistory(report: AnalysisReport) {
  try {
    const history = getReportHistory();
    const item: AnalysisHistoryItem = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      keyword: report.keyword,
      market: report.market,
      grade: report.grade,
      overall_score: report.overall_score,
      created_at: new Date().toISOString(),
    };
    // 去重：相同关键词+市场+等级+评分认为是同一次分析
    const exists = history.some(
      (h) => h.keyword === item.keyword && h.market === item.market && h.grade === item.grade && h.overall_score === item.overall_score
    );
    if (exists) return;
    const next = [item, ...history].slice(0, 50);
    localStorage.setItem(REPORT_HISTORY_KEY, JSON.stringify(next));
    // 同时保存完整报告详情，便于离线查看
    localStorage.setItem(`xuanpin_report_detail_${item.id}`, JSON.stringify(report));
  } catch {
    // ignore storage errors
  }
}

export function useReport() {
  const dispatch = useDispatch();
  const { currentReport, lastSearch } = useSelector((state: RootState) => state.ui);
  const [loading, setLoading] = useState(false);
  const [isMockMode, setIsMockMode] = useState(false);

  const analyze = useCallback(async (params: SearchParams, options?: { persist?: boolean }) => {
    setLoading(true);
    const persist = options?.persist !== false;
    try {
      if (persist) {
        dispatch(setLastSearch(params));
      }

      // 检查是否强制使用 Mock 模式（通过环境变量或 URL 参数）
      const forceMock = import.meta.env.VITE_USE_MOCK === 'true' ||
                        new URLSearchParams(window.location.search).has('mock');

      if (forceMock) {
        // 强制 Mock 模式
        const report = generateMockReport(params.keyword, params.market, params.budget);
        dispatch(setCurrentReport(report));
        if (persist) saveReportToHistory(report);
        setIsMockMode(true);
        return report;
      }

      // 尝试调用真实 API
      try {
        const res = await analysisApi.create({
          keyword: params.keyword,
          market: params.market,
          budget: params.budget,
        });
        const report: AnalysisReport = res.data.report;
        dispatch(setCurrentReport(report));
        if (persist) saveReportToHistory(report);
        setIsMockMode(false);
        return report;
      } catch (apiError) {
        // API 调用失败，降级到 Mock 数据
        console.warn('API 调用失败，降级到 Mock 数据:', apiError);
        const report = generateMockReport(params.keyword, params.market, params.budget);
        dispatch(setCurrentReport(report));
        if (persist) saveReportToHistory(report);
        setIsMockMode(true);
        return report;
      }
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  return {
    report: currentReport,
    lastSearch,
    loading,
    isMockMode,
    analyze,
  };
}
