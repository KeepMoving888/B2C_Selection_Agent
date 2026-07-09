import { Card, Col, Row, Spin } from 'antd';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import { useEffect, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

function TrendChart({ report }: { report: AnalysisReport }) {
  const trend = report.trend_analysis;
  const peakMonths = new Set(trend.peak_months);
  const entryWindows = new Set(trend.entry_windows);

  const option: EChartsOption = useMemo(() => {
    const x = trend.series.months;
    const y = trend.series.values;
    const lastYear = trend.series.last_year_values || [];
    const forecastMonths = trend.series.forecast_months || [];
    const forecast = trend.series.forecast_values || [];
    const allX = [...x, ...forecastMonths];
    const maxY = Math.max(...y, ...lastYear.filter(Boolean), ...forecast.filter(Boolean));

    const markAreas: any[] = [];
    entryWindows.forEach((m) => {
      const idx = (m as number) - 1;
      markAreas.push([{ xAxis: idx - 0.5 }, { xAxis: idx + 0.5, itemStyle: { color: 'rgba(20, 184, 166, 0.15)' } }]);
    });
    peakMonths.forEach((m) => {
      const idx = (m as number) - 1;
      markAreas.push([{ xAxis: idx - 0.5 }, { xAxis: idx + 0.5, itemStyle: { color: 'rgba(239, 68, 68, 0.18)' } }]);
    });

    const annotations: any[] = [];
    if (entryWindows.size > 0) {
      const firstEntry = Math.min(...Array.from(entryWindows)) - 1;
      annotations.push({
        x: firstEntry,
        y: maxY * 1.08,
        text: '🚀 提前备货/入局',
        fontSize: 12,
        color: '#0f766e',
        borderColor: '#14b8a6',
      });
    }
    if (peakMonths.size > 0) {
      const firstPeak = Math.min(...Array.from(peakMonths)) - 1;
      annotations.push({
        x: firstPeak,
        y: maxY * 1.08,
        text: '🔥 旺季高峰',
        fontSize: 12,
        color: '#b91c1c',
        borderColor: '#ef4444',
      });
    }

    return {
      tooltip: { trigger: 'axis' },
      legend: { orient: 'horizontal', top: 0, right: 0, backgroundColor: 'rgba(255,255,255,0.8)', borderColor: '#e2e8f0', borderWidth: 1 },
      grid: { left: 20, right: 20, top: 60, bottom: 20, containLabel: true },
      xAxis: { type: 'category', data: allX, axisLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' } },
      yAxis: { type: 'value', name: '搜索热度', max: maxY * 1.18, axisLine: { show: false }, splitLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' } },
      series: [
        {
          type: 'line',
          name: '本年度搜索热度',
          data: [...y, ...new Array(forecastMonths.length).fill(null)],
          smooth: true,
          lineStyle: { color: '#2563eb', width: 3.5 },
          itemStyle: { color: '#2563eb' },
          symbol: 'circle',
          symbolSize: 8,
          label: { show: true, position: 'top', color: '#1e40af', fontSize: 10 },
          markArea: { data: markAreas, silent: true },
          markPoint: {
            data: annotations.map((a) => ({
              name: a.text,
              xAxis: a.x,
              yAxis: a.y,
              label: { show: true, formatter: a.text, color: a.color, fontSize: a.fontSize, backgroundColor: 'rgba(255,255,255,0.95)', borderColor: a.borderColor, borderWidth: 1, padding: [4, 6], borderRadius: 4 },
              symbol: 'rect',
              symbolSize: [1, 1],
              itemStyle: { color: 'transparent' },
            })),
          },
        },
        {
          type: 'line',
          name: '去年同期',
          data: lastYear.length ? [...lastYear, ...new Array(forecastMonths.length).fill(null)] : [],
          smooth: false,
          lineStyle: { color: '#94a3b8', width: 2, type: 'dashed' },
          itemStyle: { color: '#94a3b8' },
          symbol: 'circle',
          symbolSize: 6,
        },
        {
          type: 'line',
          name: '趋势预测',
          data: [...new Array(x.length).fill(null), ...forecast],
          smooth: true,
          lineStyle: { color: '#f59e0b', width: 3, type: 'dashed' },
          itemStyle: { color: '#f59e0b' },
          symbol: 'circle',
          symbolSize: 7,
          label: { show: true, position: 'top', color: '#b45309', fontSize: 10 },
        },
        {
          type: 'scatter',
          name: '提前备货/入局窗口',
          data: [[null, null]],
          itemStyle: { color: 'rgba(20, 184, 166, 0.5)' },
          symbolSize: 12,
        },
        {
          type: 'scatter',
          name: '旺季高峰',
          data: [[null, null]],
          itemStyle: { color: 'rgba(239, 68, 68, 0.5)' },
          symbolSize: 12,
        },
      ],
    };
  }, [trend, peakMonths, entryWindows]);

  return <ReactECharts option={option} style={{ height: 380, width: '100%' }} />;
}

function SeasonActionList({ report }: { report: AnalysisReport }) {
  const trend = report.trend_analysis;
  const peak = [...trend.peak_months].sort((a, b) => a - b).map((m) => `${m}月`).join('、');
  const entry = [...trend.entry_windows].sort((a, b) => a - b).map((m) => `${m}月`).join('、');
  const narrative = trend.season_narrative || {};

  const actionItems = [
    { title: '当前', desc: '完成关键词/市场数据分析，确认品类季节性与利润空间。', color: '#2563eb' },
    { title: '样品验证', desc: '2 周内锁定供应商、完成样品测试与合规资料确认。', color: '#0891b2' },
    { title: '备货发货', desc: `在 ${entry} 完成首批备货并发出，确保旺季前 4-6 周到仓。`, color: '#0f766e' },
    { title: '旺季销售', desc: `把握 ${peak} 需求高峰，加大广告投放与促销力度。`, color: '#ef4444' },
    { title: '复盘迭代', desc: '旺季结束后复盘差评与库存周转，推进 V2.0 产品改良。', color: '#7c3aed' },
  ];

  return (
    <div className="info-card" style={{ marginTop: 14 }}>
      <div className="info-card-title">📅 季节与入场节奏</div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 14, color: '#475569', lineHeight: 1.7, marginBottom: 12 }}>
        <div><span style={{ color: '#ef4444', fontWeight: 800 }}>🔥 旺季高峰：</span>{peak}</div>
        <div><span style={{ color: '#0f766e', fontWeight: 800 }}>🚀 建议提前备货/入局窗口：</span>{entry}</div>
      </div>
      <div style={{ padding: 14, background: '#f8fafc', borderRadius: 12, borderLeft: '4px solid #2563eb' }}>
        <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.75, marginBottom: 6 }}><strong>行业季节洞察：</strong>{narrative.season_desc}</div>
        <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.75 }}><strong>趋势判断：</strong>{narrative.trend_desc}</div>
      </div>
      <div style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>📍 选品到销售行动节奏</div>
        {actionItems.map((item) => (
          <div key={item.title} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
            <div style={{ flexShrink: 0, width: 8, height: 8, borderRadius: '50%', background: item.color, marginTop: 7 }} />
            <div style={{ flex: 1 }}>
              <span style={{ fontWeight: 800, color: '#0f172a', fontSize: 13 }}>{item.title}：</span>
              <span style={{ color: '#475569', fontSize: 13, lineHeight: 1.6 }}>{item.desc}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TrendSeasonal() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();

  useEffect(() => {
    dispatch(setPageTitle('趋势季节'));
  }, [dispatch]);

  return (
    <div className="page-container">
      <div className="page-header">趋势季节</div>
      <Card style={{ borderRadius: 16, marginBottom: 24 }}>
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>正在分析趋势数据...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="趋势季节" />}

      {!loading && report && (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={16}>
            <div className="info-card">
              <div className="info-card-title">📈 搜索热度与季节窗口</div>
              <TrendChart report={report} />
            </div>
          </Col>
          <Col xs={24} lg={8}>
            <SeasonActionList report={report} />
          </Col>
        </Row>
      )}
    </div>
  );
}
