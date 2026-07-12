import { CalendarOutlined, CarryOutOutlined, FireOutlined, InboxOutlined, LineChartOutlined, RiseOutlined } from '@ant-design/icons';
import { Card, Col, Row, Spin } from 'antd';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import { useEffect, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useMobile } from '../hooks/useMobile';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

// 明亮、通透、成熟的商务配色 —— 与原 Streamlit 页面保持一致，避免任何偏黑/沉闷色块
const COLORS = {
  currentLine: '#2563eb',
  currentFill: '#60a5fa',
  lastYear: '#94a3b8',
  forecast: '#f59e0b',
  entryBg: 'rgba(20, 184, 166, 0.06)',
  entryText: '#0f766e',
  entryBorder: '#14b8a6',
  peakBg: 'rgba(239, 68, 68, 0.06)',
  peakText: '#b91c1c',
  peakBorder: '#ef4444',
  grid: '#e2e8f0',
  text: '#475569',
  textMuted: '#64748b',
  bg: '#ffffff',
};

function TrendChart({ report }: { report: AnalysisReport }) {
  const trend = report.trend_analysis;
  const isMobile = useMobile();
  const peakMonths = useMemo(() => new Set(trend.peak_months), [trend.peak_months]);
  const entryWindows = useMemo(() => new Set(trend.entry_windows), [trend.entry_windows]);

  const option: EChartsOption = useMemo(() => {
    const x = trend.series.months;
    const y = trend.series.values;
    const lastYear = trend.series.last_year_values || [];
    const forecastMonths = trend.series.forecast_months || [];
    const forecast = trend.series.forecast_values || [];
    const allX = [...x, ...forecastMonths];
    const rawMaxY = Math.max(...y, ...lastYear.filter(Boolean), ...forecast.filter(Boolean));
    const maxY = Math.ceil(rawMaxY * 1.12 / 10) * 10;

    const markAreas: any[] = [];
    entryWindows.forEach((m) => {
      const idx = (m as number) - 1;
      markAreas.push([{ xAxis: idx - 0.5 }, { xAxis: idx + 0.5, itemStyle: { color: COLORS.entryBg } }]);
    });
    peakMonths.forEach((m) => {
      const idx = (m as number) - 1;
      markAreas.push([{ xAxis: idx - 0.5 }, { xAxis: idx + 0.5, itemStyle: { color: COLORS.peakBg } }]);
    });

    return {
      backgroundColor: COLORS.bg,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30, 41, 59, 0.92)',
        borderWidth: 0,
        padding: [5, 8],
        confine: true,
        textStyle: { color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: 11 },
        extraCssText: 'max-width:180px !important;width:auto !important;min-width:0 !important;word-wrap:break-word !important;white-space:normal !important;border-radius:4px !important;box-shadow:0 2px 8px rgba(0,0,0,0.15) !important;backdrop-filter:blur(4px) !important;',
        formatter: (params: any) => {
          const validParams = params.filter((p: any) => p.data != null && p.data !== undefined);
          const lines = validParams.map((p: any) => `<span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:${p.color};margin-right:5px;vertical-align:middle"></span><span style="font-size:10px;color:rgba(255,255,255,0.8)">${p.seriesName}: ${p.data ?? p.value}</span>`);
          return `<div style="font-weight:800;font-size:12px;color:#fff;margin-bottom:3px">${params[0].axisValue}</div><div style="line-height:1.45">${lines.join('<br/>')}</div>`;
        },
      },
      legend: {
        orient: 'horizontal',
        top: isMobile ? undefined : 0,
        bottom: isMobile ? 0 : undefined,
        left: 'center',
        itemGap: isMobile ? 10 : 20,
        itemWidth: isMobile ? 10 : 14,
        itemHeight: isMobile ? 10 : 14,
        textStyle: { color: COLORS.text, fontWeight: 700, fontFamily: 'var(--font-sans)', fontSize: isMobile ? 10 : 12 },
      },
      grid: { left: isMobile ? 10 : 16, right: isMobile ? 10 : 16, top: isMobile ? 38 : 52, bottom: isMobile ? 48 : 32, containLabel: true },
      xAxis: {
        type: 'category',
        data: allX,
        axisLine: { lineStyle: { color: COLORS.grid } },
        axisLabel: { color: COLORS.textMuted, fontWeight: 600, fontFamily: 'var(--font-sans)', fontSize: isMobile ? 10 : 12, interval: 0, rotate: isMobile ? 30 : 0 },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        name: isMobile ? '' : '搜索热度',
        max: maxY,
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: COLORS.textMuted, fontWeight: 600, fontFamily: 'var(--font-sans)', fontSize: isMobile ? 10 : 12 },
        nameTextStyle: { color: COLORS.textMuted, fontWeight: 700, fontFamily: 'var(--font-sans)' },
      },
      series: [
        {
          type: 'line',
          name: '本年度搜索热度',
          data: [...y, ...new Array(forecastMonths.length).fill(null)],
          smooth: true,
          lineStyle: { color: COLORS.currentLine, width: 3.5 },
          itemStyle: { color: COLORS.currentFill, borderColor: COLORS.currentLine, borderWidth: 2 },
          symbol: 'circle',
          symbolSize: 7,
          label: { show: false },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(37, 99, 235, 0.12)' },
              { offset: 1, color: 'rgba(37, 99, 235, 0.01)' },
            ]),
          },
          markArea: {
            silent: true,
            data: markAreas,
            itemStyle: { opacity: isMobile ? 0.5 : 0.7 },
          },
        },
        {
          type: 'line',
          name: '去年同期',
          data: lastYear.length ? [...lastYear, ...new Array(forecastMonths.length).fill(null)] : [],
          smooth: false,
          lineStyle: { color: COLORS.lastYear, width: 2, type: 'dashed' },
          itemStyle: { color: COLORS.lastYear },
          symbol: 'circle',
          symbolSize: 4,
        },
        {
          type: 'line',
          name: '趋势预测',
          data: [...new Array(x.length).fill(null), ...forecast],
          smooth: true,
          lineStyle: { color: COLORS.forecast, width: 3, type: 'dashed' },
          itemStyle: { color: COLORS.forecast },
          symbol: 'circle',
          symbolSize: 6,
          label: { show: false },
        },
        {
          type: 'scatter',
          name: '提前备货 / 入局窗口',
          data: [[null, null]],
          itemStyle: { color: COLORS.entryBorder, opacity: 0.6 },
          symbolSize: 10,
        },
        {
          type: 'scatter',
          name: '旺季高峰',
          data: [[null, null]],
          itemStyle: { color: COLORS.peakBorder, opacity: 0.6 },
          symbolSize: 10,
        },
      ],
    };
  }, [trend, peakMonths, entryWindows, isMobile]);

  return <ReactECharts option={option} style={{ height: isMobile ? 300 : 420, width: '100%' }} />;
}

