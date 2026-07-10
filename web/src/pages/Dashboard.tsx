import {
  AuditOutlined,
  BarChartOutlined,
  CarryOutOutlined,
  CommentOutlined,
  DollarOutlined,
  FallOutlined,
  FileTextOutlined,
  RiseOutlined,
  ShopOutlined,
  StarOutlined,
  StockOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Spin, Typography } from 'antd';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import { useEffect, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

const { Text } = Typography;

const MAX_VALUES: Record<string, number> = {
  利润空间: 40,
  趋势热度: 25,
  竞争强度: 20,
  评论洞察: 15,
};

const SCORE_COLORS: Record<string, { start: string; end: string; bg: string }> = {
  利润空间: { start: '#059669', end: '#34d399', bg: '#ecfdf5' },
  趋势热度: { start: '#7c3aed', end: '#a78bfa', bg: '#f5f3ff' },
  竞争强度: { start: '#0891b2', end: '#22d3ee', bg: '#ecfeff' },
  评论洞察: { start: '#2563eb', end: '#60a5fa', bg: '#eff6ff' },
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
  const color = isRising ? '#059669' : isStable ? '#d97706' : '#dc2626';
  const bg = isRising ? '#ecfdf5' : isStable ? '#fffbeb' : '#fef2f2';
  const border = isRising ? '#d1fae5' : isStable ? '#fde68a' : '#fee2e2';
  const Icon = isRising ? RiseOutlined : isStable ? FallOutlined : FallOutlined;
  const label = isRising ? '上升' : isStable ? '稳定' : '下滑';

  return (
    <span className="badge" style={{ background: bg, color, border: `1px solid ${border}`, fontSize: 13, fontWeight: 800 }}>
      <Icon style={{ fontSize: 12 }} /> 趋势 {label}
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
  const trendColor = trend.trend_direction === 'rising' ? '#059669' : trend.trend_direction === 'stable' ? '#d97706' : '#dc2626';
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
      sub: `单件毛利 USD ${profit.gross_profit_per_unit.toFixed(2)}`,
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
      trend: `旺季集中在 ${trend.peak_months.slice(0, 3).join('、')} 月`,
      accent: METRIC_ACCENTS['趋势热度'],
    },
  ];

  return (
    <div className="metric-grid">
      {metrics.map((m) => (
        <div key={m.label} className="metric-box" style={{ ['--accent' as string]: m.accent.color, ['--accent-bg' as string]: m.accent.bg, ['--accent-light' as string]: m.accent.light } as React.CSSProperties}>
          <div className="metric-top">
            <div className="metric-icon">{m.accent.icon}</div>
            <div className="metric-label">{m.label}</div>
          </div>
          <div className="metric-value" style={{ color: m.label === '趋势热度' ? trendColor : m.accent.color }}>
            {m.value}
          </div>
          <div className="metric-sub">{m.sub}</div>
          <div className="metric-trend">
            <span style={{ color: m.label === '趋势热度' ? trendColor : m.accent.color }}>●</span> {m.trend}
          </div>
        </div>
      ))}
    </div>
  );
}

function RadarChart({ report }: { report: AnalysisReport }) {
  const option: EChartsOption = useMemo(() => {
    const categories = Object.keys(report.score_breakdown);
    const values = Object.values(report.score_breakdown);
    const normalized = categories.map((cat, i) => Math.min(100, (values[i] / MAX_VALUES[cat]) * 100));

    return {
      color: ['#2563eb'],
      tooltip: {
        trigger: 'item',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        textStyle: { color: '#1e293b', fontFamily: 'var(--font-sans)' },
        formatter: (params: any) => {
          const idx = params.dataIndex % normalized.length;
          const raw = values[idx];
          const max = MAX_VALUES[categories[idx]];
          return `<div style="font-weight:700">${categories[idx]}</div>
                  <div style="color:#64748b;font-size:12px">得分 ${raw} / ${max}</div>
                  <div style="color:#2563eb;font-weight:800">占比 ${normalized[idx].toFixed(1)}%</div>`;
        },
      },
      polar: { radius: '62%' },
      angleAxis: {
        type: 'category',
        data: [...categories, categories[0]],
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#475569', fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-sans)' },
        splitLine: { lineStyle: { color: '#f1f5f9' } },
      },
      radiusAxis: {
        min: 0,
        max: 100,
        axisLine: { show: false },
        axisLabel: { color: '#94a3b8', fontWeight: 600, fontFamily: 'var(--font-sans)' },
        splitLine: { lineStyle: { color: '#e2e8f0' } },
      },
      series: [{
        type: 'line',
        coordinateSystem: 'polar',
        data: [...normalized, normalized[0]],
        areaStyle: {
          color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.35)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.06)' },
          ]),
        },
        lineStyle: { color: '#2563eb', width: 3 },
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: { color: '#2563eb', borderColor: '#fff', borderWidth: 2.5, shadowBlur: 8, shadowColor: 'rgba(37,99,235,0.25)' },
        label: {
          show: true,
          position: 'top',
          formatter: (params: any) => {
            const idx = params.dataIndex;
            return idx < normalized.length ? `${Math.round(normalized[idx])}` : '';
          },
          color: '#2563eb',
          fontSize: 11,
          fontWeight: 800,
          fontFamily: 'var(--font-sans)',
        },
      }],
    };
  }, [report]);

  return <ReactECharts option={option} style={{ height: 400 }} />;
}

