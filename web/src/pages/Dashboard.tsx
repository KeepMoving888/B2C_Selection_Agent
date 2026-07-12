import {
  AuditOutlined,
  BarChartOutlined,
  CarryOutOutlined,
  CommentOutlined,
  DollarOutlined,
  FallOutlined,
  FileTextOutlined,
  FireOutlined,
  RiseOutlined,
  ShopOutlined,
  StarOutlined,
  StockOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Spin } from 'antd';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import React, { useEffect, useMemo, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import WelcomeGuide from '../components/WelcomeGuide';
import { useMobile } from '../hooks/useMobile';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';
import { getMarketCurrency } from '../utils/currency';

const MAX_VALUES: Record<string, number> = {
  利润空间: 40,
  趋势热度: 25,
  竞争强度: 20,
  评论洞察: 15,
  供应链稳定性: 15,
};

const SCORE_COLORS: Record<string, { start: string; end: string; bg: string }> = {
  利润空间: { start: '#059669', end: '#34d399', bg: '#ecfdf5' },
  趋势热度: { start: '#dc2626', end: '#f87171', bg: '#fef2f2' },
  竞争强度: { start: '#0891b2', end: '#22d3ee', bg: '#ecfeff' },
  评论洞察: { start: '#2563eb', end: '#60a5fa', bg: '#eff6ff' },
  供应链稳定性: { start: '#d97706', end: '#fbbf24', bg: '#fffbeb' },
};

const METRIC_ACCENTS: Record<string, { color: string; bg: string; light: string; icon: React.ReactNode }> = {
  综合评分: { color: '#2563eb', bg: '#eff6ff', light: '#dbeafe', icon: <TrophyOutlined /> },
  毛利率: { color: '#059669', bg: '#ecfdf5', light: '#d1fae5', icon: <DollarOutlined /> },
  盈亏平衡: { color: '#0891b2', bg: '#ecfeff', light: '#cffafe', icon: <StarOutlined /> },
  趋势热度: { color: '#7c3aed', bg: '#f5f3ff', light: '#ede9fe', icon: <StockOutlined /> },
};

const quickLinks = [
  { path: '/market-analysis', label: '市场分析', sub: '竞品与定价', icon: <BarChartOutlined />, color: '#2563eb', bg: '#eff6ff' },
  { path: '/review-insights', label: '评论洞察', sub: '痛点与机会', icon: <CommentOutlined />, color: '#0891b2', bg: '#ecfeff' },
  { path: '/profit-analysis', label: '利润测算', sub: '成本与 ROI', icon: <DollarOutlined />, color: '#059669', bg: '#ecfdf5' },
  { path: '/trend-seasonal', label: '趋势季节', sub: '热度与备货', icon: <StockOutlined />, color: '#d97706', bg: '#fffbeb' },
  { path: '/suppliers', label: '供应商', sub: '报价与产能', icon: <ShopOutlined />, color: '#7c3aed', bg: '#f5f3ff' },
  { path: '/compliance', label: '合规检查', sub: '认证与风控', icon: <AuditOutlined />, color: '#dc2626', bg: '#fef2f2' },
  { path: '/action-plan', label: '行动计划', sub: '落地节奏', icon: <CarryOutOutlined />, color: '#0d9488', bg: '#f0fdfa' },
  { path: '/report-center', label: '报告中心', sub: '归档与分享', icon: <FileTextOutlined />, color: '#475569', bg: '#f8fafc' },
];

function TrendTag({ direction }: { direction: string }) {
  const isRising = direction === 'rising';
  const isStable = direction === 'stable';
  // 选品行业配色：红色 = 上升/热门；绿色 = 下降/冷却；黄色 = 警惕/稳定
  const color = isRising ? '#dc2626' : isStable ? '#d97706' : '#059669';
  const bg = isRising ? '#fef2f2' : isStable ? '#fffbeb' : '#ecfdf5';
  const border = isRising ? '#fee2e2' : isStable ? '#fde68a' : '#d1fae5';
  const Icon = isRising ? RiseOutlined : isStable ? FireOutlined : FallOutlined;
  const label = isRising ? '上升' : isStable ? '稳定' : '下滑';

  return (
    <span className="badge" style={{ background: bg, color, border: `1px solid ${border}`, fontSize: 14, fontWeight: 800, padding: '6px 14px' }}>
      <Icon style={{ fontSize: 13 }} /> 趋势 {label}
    </span>
  );
}

function VerdictBanner({ report }: { report: AnalysisReport }) {
  const profile = report.market_analysis.market_profile;
  const market = report.market_analysis;

  return (
    <div className="verdict-banner">
      <div className="verdict-banner-inner">
        <div className="verdict-main">
          <div className="verdict-label">分析对象</div>
          <div className="verdict-title">{report.keyword} · {profile.name}</div>
          <div className="verdict-meta">
            <span className="badge" style={{ background: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0' }}>
              预算 {report.budget}
            </span>
            <span className="badge" style={{ background: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0', marginLeft: 8 }}>
              均价 {profile.currency}{market.avg_price}
            </span>
            <span className="badge" style={{ background: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0', marginLeft: 8 }}>
              评分 {market.avg_rating} / 5.0
            </span>
          </div>
        </div>
        <div className="verdict-actions">
          <TrendTag direction={report.trend_analysis.trend_direction} />
          <span className="verdict-pill" style={{ background: `linear-gradient(135deg, ${report.verdict_color}, ${adjustColor(report.verdict_color, -20)})` }}>
            <span className="verdict-grade">{report.grade}</span>
            {report.verdict}
          </span>
        </div>
      </div>
    </div>
  );
}

function KpiCards({ report }: { report: AnalysisReport }) {
  const profit = report.profit_analysis;
  const trend = report.trend_analysis;
  const breakeven = profit.breakeven_units ?? 'N/A';
  const trendLabel = trend.trend_direction === 'rising' ? '上升' : trend.trend_direction === 'stable' ? '稳定' : '下滑';
  const { symbol } = getMarketCurrency(report.market);
  // 选品行业配色：上升=红色（热门/积极），稳定=黄色（警惕），下滑=绿色（冷却）
  const trendColor = trend.trend_direction === 'rising' ? '#dc2626' : trend.trend_direction === 'stable' ? '#d97706' : '#059669';
  const trendBg = trend.trend_direction === 'rising' ? '#fef2f2' : trend.trend_direction === 'stable' ? '#fffbeb' : '#ecfdf5';
  const trendLight = trend.trend_direction === 'rising' ? '#fee2e2' : trend.trend_direction === 'stable' ? '#fef3c7' : '#d1fae5';
  const scorePct = Math.min(99, Math.round((report.overall_score / report.max_score) * 100));

  const metrics = [
    {
      label: '综合评分',
      value: `${report.overall_score}/${report.max_score}`,
      sub: `等级 ${report.grade} · ${report.verdict}`,
      trend: `高于 ${scorePct}% 的品类`,
      accent: METRIC_ACCENTS['综合评分'],
    },
    {
      label: '毛利率',
      value: profit.gross_margin_pct,
      sub: `单件毛利 ${symbol}${profit.gross_profit_per_unit.toFixed(2)}`,
      trend: '基于市场均价测算',
      accent: METRIC_ACCENTS['毛利率'],
    },
    {
      label: '盈亏平衡',
      value: `${breakeven} 件`,
      sub: '覆盖固定成本所需销量',
      trend: '月销量 ≥ 此值可盈利',
      accent: METRIC_ACCENTS['盈亏平衡'],
    },
    {
      label: '趋势热度',
      value: trendLabel,
      sub: `搜索热度${trendLabel === '上升' ? '持续走高' : trendLabel === '稳定' ? '保持平稳' : '出现回落'}`,
      trend: (
        <>
          <span style={{ color: trendColor }}>旺季</span>
          <span>集中在 {trend.peak_months.slice(0, 3).join('、')} 月</span>
        </>
      ),
      accent: { color: trendColor, bg: trendBg, light: trendLight, icon: <StockOutlined /> },
    },
  ];

  return (
    <div className="metric-grid">
      {metrics.map((m) => (
        <div key={m.label} className="metric-box" style={{ ['--accent' as string]: m.accent.color, ['--accent-bg' as string]: m.accent.bg, ['--accent-light' as string]: m.accent.light } as React.CSSProperties}>
          <div className="metric-top">
            <div className="metric-icon">{m.accent.icon}</div>
            <div className="metric-label" style={{ color: m.accent.color }}>{m.label}</div>
          </div>
          <div className="metric-value" style={{ color: m.accent.color }}>
            {m.value}
          </div>
          <div className="metric-sub">{m.sub}</div>
          <div className="metric-trend">
            <span style={{ color: m.accent.color }}>●</span>
            <span style={{ color: 'var(--saas-text-muted)' }}>{m.trend}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function RadarChart({ report }: { report: AnalysisReport }) {
  const isMobile = useMobile();
  const option: EChartsOption = useMemo(() => {
    const categories = Object.keys(report.score_breakdown);
    const values = Object.values(report.score_breakdown);
    const normalized = categories.map((cat, i) => Math.min(100, (values[i] / MAX_VALUES[cat]) * 100));
    const avg = normalized.reduce((a, b) => a + b, 0) / normalized.length;
    const benchmark = categories.map(() => 60);
    const shortNames: Record<string, string> = {
      利润空间: '利润\n空间',
      趋势热度: '趋势\n热度',
      竞争强度: '竞争\n强度',
      评论洞察: '评论\n洞察',
      供应链稳定性: '供应链\n稳定性',
    };

    return {
      color: ['#2563eb', '#94a3b8'],
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(30, 41, 59, 0.86)',
        borderWidth: 0,
        padding: [3, 6],
        confine: true,
        extraCssText: 'max-width:120px;word-wrap:break-word;white-space:normal;border-radius:3px;box-shadow:none;backdrop-filter:blur(4px);',
        textStyle: { color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: 9 },
        formatter: (params: any) => {
          if (params.seriesIndex === 1) {
            return '<div style="font-weight:800;font-size:9px;color:#fff">行业基准</div><div style="color:rgba(255,255,255,0.72);font-size:8px;margin-top:1px">参考线 60%</div>';
          }
          const list = params.value.map((v: number, i: number) => {
            const color = SCORE_COLORS[categories[i]].start;
            return `<div style="display:flex;align-items:center;gap:4px;margin:1px 0;flex-wrap:nowrap">
              <span style="display:inline-block;width:4px;height:4px;border-radius:50%;background:${color};flex-shrink:0"></span>
              <span style="font-weight:700;font-size:9px;color:#fff;white-space:nowrap">${categories[i]}</span>
              <span style="color:rgba(255,255,255,0.72);font-size:8px;margin-left:auto">${v.toFixed(0)}%</span>
            </div>`;
          }).join('');
          return `<div style="font-weight:800;margin-bottom:2px;font-size:9px;color:#fff">选品能力评分</div>${list}`;
        },
      },
      radar: {
        indicator: categories.map((cat) => ({
          name: isMobile ? shortNames[cat] || cat : cat,
          max: 100,
          color: SCORE_COLORS[cat].start,
        })),
        radius: isMobile ? '58%' : '72%',
        center: ['50%', isMobile ? '52%' : '50%'],
        shape: 'polygon',
        splitNumber: 5,
        axisName: {
          fontSize: isMobile ? 10 : 13,
          fontWeight: 900,
          fontFamily: 'var(--font-sans)',
          lineHeight: 14,
        },
        axisLine: {
          lineStyle: { color: '#cbd5e1', width: 1.5 },
        },
        splitLine: {
          lineStyle: {
            color: '#e2e8f0',
            width: 1,
          },
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: ['rgba(248, 250, 252, 0.9)', 'rgba(241, 245, 249, 0.7)', 'rgba(248, 250, 252, 0.85)', 'rgba(241, 245, 249, 0.6)', 'rgba(248, 250, 252, 0.95)'],
          },
        },
      },
      series: [
        {
          type: 'radar',
          data: [{
            value: normalized,
            name: '选品能力评分',
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(37, 99, 235, 0.48)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.14)' },
              ]),
            },
            lineStyle: { color: '#2563eb', width: 3, shadowBlur: 14, shadowColor: 'rgba(37,99,235,0.28)' },
            symbol: 'circle',
            symbolSize: 10,
            itemStyle: { color: '#2563eb', borderColor: '#fff', borderWidth: 3, shadowBlur: 14, shadowColor: 'rgba(37,99,235,0.45)' },
            label: {
              show: true,
              formatter: (params: any) => String(Math.round(params.value)),
              color: '#1e40af',
              fontSize: 13,
              fontWeight: 900,
              fontFamily: 'var(--font-sans)',
              textShadowColor: 'rgba(255,255,255,0.95)',
              textShadowBlur: 4,
            },
          }],
          animationDuration: 1200,
          animationEasing: 'cubicOut',
          z: 10,
        },
        {
          type: 'radar',
          data: [{
            value: benchmark,
            name: '行业基准',
            lineStyle: { color: '#94a3b8', width: 2, type: [6, 4] },
            symbol: 'none',
            itemStyle: { opacity: 0 },
            areaStyle: { opacity: 0 },
          }],
          silent: true,
          z: 5,
        },
      ],
      graphic: [
        {
          type: 'group',
          left: 'center',
          top: '50%',
          z: 100,
          children: [
            {
              type: 'circle',
              shape: { cx: 0, cy: 0, r: 44 },
              style: {
                fill: 'rgba(255, 255, 255, 0.98)',
                stroke: 'rgba(226, 232, 240, 0.8)',
                lineWidth: 1,
                shadowBlur: 18,
                shadowColor: 'rgba(37, 99, 235, 0.14)',
              },
            },
            {
              type: 'circle',
              shape: { cx: 0, cy: 0, r: 40 },
              style: {
                fill: 'none',
                stroke: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#60a5fa' },
                  { offset: 1, color: '#1d4ed8' },
                ]),
                lineWidth: 5,
              },
            },
            {
              type: 'text',
              left: 'center',
              top: 'center',
              style: {
                text: `${Math.round(avg)}`,
                fontSize: 28,
                fontWeight: 900,
                fill: '#1e40af',
                textAlign: 'center',
                textVerticalAlign: 'middle',
                fontFamily: 'var(--font-sans)',
                y: -8,
              },
            },
            {
              type: 'text',
              left: 'center',
              top: 'center',
              style: {
                text: '综合均分',
                fontSize: 12,
                fontWeight: 800,
                fill: '#64748b',
                textAlign: 'center',
                textVerticalAlign: 'middle',
                fontFamily: 'var(--font-sans)',
                y: 18,
              },
            },
          ],
        },
      ],
    };
  }, [report, isMobile]);

  return <ReactECharts key={`radar-${report.keyword}`} option={option} style={{ height: isMobile ? 340 : 440 }} notMerge={true} />;
}

function ScoreBreakdown({ report }: { report: AnalysisReport }) {
  const total = Object.values(report.score_breakdown).reduce((a, b) => a + b, 0);
  const sortedDimensions = Object.entries(report.score_breakdown)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([name]) => name);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="info-card-title">五维评分拆解</div>
      <div className="section-desc">
        各项得分对综合评分的贡献度与相对表现，帮助定位优势与短板。
      </div>
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1 }}>
          {Object.entries(report.score_breakdown).map(([name, score]) => {
            const maxV = MAX_VALUES[name] ?? 25;
            const pct = Math.min(100, Math.max(0, (score / maxV) * 100));
            const contribution = total > 0 ? (score / total) * 100 : 0;
            const color = SCORE_COLORS[name];
            return (
              <div key={name} className="score-row">
                <div className="score-name" style={{ color: color.start, fontWeight: 800 }}>{name}</div>
                <div className="score-bar-bg">
                  <div className="score-bar-fill" style={{ width: `${pct}%`, ['--bar-start' as string]: color.start, ['--bar-end' as string]: color.end }} />
                </div>
                <div className="score-value" style={{ color: color.start }}>
                  <span>{score}</span>
                  <span style={{ fontSize: 11, color: color.end, fontWeight: 700, marginLeft: 2 }}>/{maxV}</span>
                </div>
                <div className="score-contribution" style={{ color: color.start }}>{contribution.toFixed(1)}%</div>
              </div>
            );
          })}
        </div>
        <div className="dashboard-insight-box" style={{ marginTop: 'auto', flexShrink: 0 }}>
          <strong>综合判定：</strong>
          该品类在{' '}
          {sortedDimensions.map((name, idx) => (
            <React.Fragment key={name}>
              <span style={{ color: SCORE_COLORS[name].start, fontWeight: 800 }}>{name}</span>
              {idx < sortedDimensions.length - 1 ? '、' : ''}
            </React.Fragment>
          ))}
          {' '}等维度表现突出；建议结论由五维加权与毛利率共同决定，若趋势/竞争/供应链任一维度偏弱，会下调评级。
        </div>
      </div>
    </div>
  );
}

