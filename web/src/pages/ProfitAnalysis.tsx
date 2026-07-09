import { Card, Col, Row, Slider, Spin } from 'antd';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import { useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

const COST_COLORS: Record<string, string> = {
  产品成本: '#1e3a8a',
  头程物流: '#06b6d4',
  'FBA 费用': '#f97316',
  平台佣金: '#8b5cf6',
  广告费用: '#ef4444',
  退货预留: '#eab308',
  其他杂费: '#6b7280',
};

function costColor(item: string) {
  return COST_COLORS[item] || '#3b82f6';
}

function roiColor(roi: number) {
  if (roi < 20) return '#dc2626';
  if (roi < 40) return '#f97316';
  if (roi < 60) return '#eab308';
  return '#16a34a';
}

function assumptionRiskColor(name: string, value: number) {
  if (['平台佣金', '广告占比', '退货预留'].includes(name)) {
    if (value >= 15) return '#dc2626';
    if (value >= 10) return '#eab308';
    return '#16a34a';
  }
  if (name === 'FBA 费用') {
    if (value >= 5.5) return '#dc2626';
    if (value >= 4.0) return '#eab308';
    return '#16a34a';
  }
  if (name === '头程物流') {
    if (value >= 3.5) return '#dc2626';
    if (value >= 2.5) return '#eab308';
    return '#16a34a';
  }
  if (name === '盈亏平衡') {
    if (value >= 400) return '#dc2626';
    if (value >= 200) return '#eab308';
    return '#16a34a';
  }
  return '#2563eb';
}

function CostRow({ item, value, pct, total }: { item: string; value: number; pct: string; total: number }) {
  const width = total > 0 ? Math.min(100, Math.max(0, (value / total) * 100)) : 0;
  const pctNum = parseFloat(pct.replace('%', '')) || 0;
  const textColor = width > 18 ? '#ffffff' : costColor(item);

  return (
    <div className="cost-row">
      <div className="cost-dot" style={{ background: costColor(item) }} />
      <div className="cost-info">
        <div className="cost-meta"><span>{item}</span><span>USD {value.toFixed(2)}</span></div>
        <div className="cost-bar-wrapper">
          <div className="cost-bar-fill" style={{ width: `${width}%`, background: costColor(item), color: textColor }}>
            {pctNum.toFixed(1)}%
          </div>
        </div>
        <div className="cost-tooltip">成本构成：USD {value.toFixed(2)} ({pctNum.toFixed(1)}%)</div>
      </div>
    </div>
  );
}

function ScenarioCard({ name, data }: { name: string; data: any }) {
  const icons: Record<string, string> = { 保守: '🛡️', 中性: '⚖️', 乐观: '🚀' };
  const colors: Record<string, any> = {
    保守: { bg: '#eff6ff', border: '#bfdbfe', accent: '#60a5fa', value: '#2563eb', pill: '#1d4ed8' },
    中性: { bg: '#f0fdf4', border: '#bbf7d0', accent: '#4ade80', value: '#16a34a', pill: '#15803d' },
    乐观: { bg: '#fff7ed', border: '#fed7aa', accent: '#fbbf24', value: '#d97706', pill: '#9a3412' },
  };
  const c = colors[name];

  return (
    <div style={{
      background: `linear-gradient(145deg, #ffffff 0%, ${c.bg} 100%)`,
      border: `1px solid ${c.border}`,
      borderRadius: 18,
      padding: '22px 18px',
      textAlign: 'center',
      position: 'relative',
      overflow: 'hidden',
      boxShadow: '0 6px 18px rgba(15,23,42,0.05)',
    }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 5, background: `linear-gradient(90deg, ${c.accent}, ${c.value})` }} />
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        background: 'rgba(255,255,255,0.85)',
        border: `1px solid ${c.border}`,
        color: c.pill,
        padding: '6px 16px',
        borderRadius: 24,
        fontSize: 13,
        fontWeight: 800,
        marginBottom: 16,
        whiteSpace: 'nowrap',
        boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
      }}>
        <span style={{ fontSize: 15 }}>{icons[name]}</span><span>{name}情景</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <div style={{ background: 'rgba(255,255,255,0.65)', borderRadius: 12, padding: '12px 8px' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 5 }}>月销量</div>
          <div style={{ color: c.value, fontSize: 34, fontWeight: 900, lineHeight: 1 }}>{data['月销量']}</div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.65)', borderRadius: 12, padding: '12px 8px' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 5 }}>ROI</div>
          <div style={{ color: c.value, fontSize: 34, fontWeight: 900, lineHeight: 1 }}>{data['ROI']}%</div>
        </div>
      </div>
      <div style={{ borderTop: `1px solid ${c.border}`, paddingTop: 14, textAlign: 'left' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 9 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#64748b', fontSize: 13, fontWeight: 600 }}><span>💰</span> 月毛利</span>
          <span style={{ color: '#0f172a', fontSize: 15, fontWeight: 800 }}>${data['月毛利'].toLocaleString()}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#64748b', fontSize: 13, fontWeight: 600 }}><span>⏳</span> 回本周期</span>
          <span style={{ color: '#0f172a', fontSize: 15, fontWeight: 800 }}>{data['回本周期'] ? `${data['回本周期']} 月` : '—'}</span>
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
        lineStyle: { color: '#3b82f6', width: 3 },
        areaStyle: { color: 'rgba(59, 130, 246, 0.08)' },
        symbol: 'none',
        markLine: {
          symbol: 'none',
          data: [
            { yAxis: 20, lineStyle: { color: '#dc2626', width: 1, type: 'dashed' }, label: { formatter: '20%', color: '#dc2626', fontSize: 10 }, opacity: 0.7 },
            { yAxis: 40, lineStyle: { color: '#f97316', width: 1, type: 'dashed' }, label: { formatter: '40%', color: '#f97316', fontSize: 10 }, opacity: 0.7 },
            { yAxis: 60, lineStyle: { color: '#eab308', width: 1, type: 'dashed' }, label: { formatter: '60%', color: '#eab308', fontSize: 10 }, opacity: 0.7 },
          ],
        },
      },
      {
        type: 'scatter',
        name: '当前销量',
        data: [[currentVolume, currentRoi]],
        symbolSize: 14,
        itemStyle: { color: roiColor(currentRoi), borderColor: '#fff', borderWidth: 2 },
      },
    ];

    Object.entries(scenarioPoints).forEach(([sName, sVol]) => {
      const sRoi = sVol * grossProfit / investment * 100;
      series.push({
        type: 'scatter',
        name: `${sName}情景`,
        data: [[sVol, sRoi]],
        symbolSize: 10,
        itemStyle: { color: roiColor(sRoi), borderColor: '#fff', borderWidth: 2 },
        label: { show: true, position: 'top', formatter: sName, color: '#475569', fontSize: 11 },
      });
    });

    return {
      tooltip: { trigger: 'axis', formatter: (params: any) => `月销量：${params[0].axisValue}<br/>ROI：${params[0].data[1]?.toFixed?.(2) ?? params[0].data.toFixed(2)}%` },
      grid: { left: 20, right: 50, top: 20, bottom: 40, containLabel: true },
      xAxis: { type: 'category', data: volumes, gridLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' }, name: '月销量' },
      yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b', formatter: '{value}%' }, name: 'ROI %' },
      series,
    };
  }, [currentVolume, grossProfit, investment]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', marginBottom: 12 }}>
        <div style={{ flex: 1, minWidth: 140, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '12px 16px', boxShadow: '0 2px 8px rgba(15,23,42,0.04)' }}>
          <div style={{ fontSize: 11, fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 4 }}>当前月销量</div>
          <div style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>{currentVolume} 件</div>
        </div>
        <div style={{ flex: 1, minWidth: 140, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '12px 16px', boxShadow: '0 2px 8px rgba(15,23,42,0.04)' }}>
          <div style={{ fontSize: 11, fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 4 }}>当前 ROI</div>
          <div style={{ fontSize: 20, fontWeight: 900, color: roiColor(currentVolume * grossProfit / investment * 100) }}>{(currentVolume * grossProfit / investment * 100).toFixed(2)}%</div>
        </div>
      </div>
      <Slider min={100} max={600} step={10} value={currentVolume} onChange={setCurrentVolume} tooltip={{ formatter: (v) => `${v} 件` }} />
      <ReactECharts option={option} style={{ height: 340 }} />
    </div>
  );
}

