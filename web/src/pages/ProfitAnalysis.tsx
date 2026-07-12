import {
  DollarOutlined,
  FallOutlined,
  PieChartOutlined,
  RiseOutlined,
  SafetyOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Slider, Spin } from 'antd';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useMobile } from '../hooks/useMobile';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';
import { getMarketCurrency } from '../utils/currency';

const COST_COLORS: Record<string, { start: string; end: string; text: string; icon: React.ReactNode }> = {
  产品成本: { start: '#2563eb', end: '#60a5fa', text: '#ffffff', icon: <PieChartOutlined /> },
  头程物流: { start: '#0891b2', end: '#22d3ee', text: '#ffffff', icon: <FallOutlined /> },
  'FBA 费用': { start: '#d97706', end: '#fbbf24', text: '#78350f', icon: <SafetyOutlined /> },
  平台佣金: { start: '#7c3aed', end: '#a78bfa', text: '#ffffff', icon: <DollarOutlined /> },
  广告费用: { start: '#dc2626', end: '#f87171', text: '#ffffff', icon: <RiseOutlined /> },
  退货预留: { start: '#059669', end: '#34d399', text: '#ffffff', icon: <FallOutlined /> },
  其他杂费: { start: '#64748b', end: '#94a3b8', text: '#ffffff', icon: <DollarOutlined /> },
};

function costColor(item: string) {
  return COST_COLORS[item] || { start: '#2563eb', end: '#60a5fa', text: '#ffffff', icon: <DollarOutlined /> };
}

function roiColor(roi: number) {
  if (roi < 20) return '#dc2626';
  if (roi < 40) return '#d97706';
  if (roi < 60) return '#0891b2';
  return '#059669';
}

function roiBgColor(roi: number) {
  if (roi < 20) return '#fef2f2';
  if (roi < 40) return '#fffbeb';
  if (roi < 60) return '#ecfeff';
  return '#ecfdf5';
}

function assumptionRiskColor(name: string, value: number) {
  if (['平台佣金', '广告占比'].includes(name)) {
    // 占售价比例：>20% 高风险，>15% 关注
    if (value >= 20) return '#dc2626';
    if (value >= 15) return '#d97706';
    return '#059669';
  }
  if (name === '退货预留') {
    if (value >= 8) return '#dc2626';
    if (value >= 5) return '#d97706';
    return '#059669';
  }
  if (name === 'FBA 费用') {
    if (value >= 5.5) return '#dc2626';
    if (value >= 4.0) return '#d97706';
    return '#059669';
  }
  if (name === '头程物流') {
    if (value >= 3.5) return '#dc2626';
    if (value >= 2.5) return '#d97706';
    return '#059669';
  }
  if (name === '盈亏平衡') {
    if (value >= 400) return '#dc2626';
    if (value >= 200) return '#d97706';
    return '#059669';
  }
  return '#2563eb';
}

function assumptionRiskBg(color: string) {
  if (color === '#dc2626') return '#fef2f2';
  if (color === '#d97706') return '#fffbeb';
  return '#ecfdf5';
}

// C 端真实 ROI 模型：ROI = 月净利润 / 月总投资
// 月净利润 = 月销量 × 单件净利 - 月度固定运营费用
// 月总投资 = 安全库存投资 + 月度固定运营费用
// 销量上升时，变动成本（产品/物流/FBA/佣金/广告/退货）随销量线性增加，固定费用被摊薄，
// ROI 会逐步上升并趋近于理论上限 = 单件净利 / (安全库存月数 × 到岸成本)
function calculateOptimizedRoiModel(
  report: AnalysisReport,
  costReduction: number,
  adReduction: number,
  fbaReduction: number,
  priceIncrease: number
) {
  const profit = report.profit_analysis;
  const shipping = profit.cost_breakdown['头程物流'] || 2;
  const commission = profit.cost_breakdown['平台佣金'] || 0;
  const returns = profit.cost_breakdown['退货预留'] || 0;
  const other = profit.cost_breakdown['其他杂费'] || 0;

  const newUnitCost = Math.max(0, profit.unit_cost - costReduction);
  const newAdCost = Math.max(0, (profit.cost_breakdown['广告费用'] || 0) - adReduction);
  const newFbaCost = Math.max(0, (profit.cost_breakdown['FBA 费用'] || 0) - fbaReduction);
  const newSellingPrice = profit.selling_price + priceIncrease;

  // 单件变动成本：销量越高，这些成本总额越高，但单件保持不变
  const variableCostPerUnit = newUnitCost + shipping + newFbaCost + commission + newAdCost + returns + other;
  const netProfitPerUnit = newSellingPrice - variableCostPerUnit;
  const landingCost = newUnitCost + shipping;

  const inventoryMonths = 2;
  // 月度固定费用：含人员、仓储租金、软件、办公等，不随销量线性变化
  const monthlyFixed = 2000;
  const volumes = Array.from({ length: 51 }, (_, i) => 100 + i * 10);

  const roiValues = volumes.map((sales) => {
    const monthlyNetProfit = sales * netProfitPerUnit - monthlyFixed;
    const inventoryInvestment = sales * inventoryMonths * landingCost;
    const totalInvestment = inventoryInvestment + monthlyFixed;
    return totalInvestment > 0 ? (monthlyNetProfit / totalInvestment) * 100 : 0;
  });

  const asymptoticRoi = landingCost > 0 && inventoryMonths > 0
    ? (netProfitPerUnit / (landingCost * inventoryMonths)) * 100
    : 0;

  return {
    volumes,
    roiValues,
    netProfitPerUnit,
    variableCostPerUnit,
    newSellingPrice,
    landingCost,
    asymptoticRoi,
    monthlyFixed,
  };
}