function Conclusion({ report }: { report: AnalysisReport }) {
  const market = report.market_analysis;
  const profile = market.market_profile;
  const trendMap: Record<string, string> = { rising: '上升', stable: '稳定', falling: '下滑' };
  const trendText = trendMap[report.trend_analysis.trend_direction] || report.trend_analysis.trend_direction;

  return (
    <div>
      <div className="info-card-title" style={{ marginBottom: 10, paddingBottom: 10, fontSize: 14 }}>核心结论</div>
      <p style={{ color: 'var(--saas-text-secondary)', lineHeight: 1.6, margin: 0, fontSize: 13 }}>
        关键词 <strong style={{ color: '#2563eb' }}>{report.keyword}</strong>
        在 <strong>{profile.name}</strong> 市场平均售价
        <strong> {profile.currency}{market.avg_price}</strong>，
        毛利率 <strong style={{ color: report.verdict_color }}>{report.profit_analysis.gross_margin_pct}</strong>，
        趋势 <strong>{trendText}</strong>。
        综合判定为 <strong style={{ color: report.verdict_color }}>{report.verdict}</strong>。
      </p>
      <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
        <span className="badge" style={{ background: '#eff6ff', color: '#1d4ed8', border: '1px solid #dbeafe', fontSize: 11, padding: '4px 10px' }}>竞品 {market.competitors.length} 款</span>
        <span className="badge" style={{ background: '#dbeafe', color: '#1e40af', border: '1px solid #bfdbfe', fontSize: 11, padding: '4px 10px' }}>评分 {market.avg_rating}</span>
        <span className="badge" style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #e2e8f0', fontSize: 11, padding: '4px 10px' }}>评论 {market.avg_reviews.toLocaleString()}+</span>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { report, lastSearch, loading, analyze } = useReport();

  // 优先使用 URL 参数作为表单初始值，避免从关键词点击打开时污染原页面的 lastSearch
  const urlParams = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return {
      keyword: params.get('keyword')?.trim() || '',
      market: params.get('market')?.trim() || lastSearch.market || 'US',
      budget: params.get('budget')?.trim() || lastSearch.budget || '5000-10000',
      auto: params.get('auto') === '1',
      nopersist: params.get('nopersist') === '1',
    };
  }, [lastSearch]);

  const formInitialValues = useMemo(() => {
    return urlParams.keyword
      ? { keyword: urlParams.keyword, market: urlParams.market, budget: urlParams.budget }
      : lastSearch;
  }, [urlParams, lastSearch]);

  useEffect(() => {
    dispatch(setPageTitle('首页概览'));
  }, [dispatch]);

  // 支持从 URL 参数自动发起分析（如细分关键词点击“在新页面分析”）
  const autoAnalyzed = useRef(false);
  useEffect(() => {
    if (autoAnalyzed.current) return;
    if (urlParams.auto && urlParams.keyword) {
      autoAnalyzed.current = true;
      analyze(
        {
          keyword: urlParams.keyword,
          market: urlParams.market,
          budget: urlParams.budget,
        },
        { persist: !urlParams.nopersist }
      ).then(() => {
        // 分析完成后清理 auto/nopersist 参数，避免刷新重复触发
        const next = new URLSearchParams(window.location.search);
        next.delete('auto');
        next.delete('nopersist');
        window.history.replaceState({}, '', `${window.location.pathname}?${next.toString()}`);
      });
    }
  }, [analyze, urlParams]);

  return (
    <div className="page-container">
      <div className="page-hero">
        <div>
          <div className="page-header">首页概览</div>
          <div className="page-subtitle">输入关键词，获取多维度选品分析与决策建议</div>
        </div>
        {report && (
          <span className="section-badge">
            <BarChartOutlined /> 当前分析：{report.keyword}
          </span>
        )}
      </div>
      <Card className="search-card">
        <AnalysisSearchForm initialValues={formInitialValues} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>Multi-Agent 协同分析中，请稍候...</div>
        </div>
      )}

      {!loading && !report && (
        <WelcomeGuide
          onExample={(keyword) => {
            const params = { ...lastSearch, keyword };
            analyze(params);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        />
      )}

      {!loading && report && (
        <>
          <VerdictBanner report={report} />
          <KpiCards report={report} />

          <div className="info-card" style={{ marginBottom: 24 }}>
            <Conclusion report={report} />
          </div>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={14}>
              <div className="info-card" style={{ height: '100%' }}>
                <div className="info-card-title">选品能力雷达</div>
                <RadarChart report={report} />
              </div>
            </Col>
            <Col xs={24} lg={10}>
              <div className="info-card" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
                <ScoreBreakdown report={report} />
              </div>
            </Col>
          </Row>

          <div className="info-card" style={{ height: 'auto' }}>
            <div className="info-card-title">深度分析入口</div>
            <div className="section-desc">
              点击以下模块，查看「{report.keyword}」在各维度的详细分析与决策建议。
            </div>
            <div className="quick-link-grid">
              {quickLinks.map((link) => (
                <div
                  key={link.path}
                  className="quick-link"
                  onClick={() => navigate(link.path)}
                  style={{ ['--quick-accent' as string]: link.color, ['--quick-bg' as string]: link.bg } as React.CSSProperties}
                >
                  <span className="quick-link-icon">
                    {link.icon}
                  </span>
                  <span className="quick-link-text">
            <span className="quick-link-label">{link.label}</span>
            <span className="quick-link-sub">{link.sub}</span>
          </span>
                  <span className="quick-link-arrow">→</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function adjustColor(hex: string, amount: number): string {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.min(255, Math.max(0, (num >> 16) + amount));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00ff) + amount));
  const b = Math.min(255, Math.max(0, (num & 0x0000ff) + amount));
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}