function SeasonActionList({ report }: { report: AnalysisReport }) {
  const trend = report.trend_analysis;
  const peak = [...trend.peak_months].sort((a, b) => a - b).map((m) => `${m}月`).join('、');
  const entry = [...trend.entry_windows].sort((a, b) => a - b).map((m) => `${m}月`).join('、');
  const narrative = trend.season_narrative || {};

  const actionItems = [
    { title: '当前', desc: '完成关键词/市场数据分析，确认品类季节性与利润空间。', color: '#3b82f6', icon: <LineChartOutlined /> },
    { title: '样品验证', desc: '2 周内锁定供应商、完成样品测试与合规资料确认。', color: '#0891b2', icon: <InboxOutlined /> },
    { title: '备货发货', desc: `在 ${entry} 完成首批备货并发出，确保旺季前 4-6 周到仓。`, color: '#14b8a6', icon: <CarryOutOutlined /> },
    { title: '旺季销售', desc: `把握 ${peak} 需求高峰，加大广告投放与促销力度。`, color: '#ef4444', icon: <FireOutlined /> },
    { title: '复盘迭代', desc: '旺季结束后复盘差评与库存周转，推进 V2.0 产品改良。', color: '#7c3aed', icon: <RiseOutlined /> },
  ];

  return (
    <div className="info-card" style={{ height: '100%' }}>
      <div className="info-card-title">
        <CalendarOutlined style={{ color: 'var(--saas-primary)' }} /> 季节与入场节奏
      </div>
      <div className="section-desc">
        基于全年热度曲线，提炼旺季高峰与最佳备货/入局窗口，指导选品到销售节奏。
      </div>

      <div className="season-highlight-grid">
        <div className="season-peak-box">
          <div className="season-highlight-label" style={{ color: '#dc2626' }}>旺季高峰</div>
          <div className="season-highlight-value" style={{ color: '#b91c1c' }}>{peak}</div>
        </div>
        <div className="season-entry-box">
          <div className="season-highlight-label" style={{ color: '#0f766e' }}>建议备货窗口</div>
          <div className="season-highlight-value" style={{ color: '#0f766e' }}>{entry}</div>
        </div>
      </div>

      <div className="season-insight-box" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, color: 'var(--saas-text-secondary)', lineHeight: 1.8, marginBottom: 8 }}>
          <strong style={{ color: 'var(--saas-text)' }}>行业季节洞察：</strong>{narrative.season_desc}
        </div>
        <div style={{ fontSize: 13, color: 'var(--saas-text-secondary)', lineHeight: 1.8 }}>
          <strong style={{ color: 'var(--saas-text)' }}>趋势判断：</strong>{narrative.trend_desc}
        </div>
      </div>

      <div>
        <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--saas-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 14 }}>
          选品到销售行动节奏
        </div>
        {actionItems.map((item) => (
          <div key={item.title} className="season-timeline-item">
            <div className="season-timeline-icon" style={{ background: `${item.color}15`, color: item.color }}>
              {item.icon}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 800, color: 'var(--saas-text)', fontSize: 14, marginBottom: 4 }}>{item.title}</div>
              <div style={{ color: 'var(--saas-text-secondary)', fontSize: 13, lineHeight: 1.65 }}>{item.desc}</div>
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
      <div className="page-hero">
        <div>
          <div className="page-header">趋势季节</div>
          <div className="page-subtitle">分析全年搜索热度走势，识别旺季高峰与最佳备货/入局窗口</div>
        </div>
        {report && (
          <span className="section-badge">
            <LineChartOutlined /> 当前分析：{report.keyword}
          </span>
        )}
      </div>
      <Card className="search-card">
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>正在分析趋势数据...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="趋势季节" />}

      {!loading && report && (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={16}>
            <div className="info-card">
              <div className="info-card-title">
                <LineChartOutlined style={{ color: 'var(--saas-primary)' }} /> 搜索热度与季节窗口
              </div>
              <div className="section-desc">
                蓝色实线为当年热度，灰色虚线为去年同期，橙色虚线为预测趋势；绿色与红色区域分别为建议备货窗口与旺季高峰。数据源：Google Trends 搜索热度（经季节性与趋势拟合）。
              </div>
              <div className="season-legend-bar">
                <span className="season-legend-item"><span className="season-legend-dot" style={{ background: COLORS.entryBorder, opacity: 0.5 }} />提前备货 / 入局窗口</span>
                <span className="season-legend-item"><span className="season-legend-dot" style={{ background: COLORS.peakBorder, opacity: 0.5 }} />旺季高峰</span>
              </div>
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