function CostRow({ item, value, pct, total, market, sellingPrice }: { item: string; value: number; pct: string; total: number; market: string; sellingPrice: number }) {
  const width = total > 0 ? Math.min(100, Math.max(0, (value / total) * 100)) : 0;
  const pctNum = parseFloat(pct.replace('%', '')) || 0;
  const color = costColor(item);
  const { symbol } = getMarketCurrency(market);
  const ofSellingPct = sellingPrice > 0 ? (value / sellingPrice) * 100 : 0;
  const tooltipText = item === '平台佣金'
    ? `平台佣金：${symbol}${value.toFixed(2)}（占售价 ${ofSellingPct.toFixed(1)}%，与类目佣金率一致）`
    : `成本构成：${symbol}${value.toFixed(2)}（占总成本 ${pctNum.toFixed(1)}%）`;

  return (
    <div className="cost-row">
      <div className="cost-icon" style={{ background: `linear-gradient(135deg, ${color.start}, ${color.end})`, color: '#fff' }}>
        {color.icon}
      </div>
      <div className="cost-info">
        <div className="cost-meta">
          <span className="cost-name">{item}</span>
          <span className="cost-amount">{symbol}{value.toFixed(2)}</span>
        </div>
        <div className="cost-bar-row">
          <div className="cost-bar-wrapper" style={{ background: `${color.start}18`, flex: 1, minWidth: 0 }}>
            <div className="cost-bar-fill" style={{
              width: `${width}%`,
              background: `linear-gradient(90deg, ${color.start}, ${color.end})`,
              color: color.text,
            }} />
          </div>
          <span className="cost-bar-outside-pct" style={{ color: color.start, minWidth: 42, textAlign: 'right' }}>
            {pctNum.toFixed(1)}%
          </span>
        </div>
        <div className="cost-tooltip">{tooltipText}</div>
      </div>
    </div>
  );
}

const SCENARIO_THEME: Record<string, { bg: string; border: string; accent: string; value: string; pill: string; light: string; icon: React.ReactNode }> = {
  保守: {
    bg: '#eff6ff',
    border: '#bfdbfe',
    accent: '#3b82f6',
    value: '#2563eb',
    pill: '#1d4ed8',
    light: '#dbeafe',
    icon: <SafetyOutlined />,
  },
  中性: {
    bg: '#ecfdf5',
    border: '#a7f3d0',
    accent: '#10b981',
    value: '#059669',
    pill: '#047857',
    light: '#d1fae5',
    icon: <PieChartOutlined />,
  },
  乐观: {
    bg: '#fffbeb',
    border: '#fde68a',
    accent: '#f59e0b',
    value: '#d97706',
    pill: '#b45309',
    light: '#fef3c7',
    icon: <RiseOutlined />,
  },
};