function ScoreBreakdown({ report }: { report: AnalysisReport }) {
  const total = Object.values(report.score_breakdown).reduce((a, b) => a + b, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="info-card-title">五维评分拆解</div>
      <div className="section-desc">
        各项得分对综合评分的贡献度与相对表现，帮助定位优势与短板。
      </div>
      <div style={{ flex: 1 }}>
        {Object.entries(report.score_breakdown).map(([name, score]) => {
          const maxV = MAX_VALUES[name] ?? 25;
          const pct = Math.min(100, Math.max(0, (score / maxV) * 100));
          const contribution = total > 0 ? (score / total) * 100 : 0;
          const color = SCORE_COLORS[name];
          return (
            <div key={name} className="score-row">
              <div className="score-name">{name}</div>
              <div className="score-bar-bg">
                <div className="score-bar-fill" style={{ width: `${pct}%`, ['--bar-start' as string]: color.start, ['--bar-end' as string]: color.end }} />
              </div>
              <div className="score-value">
                <span>{score}</span>
                <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 700, marginLeft: 2 }}>/{maxV}</span>
              </div>
              <div className="score-contribution">{contribution.toFixed(1)}%</div>
            </div>
          );
        })}
      </div>
      <div className="dashboard-insight-box">
        <strong>综合判定：</strong>
        该品类在 <span style={{ color: '#059669', fontWeight: 800 }}>利润空间</span> 与 <span style={{ color: '#7c3aed', fontWeight: 800 }}>趋势热度</span> 维度表现突出，
        建议结合评论洞察进一步验证差异化机会。
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
      <div className="info-card-title">核心结论</div>
      <p style={{ color: 'var(--saas-text-secondary)', lineHeight: 1.85, margin: 0, fontSize: 14 }}>
        关键词 <strong style={{ color: '#2563eb' }}>{report.keyword}</strong>
        在 <strong>{profile.name}</strong> 市场平均售价
        <strong> {profile.currency}{market.avg_price}</strong>，
        毛利率 <strong style={{ color: report.verdict_color }}>{report.profit_analysis.gross_margin_pct}</strong>，
        趋势 <strong>{trendText}</strong>。
        综合判定为 <strong style={{ color: report.verdict_color }}>{report.verdict}</strong>。
      </p>
      <div style={{ display: 'flex', gap: 10, marginTop: 18, flexWrap: 'wrap' }}>
        <span className="badge" style={{ background: '#eff6ff', color: '#1d4ed8', border: '1px solid #dbeafe' }}>竞品 {market.competitors.length} 款</span>
        <span className="badge" style={{ background: '#dbeafe', color: '#1e40af', border: '1px solid #bfdbfe' }}>平均评分 {market.avg_rating}</span>
        <span className="badge" style={{ background: '#f1f5f9', color: '#334155', border: '1px solid #e2e8f0' }}>总评论 {market.avg_reviews.toLocaleString()}+</span>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { report, lastSearch, loading, analyze } = useReport();

  useEffect(() => {
    dispatch(setPageTitle('首页雷达'));
  }, [dispatch]);

  return (
    <div className="page-container">
      <div className="page-hero">
        <div>
          <div className="page-header">选品决策驾驶舱</div>
          <div className="page-subtitle">输入关键词，获取多维度选品分析与决策建议</div>
        </div>
        {report && (
          <span className="section-badge">
            <BarChartOutlined /> 当前分析：{report.keyword}
          </span>
        )}
      </div>
      <Card className="search-card">
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>Multi-Agent 协同分析中，请稍候...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="决策看板" />}

      {!loading && report && (
        <>
          <VerdictBanner report={report} />
          <KpiCards report={report} />

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={14}>
              <div className="info-card" style={{ height: '100%' }}>
                <div className="info-card-title">选品决策看板</div>
                <RadarChart report={report} />
              </div>
            </Col>
            <Col xs={24} lg={10} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div className="info-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <ScoreBreakdown report={report} />
              </div>
              <div className="info-card">
                <Conclusion report={report} />
              </div>
            </Col>
          </Row>

          <div className="info-card">
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
                    <Text strong style={{ color: 'inherit', fontSize: 15 }}>{link.label}</Text>
                    <Text style={{ color: 'var(--saas-text-muted)', fontSize: 12, fontWeight: 500 }}>{link.sub}</Text>
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