export default function ProfitAnalysis() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();
  const [currentVolume, setCurrentVolume] = useState(300);
  const [costReduction, setCostReduction] = useState(0);
  const [adReduction, setAdReduction] = useState(0);
  const [fbaReduction, setFbaReduction] = useState(0);
  const [priceIncrease, setPriceIncrease] = useState(0);

  useEffect(() => {
    dispatch(setPageTitle('利润测算'));
  }, [dispatch]);

  return (
    <div className="page-container">
      <div className="page-header">利润测算</div>
      <Card style={{ borderRadius: 16, marginBottom: 24 }}>
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>正在测算利润...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="利润测算" />}

      {!loading && report && (
        <>
          {(() => {
            const profit = report.profit_analysis;
            const scenarios = profit.roi_scenarios;
            const bestName = Object.keys(scenarios).reduce((a, b) => scenarios[a].ROI > scenarios[b].ROI ? a : b);
            const bestData = scenarios[bestName];
            const bestActionMap: Record<string, string> = {
              保守: '优先降本控风险，验证最小订单模型',
              中性: '按中性节奏备货，稳步扩大投放',
              乐观: '积极备货并加大广告，抢占旺季窗口',
            };

            return (
              <div style={{
                background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
                border: '1px solid #bfdbfe',
                borderRadius: 16,
                padding: '18px 22px',
                marginBottom: 22,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 14,
                boxShadow: '0 4px 14px rgba(37,99,235,0.08)',
              }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 5 }}>当前最佳 ROI 情景</div>
                  <div style={{ fontSize: 22, fontWeight: 900, color: '#1e40af' }}>{bestName}情景 · ROI {bestData.ROI.toFixed(2)}% · 月毛利 USD {bestData['月毛利'].toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
                </div>
                <div style={{ background: '#fff', borderRadius: 12, padding: '12px 18px', fontSize: 14, fontWeight: 800, color: '#1e40af', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
                  建议操作：{bestActionMap[bestName]}
                </div>
              </div>
            );
          })()}

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={10}>
              <div className="info-card">
                <div className="info-card-title">单件成本明细</div>
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
                <div className="info-card-title">ROI 情景分析</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, marginBottom: 20 }}>
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
                <div className="info-card-title">利润优化模拟器</div>
                <Row gutter={[24, 24]}>
                  <Col xs={24} md={12}>
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#475569', marginBottom: 8 }}>产品成本优化 (USD)</div>
                      <Slider min={0} max={Math.min(2, report.profit_analysis.cost_breakdown['产品成本'] * 0.3)} step={0.1} value={costReduction} onChange={setCostReduction} tooltip={{ formatter: (v) => `USD ${v}` }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#475569', marginBottom: 8 }}>广告费用优化 (USD)</div>
                      <Slider min={0} max={Math.min(1, (report.profit_analysis.cost_breakdown['广告费用'] || 0) * 0.3)} step={0.05} value={adReduction} onChange={setAdReduction} tooltip={{ formatter: (v) => `USD ${v}` }} />
                    </div>
                  </Col>
                  <Col xs={24} md={12}>
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#475569', marginBottom: 8 }}>FBA 费用优化 (USD)</div>
                      <Slider min={0} max={Math.min(1, (report.profit_analysis.cost_breakdown['FBA 费用'] || 0) * 0.3)} step={0.05} value={fbaReduction} onChange={setFbaReduction} tooltip={{ formatter: (v) => `USD ${v}` }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#475569', marginBottom: 8 }}>售价提升 (USD)</div>
                      <Slider min={0} max={5} step={0.1} value={priceIncrease} onChange={setPriceIncrease} tooltip={{ formatter: (v) => `USD ${v}` }} />
                    </div>
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
                  const impactColor = monthlyIncrease > 0 ? '#16a34a' : monthlyIncrease < 0 ? '#dc2626' : '#64748b';

                  const impactLines = [];
                  if (costReduction > 0) impactLines.push(`产品成本降低 USD ${costReduction.toFixed(2)}`);
                  if (adReduction > 0) impactLines.push(`广告费用降低 USD ${adReduction.toFixed(2)}`);
                  if (fbaReduction > 0) impactLines.push(`FBA 费用降低 USD ${fbaReduction.toFixed(2)}`);
                  if (priceIncrease > 0) impactLines.push(`售价提升 USD ${priceIncrease.toFixed(2)}`);

                  return (
                    <>
                      <div className="simulator-result">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                          <div>
                            <div style={{ fontSize: 12, fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 4 }}>优化后毛利率</div>
                            <div style={{ fontSize: 26, fontWeight: 900, color: '#15803d' }}>{(newMargin * 100).toFixed(2)}%</div>
                          </div>
                          <div>
                            <div style={{ fontSize: 12, fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 4 }}>月利润变化</div>
                            <div style={{ fontSize: 26, fontWeight: 900, color: impactColor }}>{monthlyIncrease > 0 ? '+' : ''}USD {monthlyIncrease.toFixed(2)}</div>
                          </div>
                        </div>
                        <div style={{ marginTop: 10, fontSize: 13, color: '#475569', fontWeight: 500 }}>基于 300 件/月销量估算 · 优化后单件毛利 USD {newGrossProfit.toFixed(2)}</div>
                      </div>
                      {impactLines.length > 0 && (
                        <div style={{ marginTop: 12, fontSize: 13, color: '#334155', fontWeight: 500, lineHeight: 1.7 }}>
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
                <div className="info-card-title">关键假设</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
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
                      return (
                        <div key={a.label} className="assumption-card">
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