function ScenarioCard({ name, data, market }: { name: string; data: any; market: string }) {
  const c = SCENARIO_THEME[name];
  const { symbol } = getMarketCurrency(market);

  return (
    <div className="scenario-card" style={{ ['--border' as string]: c.border, ['--bg' as string]: c.bg, ['--accent' as string]: c.accent, ['--value' as string]: c.value, ['--pill' as string]: c.pill, ['--light' as string]: c.light } as React.CSSProperties}>
      <div className="scenario-card-top" style={{ background: `linear-gradient(90deg, ${c.accent}, ${c.value})` }} />
      <div className="scenario-card-badge">
        <span className="scenario-card-icon">{c.icon}</span>
        <span>{name}情景</span>
      </div>
      <div className="scenario-card-metrics">
        <div className="scenario-metric">
          <div className="scenario-metric-label">月销量</div>
          <div className="scenario-metric-value" style={{ color: c.value }}>{data['月销量']}</div>
        </div>
        <div className="scenario-metric">
          <div className="scenario-metric-label">毛利率</div>
          <div className="scenario-metric-value" style={{ color: c.value }}>{data['毛利率']}</div>
        </div>
        <div className="scenario-metric">
          <div className="scenario-metric-label">ROI</div>
          <div className="scenario-metric-value" style={{ color: c.value }}>{data['ROI'].toFixed(2)}%</div>
        </div>
      </div>
      <div className="scenario-card-footer">
        <div className="scenario-footer-row">
          <span className="scenario-footer-label">月毛利</span>
          <span className="scenario-footer-value">{symbol}{data['月毛利'].toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
        </div>
        <div className="scenario-footer-row">
          <span className="scenario-footer-label">回本周期</span>
          <span className="scenario-footer-value">{data['回本周期'] ? `${data['回本周期']} 月` : '—'}</span>
        </div>
      </div>
    </div>
  );
}

function RoiChart({ report, currentVolume, setCurrentVolume }: { report: AnalysisReport; currentVolume: number; setCurrentVolume: (v: number) => void }) {
  const profit = report.profit_analysis;
  const isMobile = useMobile();
  const shipping = profit.cost_breakdown['头程物流'] || 2;
  const commission = profit.cost_breakdown['平台佣金'] || 0;
  const returns = profit.cost_breakdown['退货预留'] || 0;
  const other = profit.cost_breakdown['其他杂费'] || 0;
  const variableCostPerUnit = profit.unit_cost + shipping + (profit.cost_breakdown['FBA 费用'] || 0) + commission + (profit.cost_breakdown['广告费用'] || 0) + returns + other;
  const netProfitPerUnit = profit.selling_price - variableCostPerUnit;
  const landingCost = profit.unit_cost + shipping;

  const chartData = useMemo(() => {
    const inventoryMonths = 2;
    const monthlyFixed = 2000;
    const volumes = Array.from({ length: 51 }, (_, i) => 100 + i * 10);
    const roiValues = volumes.map((sales) => {
      const monthlyNetProfit = sales * netProfitPerUnit - monthlyFixed;
      const inventoryInvestment = sales * inventoryMonths * landingCost;
      const totalInvestment = inventoryInvestment + monthlyFixed;
      return totalInvestment > 0 ? (monthlyNetProfit / totalInvestment) * 100 : 0;
    });
    const currentRoi = (() => {
      const monthlyNetProfit = currentVolume * netProfitPerUnit - monthlyFixed;
      const inventoryInvestment = currentVolume * inventoryMonths * landingCost;
      const totalInvestment = inventoryInvestment + monthlyFixed;
      return totalInvestment > 0 ? (monthlyNetProfit / totalInvestment) * 100 : 0;
    })();
    const scenarioPoints: Record<string, number> = { 保守: 100, 中性: 300, 乐观: 600 };

    const series: any[] = [
      {
        type: 'line',
        name: 'ROI 趋势',
        data: roiValues,
        smooth: true,
        lineStyle: { color: '#2563eb', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.25)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.03)' },
          ]),
        },
        symbol: 'none',
        markLine: {
          symbol: 'none',
          data: [
            { yAxis: 20, lineStyle: { color: '#dc2626', width: 1, type: 'dashed' }, label: { formatter: '20%', color: '#dc2626', fontSize: 10 }, opacity: 0.7 },
            { yAxis: 40, lineStyle: { color: '#d97706', width: 1, type: 'dashed' }, label: { formatter: '40%', color: '#d97706', fontSize: 10 }, opacity: 0.7 },
            { yAxis: 60, lineStyle: { color: '#0891b2', width: 1, type: 'dashed' }, label: { formatter: '60%', color: '#0891b2', fontSize: 10 }, opacity: 0.7 },
          ],
        },
      },
      {
        type: 'scatter',
        name: '当前销量',
        data: [[currentVolume, currentRoi]],
        symbolSize: 18,
        itemStyle: { color: roiColor(currentRoi), borderColor: '#ffffff', borderWidth: 3, shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.15)' },
        label: { show: true, position: 'top', formatter: `当前\n${currentRoi.toFixed(1)}%`, color: roiColor(currentRoi), fontSize: 11, fontWeight: 800, fontFamily: 'var(--font-sans)' },
      },
    ];

    Object.entries(scenarioPoints).forEach(([sName, sVol]) => {
      const monthlyNetProfit = sVol * netProfitPerUnit - monthlyFixed;
      const inventoryInvestment = sVol * inventoryMonths * landingCost;
      const totalInvestment = inventoryInvestment + monthlyFixed;
      const sRoi = totalInvestment > 0 ? (monthlyNetProfit / totalInvestment) * 100 : 0;
      series.push({
        type: 'scatter',
        name: `${sName}情景`,
        data: [[sVol, sRoi]],
        symbolSize: 12,
        itemStyle: { color: roiColor(sRoi), borderColor: '#ffffff', borderWidth: 2 },
        label: { show: true, position: 'top', formatter: sName, color: 'var(--saas-text-secondary)', fontSize: 11, fontWeight: 800, fontFamily: 'var(--font-sans)' },
      });
    });

    const option: EChartsOption = {
      backgroundColor: '#ffffff',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30, 41, 59, 0.9)',
        borderWidth: 0,
        padding: [2, 5],
        confine: true,
        textStyle: { color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: 9 },
        extraCssText: 'max-width:120px !important;width:auto !important;min-width:0 !important;word-wrap:break-word !important;white-space:normal !important;border-radius:3px !important;box-shadow:none !important;backdrop-filter:blur(4px) !important;',
        formatter: (params: any) => `<div style="font-weight:800;font-size:9px;color:#fff;margin-bottom:2px">月销量 ${params[0].axisValue}</div><div style="color:rgba(255,255,255,0.72);font-size:8px">ROI ${params[0].data[1]?.toFixed?.(2) ?? params[0].data.toFixed(2)}%</div>`,
      },
      grid: { left: 20, right: 50, top: 30, bottom: 40, containLabel: true },
      xAxis: {
        type: 'category',
        data: volumes,
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#64748b', fontFamily: 'var(--font-sans)' },
        name: '月销量',
        nameTextStyle: { color: '#64748b', fontFamily: 'var(--font-sans)' },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#64748b', formatter: '{value}%', fontFamily: 'var(--font-sans)' },
        name: 'ROI %',
        nameTextStyle: { color: '#64748b', fontFamily: 'var(--font-sans)' },
      },
      series,
    };
    return { option, currentRoi };
  }, [currentVolume, netProfitPerUnit, landingCost]);

  const option = chartData.option;
  const currentRoi = chartData.currentRoi;

  return (
    <div>
      <div className="roi-current-cards">
        <div className="roi-current-card">
          <div className="roi-current-label">当前月销量</div>
          <div className="roi-current-value">{currentVolume} 件</div>
        </div>
        <div className="roi-current-card" style={{ background: roiBgColor(currentRoi), borderColor: roiColor(currentRoi) + '30' }}>
          <div className="roi-current-label">当前 ROI</div>
          <div className="roi-current-value" style={{ color: roiColor(currentRoi) }}>{currentRoi.toFixed(2)}%</div>
        </div>
      </div>
      <Slider min={100} max={600} step={10} value={currentVolume} onChange={setCurrentVolume} tooltip={{ formatter: (v) => `${v} 件` }} />
      <ReactECharts option={option} style={{ height: isMobile ? 280 : 340, width: '100%' }} />
    </div>
  );
}

