import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { analysisApi } from '../services/api';
import { setCurrentReport, setLastSearch, type SearchParams } from '../store/slices/uiSlice';
import type { RootState } from '../store';
import type { AnalysisReport } from '../types';

export function useReport() {
  const dispatch = useDispatch();
  const { currentReport, lastSearch } = useSelector((state: RootState) => state.ui);
  const [loading, setLoading] = useState(false);

  const analyze = async (params: SearchParams) => {
    setLoading(true);
    try {
      dispatch(setLastSearch(params));
      const res = await analysisApi.create({
        keyword: params.keyword,
        market: params.market,
        budget: params.budget,
      });
      const report: AnalysisReport = res.data.report;
      dispatch(setCurrentReport(report));
      return report;
    } finally {
      setLoading(false);
    }
  };

  return {
    report: currentReport,
    lastSearch,
    loading,
    analyze,
  };
}
