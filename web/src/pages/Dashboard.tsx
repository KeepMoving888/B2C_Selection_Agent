import {
  AuditOutlined,
  BarChartOutlined,
  CarryOutOutlined,
  CommentOutlined,
  DollarOutlined,
  ShopOutlined,
  StockOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Space, Spin, Typography } from 'antd';
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

const SCORE_COLORS: Record<string, string> = {
  利润空间: 'linear-gradient(90deg, #16a34a, #4ade80)',
  趋势热度: 'linear-gradient(90deg, #7c3aed, #a78bfa)',
  竞争强度: 'linear-gradient(90deg, #0891b2, #22d3ee)',
  评论洞察: 'linear-gradient(90deg, #2563eb, #60a5fa)',
};

const quickLinks = [
  { path: '/market-analysis', label: '市场分析', icon: <BarChartOutlined />, color: '#2563eb' },
  { path: '/review-insights', label: '评论洞察', icon: <CommentOutlined />, color: '#0891b2' },
  { path: '/profit-analysis', label: '利润测算', icon: <DollarOutlined />, color: '#16a34a' },
  { path: '/trend-seasonal', label: '趋势季节', icon: <StockOutlined />, color: '#f59e0b' },
  { path: '/suppliers', label: '供应商', icon: <ShopOutlined />, color: '#7c3aed' },
  { path: '/compliance', label: '合规检查', icon: <AuditOutlined />, color: '#dc2626' },
  { path: '/action-plan', label: '行动计划', icon: <CarryOutOutlined />, color: '#d97706' },
];

function VerdictBanner({ report }: { report: AnalysisReport }) {
  const profile = report.market_analysis.market_profile;
  const trend = report.trend_analysis.trend_direction;
  const trendIcon = trend === 'rising' ? '↗' : trend === 'stable' ? '→' : '↘';

  return (
    <div className="verdict-banner">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 20 }}>
        <div>
          <div style={{ color: '#64748b', fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>分析对象</div>
          <div style={{ color: '#0f172a', fontSize: 26, fontWeight: 800 }}>{report.keyword.toUpperCase()} · {profile.name}</div>
          <div style={{ color: '#64748b', fontSize: 13, marginTop: 6, fontWeight: 500 }}>
            预算区间 {report.budget} · 市场均价 {profile.currency}${report.market_analysis.avg_price} · 平均评分 {report.market_analysis.avg_rating}⭐
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="badge" style={{ background: '#f1f5f9', color: '#475569', fontSize: 13 }}>{trendIcon} 趋势 {trend.toUpperCase()}</span>
          <span className="verdict-pill" style={{ backgroundColor: report.verdict_color }}>
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
  const trendSub = trend.trend_direction === 'rising' ? '搜索热度上升' : trend.trend_direction === 'stable' ? '搜索热度稳定' : '搜索热度下降';

  const metrics = [
    { label: '综合评分', value: `${report.overall_score}/${report.max_score}`, color: '#1e40af', icon: '🏆', sub: `等级 ${report.grade}` },
    { label: '毛利率', value: profit.gross_margin_pct, color: '#2563eb', icon: '💰', sub: `单件毛利 $${profit.gross_profit_per_unit}` },
    { label: '盈亏平衡', value: `${breakeven} 件`, color: '#0891b2', icon: '⚖️', sub: '覆盖固定成本' },
    { label: '趋势热度', value: trend.trend_direction.toUpperCase(), color: '#7c3aed', icon: '📈', sub: trendSub },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, marginBottom: 20 }}>
      {metrics.map((m) => (
        <div key={m.label} className="metric-box" style={{ ['--accent' as string]: m.color }}>
          <div className="metric-icon">{m.icon}</div>
          <div className="metric-label">{m.label}</div>
          <div className="metric-value" style={{ color: m.color }}>{m.value}</div>
          <div className="metric-sub">{m.sub}</div>
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
      polar: {
        radius: '65%',
      },
      angleAxis: {
        type: 'category',
        data: [...categories, categories[0]],
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#1e293b', fontSize: 14, fontWeight: 800 },
      },
      radiusAxis: {
        min: 0,
        max: 100,
        axisLine: { show: false },
        axisLabel: { color: '#64748b', fontWeight: 700 },
        splitLine: { lineStyle: { color: '#e2e8f0' } },
      },
      series: [{
        type: 'line',
        coordinateSystem: 'polar',
        data: [...normalized, normalized[0]],
        areaStyle: { color: 'rgba(37, 99, 235, 0.22)' },
        lineStyle: { color: '#2563eb', width: 2.5 },
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: { color: '#2563eb' },
      }],
    };
  }, [report]);

  return <ReactECharts option={option} style={{ height: 420 }} />;
}