function OptimizedRoiChart({ report, costReduction, adReduction, fbaReduction, priceIncrease }: {
  report: AnalysisReport;
  costReduction: number;
  adReduction: number;
  fbaReduction: number;
  priceIncrease: number;
}) {
  const isMobile = useMobile();
  const { option } = useMemo(() => {
    const base = calculateOptimizedRoiModel(report, 0, 0, 0, 0);
    const optimized = calculateOptimizedRoiModel(report, costReduction, adReduction, fbaReduction, priceIncrease);

    const hasOptimization = costReduction > 0 || adReduction > 0 || fbaReduction > 0 || priceIncrease > 0;
    // eslint-disable-next-line react-hooks/exhaustive-deps

    const option: EChartsOption = {
      backgroundColor: '#ffffff',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30, 41, 59, 0.9)',
        borderWidth: 0,
        padding: [2, 5],
        confine: true,
        textStyle: { color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: 9 },
        extraCssText: 'max-width:120px !important;width:auto !important;min-width:0 !important;word-wrap:break-word !important;white-space:normal !important;border-radius:3px !important;box-shadow:none !important;backdrop-filter:blur(4px) !important;',
        formatter: (params: any) => {
          const lines = params.map((p: any) => `<span style="display:inline-block;width:4px;height:4px;border-radius:50%;background:${p.color};margin-right:4px;vertical-align:middle"></span><span style="font-size:8px;color:rgba(255,255,255,0.72)">${p.seriesName}: ${p.data[1]?.toFixed?.(2) ?? p.data.toFixed(2)}%</span>`);
          return `<div style="font-weight:800;font-size:9px;color:#fff;margin-bottom:2px">月销量 ${params[0].axisValue}</div><div style="line-height:1.3">${lines.join('<br/>')}</div>`;
        },
      },
      legend: {
        data: hasOptimization ? ['原始 ROI', '优化后 ROI'] : ['原始 ROI'],
        top: 0,
        left: 'center',
        textStyle: { color: '#64748b', fontWeight: 700, fontFamily: 'var(--font-sans)' },
      },
      grid: { left: 16, right: 24, top: 36, bottom: 24, containLabel: true },
      xAxis: {
        type: 'category',
        data: base.volumes,
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#64748b', fontFamily: 'var(--font-sans)' },
        name: '月销量',
        nameTextStyle: { color: '#64748b', fontFamily: 'var(--font-sans)' },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#64748b', formatter: '{value}%', fontFamily: 'var(--font-sans)' },
        name: 'ROI %',
        nameTextStyle: { color: '#64748b', fontFamily: 'var(--font-sans)' },
      },
      series: [
        {
          type: 'line',
          name: '原始 ROI',
          data: base.roiValues,
          smooth: true,
          lineStyle: { color: '#94a3b8', width: 2.5, type: 'dashed' },
          symbol: 'none',
          areaStyle: { color: 'rgba(148, 163, 184, 0.06)' },
        },
        ...(hasOptimization ? [{
          type: 'line' as const,
          name: '优化后 ROI',
          data: optimized.roiValues,
          smooth: true,
          lineStyle: { color: '#059669', width: 3 },
          symbol: 'none',
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(5, 150, 105, 0.18)' },
              { offset: 1, color: 'rgba(5, 150, 105, 0.02)' },
            ]),
          },
        }] : []),
      ],
    };
    return { option };
  }, [report, costReduction, adReduction, fbaReduction, priceIncrease]);

  return <ReactECharts option={option} style={{ height: isMobile ? 240 : 280, width: '100%' }} />;
}

