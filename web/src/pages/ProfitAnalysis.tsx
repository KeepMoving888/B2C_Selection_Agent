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
import { useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

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
  if (['平台佣金', '广告占比', '退货预留'].includes(name)) {
    if (value >= 15) return '#dc2626';
    if (value >= 10) return '#d97706';
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

function CostRow({ item, value, pct, total }: { item: string; value: number; pct: string; total: number }) {
  const width = total > 0 ? Math.min(100, Math.max(0, (value / total) * 100)) : 0;
  const pctNum = parseFloat(pct.replace('%', '')) || 0;
  const color = costColor(item);

  return (
    <div className="cost-row">
      <div className="cost-icon" style={{ background: `linear-gradient(135deg, ${color.start}, ${color.end})`, color: '#fff' }}>
        {color.icon}
      </div>
      <div className="cost-info">
        <div className="cost-meta">
          <span className="cost-name">{item}</span>
          <span className="cost-amount">USD {value.toFixed(2)}</span>
        </div>
        <div className="cost-bar-row">
          <div className="cost-bar-wrapper">
            <div className="cost-bar-fill" style={{
              width: `${width}%`,
              background: `linear-gradient(90deg, ${color.start}, ${color.end})`,
              color: color.text,
            }} />
          </div>
          <span className="cost-bar-outside-pct" style={{ color: color.start }}>
            {pctNum.toFixed(1)}%
          </span>
        </div>
        <div className="cost-tooltip">成本构成：USD {value.toFixed(2)} ({pctNum.toFixed(1)}%)</div>
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

function ScenarioCard({ name, data }: { name: string; data: any }) {
  const c = SCENARIO_THEME[name];

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
          <div className="scenario-metric-label">ROI</div>
          <div className="scenario-metric-value" style={{ color: c.value }}>{data['ROI'].toFixed(2)}%</div>
        </div>
      </div>
      <div className="scenario-card-footer">
        <div className="scenario-footer-row">
          <span className="scenario-footer-label">月毛利</span>
          <span className="scenario-footer-value">${data['月毛利'].toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
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
  const investment = profit.unit_cost * 500 + 2000;
  const grossProfit = profit.gross_profit_per_unit;

  const option: EChartsOption = useMemo(() => {
    const volumes = Array.from({ length: 51 }, (_, i) => 100 + i * 10);
    const roiValues = volumes.map((v) => v * grossProfit / investment * 100);
    const currentRoi = currentVolume * grossProfit / investment * 100;
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
      const sRoi = sVol * grossProfit / investment * 100;
      series.push({
        type: 'scatter',
        name: `${sName}情景`,
        data: [[sVol, sRoi]],
        symbolSize: 12,
        itemStyle: { color: roiColor(sRoi), borderColor: '#ffffff', borderWidth: 2 },
        label: { show: true, position: 'top', formatter: sName, color: 'var(--saas-text-secondary)', fontSize: 11, fontWeight: 800, fontFamily: 'var(--font-sans)' },
      });
    });

    return {
      backgroundColor: '#ffffff',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        textStyle: { color: '#1e293b', fontFamily: 'var(--font-sans)' },
        formatter: (params: any) => `月销量：${params[0].axisValue}<br/>ROI：${params[0].data[1]?.toFixed?.(2) ?? params[0].data.toFixed(2)}%`,
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
  }, [currentVolume, grossProfit, investment]);

  const currentRoi = currentVolume * grossProfit / investment * 100;

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
      <ReactECharts option={option} style={{ height: 340 }} />
    </div>
  );
}

function SimulatorSlider({ label, value, max, step, onChange, formatter, accent, icon }: { label: string; value: number; max: number; step: number; onChange: (v: number) => void; formatter: (v?: number) => string; accent?: string; icon?: React.ReactNode }) {
  return (
    <div className="simulator-slider">
      <div className="simulator-slider-header">
        <span className="simulator-slider-label">
          <span style={{ color: accent, marginRight: 6 }}>{icon}</span>
          {label}
        </span>
        <span className="simulator-slider-value" style={{ color: accent }}>{formatter(value)}</span>
      </div>
      <Slider min={0} max={max} step={step} value={value} onChange={onChange} tooltip={{ formatter }} trackStyle={{ background: accent }} handleStyle={{ borderColor: accent }} />
    </div>
  );
}

function ProfitSummaryBanner({ report }: { report: AnalysisReport }) {
  const profit = report.profit_analysis;
  const items = [
    { label: '市场售价', value: `$${profit.selling_price.toFixed(2)}`, color: '#2563eb' },
    { label: '单件总成本', value: `$${profit.total_cost_per_unit.toFixed(2)}`, color: '#475569' },
    { label: '单件毛利', value: `$${profit.gross_profit_per_unit.toFixed(2)}`, color: '#059669' },
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

  return (
    <div className="best-scenario-banner" style={{ ['--bg' as string]: theme.bg, ['--border' as string]: theme.border, ['--pill' as string]: theme.pill } as React.CSSProperties}>
      <div style={{ flex: 1, minWidth: 260 }}>
        <div className="best-scenario-label">ROI 情景切换</div>
        <div className="best-scenario-title" style={{ color: theme.pill }}>
          {activeScenario}情景 · ROI {activeData.ROI.toFixed(2)}% · 月毛利 USD {activeData['月毛利'].toLocaleString(undefined, { maximumFractionDigits: 2 })}
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

export default function ProfitAnalysis() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();
  const [currentVolume, setCurrentVolume] = useState(300);
  const [costReduction, setCostReduction] = useState(0);
  const [adReduction, setAdReduction] = useState(0);
  const [fbaReduction, setFbaReduction] = useState(0);
  const [priceIncrease, setPriceIncrease] = useState(0);
  const [activeScenario, setActiveScenario] = useState<string>('中性');

  useEffect(() => {
    dispatch(setPageTitle('利润测算'));
  }, [dispatch]);

  useEffect(() => {
    if (report) {
      setActiveScenario('中性');
      setCurrentVolume(SCENARIO_VOLUME['中性']);
    }
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
                    <span className="cost-total-value">USD {report.profit_analysis.total_cost_per_unit.toFixed(2)}</span>
                  </div>
                  {Object.entries(report.profit_analysis.cost_breakdown).map(([item, value]) => (
                    <CostRow
                      key={item}
                      item={item}
                      value={value as number}
                      pct={report.profit_analysis.cost_breakdown_pct[item] || '0%'}
                      total={report.profit_analysis.total_cost_per_unit}
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
                  基于保守、中性、乐观三种销量假设，测算对应的 ROI 与月毛利。
                </div>
                <div className="scenario-grid">
                  {Object.entries(report.profit_analysis.roi_scenarios).map(([name, data]) => (
                    <ScenarioCard key={name} name={name} data={data} />
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
                  拖动滑块模拟成本优化与售价提升对毛利率的影响，探索利润提升空间。
                </div>
                <Row gutter={[32, 0]}>
                  <Col xs={24} md={12}>
                    <SimulatorSlider
                      label="产品成本优化"
                      value={costReduction}
                      max={Math.min(2, report.profit_analysis.cost_breakdown['产品成本'] * 0.3)}
                      step={0.1}
                      onChange={setCostReduction}
                      formatter={(v) => `USD ${(v ?? 0).toFixed(2)}`}
                      accent="#2563eb"
                      icon={<PieChartOutlined />}
                    />
                    <SimulatorSlider
                      label="广告费用优化"
                      value={adReduction}
                      max={Math.min(1, (report.profit_analysis.cost_breakdown['广告费用'] || 0) * 0.3)}
                      step={0.05}
                      onChange={setAdReduction}
                      formatter={(v) => `USD ${(v ?? 0).toFixed(2)}`}
                      accent="#dc2626"
                      icon={<RiseOutlined />}
                    />
                  </Col>
                  <Col xs={24} md={12}>
                    <SimulatorSlider
                      label="FBA 费用优化"
                      value={fbaReduction}
                      max={Math.min(1, (report.profit_analysis.cost_breakdown['FBA 费用'] || 0) * 0.3)}
                      step={0.05}
                      onChange={setFbaReduction}
                      formatter={(v) => `USD ${(v ?? 0).toFixed(2)}`}
                      accent="#d97706"
                      icon={<SafetyOutlined />}
                    />
                    <SimulatorSlider
                      label="售价提升"
                      value={priceIncrease}
                      max={5}
                      step={0.1}
                      onChange={setPriceIncrease}
                      formatter={(v) => `USD ${(v ?? 0).toFixed(2)}`}
                      accent="#059669"
                      icon={<DollarOutlined />}
                    />
                  </Col>
                </Row>
                {(() => {
                  const profit = report.profit_analysis;
                  const newTotalCost = Math.max(0, profit.total_cost_per_unit - costReduction - adReduction - fbaReduction);
                  const newSellingPrice = profit.selling_price + priceIncrease;
                  const newGrossProfit = newSellingPrice - newTotalCost;
                  const newMargin = newSellingPrice > 0 ? newGrossProfit / newSellingPrice : 0;
                  const baseMonthly = 300 * profit.gross_profit_per_unit;
                  const newMonthly = 300 * newGrossProfit;
                  const rawIncrease = newMonthly - baseMonthly;
                  const monthlyIncrease = Math.abs(rawIncrease) < 0.005 ? 0 : rawIncrease;
                  const impactColor = monthlyIncrease > 0 ? '#059669' : monthlyIncrease < 0 ? '#dc2626' : '#64748b';

                  const impactLines = [];
                  if (costReduction > 0) impactLines.push(`产品成本降低 USD ${costReduction.toFixed(2)}`);
                  if (adReduction > 0) impactLines.push(`广告费用降低 USD ${adReduction.toFixed(2)}`);
                  if (fbaReduction > 0) impactLines.push(`FBA 费用降低 USD ${fbaReduction.toFixed(2)}`);
                  if (priceIncrease > 0) impactLines.push(`售价提升 USD ${priceIncrease.toFixed(2)}`);

                  return (
                    <>
                      <div className="simulator-result">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                          <div>
                            <div className="simulator-result-label">优化后毛利率</div>
                            <div className="simulator-result-value" style={{ color: '#059669' }}>{(newMargin * 100).toFixed(2)}%</div>
                          </div>
                          <div>
                            <div className="simulator-result-label">月利润变化</div>
                            <div className="simulator-result-value" style={{ color: impactColor }}>{monthlyIncrease > 0 ? '+' : ''}USD {monthlyIncrease.toFixed(2)}</div>
                          </div>
                        </div>
                        <div className="simulator-result-note">基于 300 件/月销量估算 · 优化后单件毛利 USD {newGrossProfit.toFixed(2)}</div>
                      </div>
                      {impactLines.length > 0 && (
                        <div className="simulator-impact">
                          <WarningOutlined style={{ color: 'var(--saas-warning)', marginRight: 8 }} />
                          {impactLines.join(' · ')}，毛利率从 {profit.gross_margin_pct} 提升至 {(newMargin * 100).toFixed(2)}%。
                        </div>
                      )}
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
                    const total = profit.total_cost_per_unit;
                    const breakdown = profit.cost_breakdown;
                    const assumptions = [
                      { label: '平台佣金', value: (breakdown['平台佣金'] || 0) / total * 100, fmt: '%' },
                      { label: 'FBA 费用', value: breakdown['FBA 费用'] || 0, fmt: 'USD' },
                      { label: '广告占比', value: (breakdown['广告费用'] || 0) / total * 100, fmt: '%' },
                      { label: '退货预留', value: (breakdown['退货预留'] || 0) / total * 100, fmt: '%' },
                      { label: '头程物流', value: breakdown['头程物流'] || 0, fmt: 'USD' },
                      { label: '盈亏平衡', value: profit.breakeven_units || 0, fmt: 'units' },
                    ];
                    return assumptions.map((a) => {
                      const valueText = a.fmt === '%' ? `${a.value.toFixed(2)}%` : a.fmt === 'USD' ? `USD ${a.value.toFixed(2)}` : `${Math.round(a.value)} 件/月`;
                      const color = assumptionRiskColor(a.label, a.value);
                      const bg = assumptionRiskBg(color);
                      return (
                        <div key={a.label} className="assumption-card" style={{ ['--risk-bg' as string]: bg, ['--risk-color' as string]: color } as React.CSSProperties}>
                          <div className="assumption-label">{a.label}</div>
                          <div className="assumption-value" style={{ color }}>{valueText}</div>
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