function ScoreBreakdown({ report }: { report: AnalysisReport }) {
  return (
    <div>
      <div className="info-card-title">📊 五维评分拆解</div>
      {Object.entries(report.score_breakdown).map(([name, score]) => {
        const maxV = MAX_VALUES[name] ?? 25;
        const pct = Math.min(100, Math.max(0, (score / maxV) * 100));
        return (
          <div key={name} className="score-row">
            <div className="score-name">{name}</div>
            <div className="score-bar-bg"><div className="score-bar-fill" style={{ width: `${pct}%`, background: SCORE_COLORS[name] }} /></div>
            <div className="score-value">{score}/{maxV}</div>
          </div>
        );
      })}
    </div>
  );
}

function Conclusion({ report }: { report: AnalysisReport }) {
  const market = report.market_analysis;
  const profile = market.market_profile;

  return (
    <div>
      <div className="info-card-title">💡 核心结论</div>
      <p style={{ color: '#475569', lineHeight: 1.75, margin: 0, fontSize: 14 }}>
        关键词 <strong style={{ color: '#2563eb' }}>{report.keyword}</strong>
        在 <strong>{profile.name}</strong> 市场平均售价
        <strong> {profile.currency}${market.avg_price}</strong>，
        毛利率 <strong style={{ color: report.verdict_color }}>{report.profit_analysis.gross_margin_pct}</strong>，
        趋势 <strong>{report.trend_analysis.trend_direction.toUpperCase()}</strong>。
        综合判定为 <strong style={{ color: report.verdict_color }}>{report.verdict}</strong>。
      </p>
      <div style={{ display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap' }}>
        <span className="badge" style={{ background: '#eff6ff', color: '#1d4ed8' }}>竞品 {market.competitors.length} 款</span>
        <span className="badge" style={{ background: '#dbeafe', color: '#1e40af' }}>平均评分 {market.avg_rating}⭐</span>
        <span className="badge" style={{ background: '#f1f5f9', color: '#334155' }}>总评论 {market.avg_reviews.toLocaleString()}+</span>
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
      <div style={{ marginBottom: 24 }}>
        <div className="page-header">选品决策驾驶舱</div>
        <Card style={{ borderRadius: 16 }}>
          <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
        </Card>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>Multi-Agent 协同分析中，请稍候...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="决策看板" />}

      {!loading && report && (
        <>
          <VerdictBanner report={report} />
          <KpiCards report={report} />

          <div className="info-card" style={{ marginBottom: 20, padding: 18 }}>
            <div className="info-card-title">🎯 选品决策看板</div>
            <Row gutter={[24, 24]}>
              <Col xs={24} lg={14}>
                <RadarChart report={report} />
              </Col>
              <Col xs={24} lg={10}>
                <ScoreBreakdown report={report} />
                <div style={{ marginTop: 14 }}>
                  <Conclusion report={report} />
                </div>
              </Col>
            </Row>
          </div>

          <Card title="📂 深度分析入口" style={{ borderRadius: 16 }}>
            <Space size={[16, 16]} wrap>
              {quickLinks.map((link) => (
                <div
                  key={link.path}
                  onClick={() => navigate(link.path)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '14px 18px',
                    borderRadius: 12,
                    background: '#fff',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 2px 8px rgba(15,23,42,0.04)',
                    cursor: 'pointer',
                    transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                    minWidth: 140,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 6px 16px rgba(15,23,42,0.08)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'none';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(15,23,42,0.04)';
                  }}
                >
                  <span style={{ color: link.color, fontSize: 20 }}>{link.icon}</span>
                  <Text strong style={{ color: '#0f172a' }}>{link.label}</Text>
                </div>
              ))}
            </Space>
          </Card>
        </>
      )}
    </div>
  );
}