const SimulatorSlider = React.memo(function SimulatorSlider({ label, value, max, step, onChange, onChangeComplete, formatter, accent, icon, hint }: { label: string; value: number; max: number; step: number; onChange: (v: number) => void; onChangeComplete: (v: number) => void; formatter: (v?: number) => string; accent?: string; icon?: React.ReactNode; hint?: string }) {
  return (
    <div className="simulator-slider" style={{ ['--slider-accent' as string]: accent } as React.CSSProperties}>
      <div className="simulator-slider-header">
        <span className="simulator-slider-label">
          <span style={{ color: accent, marginRight: 6 }}>{icon}</span>
          {label}
        </span>
        <span className="simulator-slider-value" style={{ color: accent }}>{formatter(value)}</span>
      </div>
      {hint && <div className="simulator-slider-hint">{hint}</div>}
      <Slider min={0} max={max} step={step} value={value} onChange={onChange} onChangeComplete={onChangeComplete} tooltip={{ formatter }} trackStyle={{ background: accent }} />
    </div>
  );
});

function ProfitSummaryBanner({ report }: { report: AnalysisReport }) {
  const profit = report.profit_analysis;
  const { symbol } = getMarketCurrency(report.market);
  const items = [
    { label: '市场售价', value: `${symbol}${profit.selling_price.toFixed(2)}`, color: '#2563eb' },
    { label: '单件总成本', value: `${symbol}${profit.total_cost_per_unit.toFixed(2)}`, color: '#475569' },
    { label: '单件毛利', value: `${symbol}${profit.gross_profit_per_unit.toFixed(2)}`, color: '#059669' },
    { label: '毛利率', value: profit.gross_margin_pct, color: profit.gross_margin_pct.startsWith('-') ? '#dc2626' : '#059669' },
    { label: '盈亏平衡', value: `${profit.breakeven_units} 件/月`, color: '#0891b2' },
  ];

  return (
    <div className="profit-summary-banner">
      {items.map((item) => (
        <div key={item.label} className="profit-summary-item">
          <div className="profit-summary-label">{item.label}</div>
          <div className="profit-summary-value" style={{ color: item.color }}>{item.value}</div>
        </div>
      ))}
    </div>
  );
}

function BestScenarioBanner({ report, activeScenario, onScenarioChange }: { report: AnalysisReport; activeScenario: string; onScenarioChange: (name: string) => void }) {
  const profit = report.profit_analysis;
  const scenarios = profit.roi_scenarios;
  const activeData = scenarios[activeScenario];
  const actionMap: Record<string, string> = {
    保守: '优先降本控风险，验证最小订单模型',
    中性: '按中性节奏备货，稳步扩大投放',
    乐观: '积极备货并加大广告，抢占旺季窗口',
  };
  const theme = SCENARIO_THEME[activeScenario];
  const { symbol } = getMarketCurrency(report.market);

  return (
    <div className="best-scenario-banner" style={{ ['--bg' as string]: theme.bg, ['--border' as string]: theme.border, ['--pill' as string]: theme.pill } as React.CSSProperties}>
      <div style={{ flex: 1, minWidth: 260 }}>
        <div className="best-scenario-label">ROI 情景切换</div>
        <div className="best-scenario-title" style={{ color: theme.pill }}>
          {activeScenario}情景 · ROI {activeData.ROI.toFixed(2)}% · 月毛利 {symbol}{activeData['月毛利'].toLocaleString(undefined, { maximumFractionDigits: 2 })}
        </div>
        <div className="best-scenario-action" style={{ marginTop: 12, display: 'inline-block' }}>
          建议操作：{actionMap[activeScenario]}
        </div>
      </div>
      <div className="best-scenario-switcher" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {Object.keys(scenarios).map((name) => {
          const isActive = name === activeScenario;
          const t = SCENARIO_THEME[name];
          return (
            <button
              key={name}
              type="button"
              onClick={() => onScenarioChange(name)}
              style={{
                padding: '10px 18px',
                borderRadius: 8,
                border: `1px solid ${isActive ? t.accent : '#e2e8f0'}`,
                background: isActive ? t.light : '#ffffff',
                color: isActive ? t.pill : '#64748b',
                fontWeight: 800,
                fontSize: 13,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                transition: 'all 0.2s ease',
                boxShadow: isActive ? `0 2px 8px ${t.accent}30` : 'var(--shadow-sm)',
              }}
            >
              {t.icon}
              {name}情景
            </button>
          );
        })}
      </div>
    </div>
  );
}

const SCENARIO_VOLUME: Record<string, number> = { 保守: 100, 中性: 300, 乐观: 600 };

// 滑动条本地显示值 + 拖动结束提交值，避免滑动时高频 setState 触发页面错误
function useSliderState(initial = 0) {
  const [committed, setCommitted] = useState(initial);
  const [display, setDisplay] = useState(initial);

  const onChange = useCallback((value: number) => {
    setDisplay(value);
  }, []);

  const onChangeComplete = useCallback((value: number) => {
    setDisplay(value);
    setCommitted(value);
  }, []);

  const reset = useCallback((value: number) => {
    setDisplay(value);
    setCommitted(value);
  }, []);

  return { committed, display, onChange, onChangeComplete, reset } as const;
}

export default function ProfitAnalysis() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();
  const [currentVolume, setCurrentVolume] = useState(300);
  const costSlider = useSliderState(0);
  const adSlider = useSliderState(0);
  const fbaSlider = useSliderState(0);
  const priceSlider = useSliderState(0);
  const [activeScenario, setActiveScenario] = useState<string>('中性');

  useEffect(() => {
    dispatch(setPageTitle('利润测算'));
  }, [dispatch]);

  useEffect(() => {
    if (report) {
      setActiveScenario('中性');
      setCurrentVolume(SCENARIO_VOLUME['中性']);
      costSlider.reset(0);
      adSlider.reset(0);
      fbaSlider.reset(0);
      priceSlider.reset(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report]);

  return (
    <div className="page-container">
      <div className="page-hero">
        <div>
          <div className="page-header">利润测算</div>
          <div className="page-subtitle">基于成本结构、售价与销量模拟利润、ROI 与回本周期</div>
        </div>
        {report && (
          <span className="section-badge">
            <DollarOutlined /> 当前分析：{report.keyword}
          </span>
        )}
      </div>
      <Card className="search-card">
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>正在测算利润...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="利润测算" />}

      {!loading && report && (
        <>
          <ProfitSummaryBanner report={report} />
          <BestScenarioBanner
            report={report}
            activeScenario={activeScenario}
            onScenarioChange={(name) => {
              setActiveScenario(name);
              setCurrentVolume(SCENARIO_VOLUME[name]);
            }}
          />

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={10}>
              <div className="info-card">
                <div className="info-card-title">
                  <PieChartOutlined style={{ color: 'var(--saas-primary)' }} /> 单件成本明细
                </div>
                <div className="section-desc">
                  清晰展示每一笔成本占比，帮助定位可优化项。
                </div>
                <div className="cost-breakdown-card" style={{ boxShadow: 'none', padding: 0, border: 'none' }}>
                  <div className="cost-total-row">
                    <span className="cost-total-label">总成本</span>
                    <span className="cost-total-value">{getMarketCurrency(report.market).symbol}{report.profit_analysis.total_cost_per_unit.toFixed(2)}</span>
                  </div>
                  {Object.entries(report.profit_analysis.cost_breakdown).map(([item, value]) => (
                    <CostRow
                      key={item}
                      item={item}
                      value={value as number}
                      pct={report.profit_analysis.cost_breakdown_pct[item] || '0%'}
                      total={report.profit_analysis.total_cost_per_unit}
                      market={report.market}
                      sellingPrice={report.profit_analysis.selling_price}
                    />
                  ))}
                </div>
              </div>
            </Col>
            <Col xs={24} lg={14}>
              <div className="info-card">
                <div className="info-card-title">
                  <RiseOutlined style={{ color: 'var(--saas-success)' }} /> ROI 情景分析
                </div>
                <div className="section-desc">
                  基于保守、中性、乐观三种销量假设，测算对应的毛利率、ROI 与月毛利。毛利率 = 单件毛利 / 售价；ROI = 月净利润 / 月总投资，二者含义不同请勿混淆。
                </div>
                <div className="scenario-grid">
                  {Object.entries(report.profit_analysis.roi_scenarios).map(([name, data]) => (
                    <ScenarioCard key={name} name={name} data={data} market={report.market} />
                  ))}
                </div>
                <RoiChart report={report} currentVolume={currentVolume} setCurrentVolume={setCurrentVolume} />
              </div>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
            <Col xs={24} lg={14}>
              <div className="info-card">
                <div className="info-card-title">
                  <DollarOutlined style={{ color: 'var(--saas-warning)' }} /> 利润优化模拟器
                </div>
                <div className="section-desc">
                  拖动滑块模拟成本优化与售价提升对利润的影响。上限根据当前成本结构动态计算：采购/FBA/广告优化最多可将对应成本降为零，售价提升上限为当前售价的 30%。
                </div>
                <Row gutter={[32, 0]}>
                  <Col xs={24} md={12}><SimulatorSlider
                      label="产品成本优化（降低）"
                      value={costSlider.display}
                      max={Number(report.profit_analysis.unit_cost.toFixed(2))}
                      step={0.05}
                      onChange={costSlider.onChange}
                      onChangeComplete={costSlider.onChangeComplete}
                      formatter={(v) => `−${getMarketCurrency(report.market).symbol}${(v ?? 0).toFixed(2)}`}
                      accent="#2563eb"
                      icon={<PieChartOutlined />}
                      hint="向右拖动表示降低单件采购成本（上限为当前产品成本，可降至 0）"
                    />
                    <SimulatorSlider
                      label="广告费用优化（降低）"
                      value={adSlider.display}
                      max={Number(((report.profit_analysis.cost_breakdown['广告费用'] || 0)).toFixed(2))}
                      step={0.05}
                      onChange={adSlider.onChange}
                      onChangeComplete={adSlider.onChangeComplete}
                      formatter={(v) => `−${getMarketCurrency(report.market).symbol}${(v ?? 0).toFixed(2)}`}
                      accent="#dc2626"
                      icon={<RiseOutlined />}
                      hint="向右拖动表示降低单件广告支出（上限为当前广告费用，可降至 0）"
                    />
                  </Col>
                  <Col xs={24} md={12}>
                    <SimulatorSlider
                      label="FBA 费用优化（降低）"
                      value={fbaSlider.display}
                      max={Number(((report.profit_analysis.cost_breakdown['FBA 费用'] || 0)).toFixed(2))}
                      step={0.05}
                      onChange={fbaSlider.onChange}
                      onChangeComplete={fbaSlider.onChangeComplete}
                      formatter={(v) => `−${getMarketCurrency(report.market).symbol}${(v ?? 0).toFixed(2)}`}
                      accent="#d97706"
                      icon={<SafetyOutlined />}
                      hint="向右拖动表示降低单件 FBA 费用（上限为当前 FBA 费用，可降至 0）"
                    />
                    <SimulatorSlider
                      label="售价提升（增加）"
                      value={priceSlider.display}
                      max={Number((report.profit_analysis.selling_price * 0.3).toFixed(2))}
                      step={0.05}
                      onChange={priceSlider.onChange}
                      onChangeComplete={priceSlider.onChangeComplete}
                      formatter={(v) => `+${getMarketCurrency(report.market).symbol}${(v ?? 0).toFixed(2)}`}
                      accent="#059669"
                      icon={<DollarOutlined />}
                      hint="向右拖动表示提升单件售价（上限为当前售价的 30%）"
                    />
                  </Col>
                </Row>
                {(() => {
                  const profit = report.profit_analysis;
                  const { symbol } = getMarketCurrency(report.market);
                  const base = calculateOptimizedRoiModel(report, 0, 0, 0, 0);
                  const optimized = calculateOptimizedRoiModel(report, costSlider.committed, adSlider.committed, fbaSlider.committed, priceSlider.committed);
                  const newMargin = optimized.newSellingPrice > 0 ? optimized.netProfitPerUnit / optimized.newSellingPrice : 0;
                  const baseMonthlyNet = 300 * base.netProfitPerUnit - base.monthlyFixed;
                  const newMonthlyNet = 300 * optimized.netProfitPerUnit - optimized.monthlyFixed;
                  const monthlyIncrease = newMonthlyNet - baseMonthlyNet;
                  const impactColor = monthlyIncrease > 0 ? '#059669' : monthlyIncrease < 0 ? '#dc2626' : '#64748b';

                  const baseRoiAt300 = base.roiValues[20];
                  const optimizedRoiAt300 = optimized.roiValues[20];
                  const roiDelta = optimizedRoiAt300 - baseRoiAt300;

                  const impactLines = [];
                  if (costSlider.committed > 0) impactLines.push(`产品成本降低 ${symbol}${costSlider.committed.toFixed(2)}`);
                  if (adSlider.committed > 0) impactLines.push(`广告费用降低 ${symbol}${adSlider.committed.toFixed(2)}`);
                  if (fbaSlider.committed > 0) impactLines.push(`FBA 费用降低 ${symbol}${fbaSlider.committed.toFixed(2)}`);
                  if (priceSlider.committed > 0) impactLines.push(`售价提升 ${symbol}${priceSlider.committed.toFixed(2)}`);

                  return (
                    <>
                      <div className="simulator-result">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                          <div>
                            <div className="simulator-result-label">优化后毛利率</div>
                            <div className="simulator-result-value" style={{ color: '#059669' }}>{(newMargin * 100).toFixed(2)}%</div>
                          </div>
                          <div>
                            <div className="simulator-result-label">月净利润变化（300件）</div>
                            <div className="simulator-result-value" style={{ color: impactColor }}>{monthlyIncrease > 0 ? '+' : ''}{symbol}{monthlyIncrease.toFixed(2)}</div>
                          </div>
                          <div>
                            <div className="simulator-result-label">300件 ROI 变化</div>
                            <div className="simulator-result-value" style={{ color: impactColor }}>{roiDelta > 0 ? '+' : ''}{roiDelta.toFixed(2)}%</div>
                          </div>
                        </div>
                        <div className="simulator-result-note">
                          当前单件净利 {symbol}{optimized.netProfitPerUnit.toFixed(2)} · 到岸成本 {symbol}{optimized.landingCost.toFixed(2)} · 月度固定费用 {symbol}{optimized.monthlyFixed.toLocaleString()} · 稳态 ROI {optimized.asymptoticRoi.toFixed(2)}%
                        </div>
                      </div>
                      {impactLines.length > 0 && (
                        <div className="simulator-impact">
                          <WarningOutlined style={{ color: 'var(--saas-warning)', marginRight: 8 }} />
                          {impactLines.join(' · ')}，毛利率从 {profit.gross_margin_pct} 提升至 {(newMargin * 100).toFixed(2)}%。
                        </div>
                      )}
                      <div style={{ marginTop: 20 }}>
                        <div className="info-card-title" style={{ fontSize: 13, marginBottom: 8 }}>
                          <RiseOutlined style={{ color: 'var(--saas-success)' }} /> 优化前后 ROI 曲线对比
                        </div>
                        <OptimizedRoiChart
                          report={report}
                          costReduction={costSlider.committed}
                          adReduction={adSlider.committed}
                          fbaReduction={fbaSlider.committed}
                          priceIncrease={priceSlider.committed}
                        />
                      </div>
                      <div className="simulator-explain">
                        <div className="simulator-explain-title">ROI 计算逻辑与销量关系</div>
                        <div className="simulator-explain-body">
                          本系统采用 C 端真实 ROI 模型：<strong>ROI = 月净利润 ÷ 月总投资</strong>。<br />
                          其中：月净利润 = 月销量 × 单件净利 - 月度固定运营费用 {symbol}{optimized.monthlyFixed.toLocaleString()}；<br />
                          月总投资 = 安全库存投资（月销量 × 2 个月 × 到岸成本）+ 月度固定运营费用。<br />
                          当销量上升时，产品成本、物流、FBA、佣金、广告、退货等变动成本会随销量线性增加，但<strong>月度固定费用被摊薄</strong>，因此 ROI 会逐步上升并趋近于理论上限 = 单件净利 ÷（安全库存月数 × 到岸成本）。<br />
                          优化器降低的是单件变动成本，直接提升单件净利，从而推动整条 ROI 曲线上移。
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            </Col>
            <Col xs={24} lg={10}>
              <div className="info-card">
                <div className="info-card-title">
                  <SafetyOutlined style={{ color: 'var(--saas-info)' }} /> 关键假设
                </div>
                <div className="section-desc">
                  以下指标直接影响利润测算结果，绿色为健康、橙色为关注、红色为高风险。
                </div>
                <div className="assumption-grid">
                  {(() => {
                    const profit = report.profit_analysis;
                    const { symbol } = getMarketCurrency(report.market);
                    const breakdown = profit.cost_breakdown;
                    const sellingPrice = profit.selling_price || 1;
                    const assumptions = [
                      { label: '平台佣金', value: ((breakdown['平台佣金'] || 0) / sellingPrice) * 100, fmt: '%', hint: '占售价比例' },
                      { label: 'FBA 费用', value: breakdown['FBA 费用'] || 0, fmt: 'money', hint: '单件费用' },
                      { label: '广告占比', value: ((breakdown['广告费用'] || 0) / sellingPrice) * 100, fmt: '%', hint: '占售价比例' },
                      { label: '退货预留', value: ((breakdown['退货预留'] || 0) / sellingPrice) * 100, fmt: '%', hint: '占售价比例' },
                      { label: '头程物流', value: breakdown['头程物流'] || 0, fmt: 'money', hint: '单件费用' },
                      { label: '盈亏平衡', value: profit.breakeven_units || 0, fmt: 'units', hint: '月销量' },
                    ];
                    return assumptions.map((a) => {
                      const valueText = a.fmt === '%'
                        ? `${a.value.toFixed(1)}%`
                        : a.fmt === 'money'
                          ? `${symbol}${a.value.toFixed(2)}`
                          : `${Math.round(a.value)} 件/月`;
                      const color = assumptionRiskColor(a.label, a.value);
                      const bg = assumptionRiskBg(color);
                      return (
                        <div key={a.label} className="assumption-card" style={{ ['--risk-bg' as string]: bg, ['--risk-color' as string]: color } as React.CSSProperties}>
                          <div className="assumption-label">{a.label}</div>
                          <div className="assumption-value" style={{ color }}>{valueText}</div>
                          <div style={{ fontSize: 10, color: 'var(--saas-text-muted)', marginTop: 4, fontWeight: 600 }}>{a.hint}</div>
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
}
