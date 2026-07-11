import { Button, Card, Col, Row, Spin, Tag } from 'antd';
import {
  BarChartOutlined,
  DollarOutlined,
  DownloadOutlined,
  FallOutlined,
  FireOutlined,
  LinkOutlined,
  RiseOutlined,
  SearchOutlined,
  ShoppingOutlined,
  StarFilled,
  TrophyOutlined,
} from '@ant-design/icons';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import { useEffect, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

const softPalette = ['#93c5fd', '#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af'];

function PriceSalesChart({ report }: { report: AnalysisReport }) {
  const competitors = report.market_analysis.competitors.slice(0, 10);

  const option: EChartsOption = useMemo(() => {
    const maxPrice = Math.max(...competitors.map((p) => p.price));
    const maxSales = Math.max(...competitors.map((p) => p.estimated_monthly_sales));

    return {
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'var(--saas-border)', textStyle: { color: 'var(--saas-text)' } },
      legend: { orient: 'horizontal', top: 0, right: 0, textStyle: { color: 'var(--saas-text-secondary)', fontWeight: 700 } },
      grid: { left: 20, right: 60, top: 50, bottom: 20, containLabel: true },
      xAxis: { type: 'category', data: competitors.map((p) => p.brand), axisLine: { lineStyle: { color: 'var(--saas-border)' } }, axisLabel: { color: 'var(--saas-text-muted)', fontWeight: 600 } },
      yAxis: [
        { type: 'value', name: '售价 (USD)', max: maxPrice * 1.28, axisLine: { show: false }, splitLine: { lineStyle: { color: 'var(--saas-border)' } }, axisLabel: { color: 'var(--saas-text-muted)', fontWeight: 600 } },
        { type: 'value', name: '月销量', max: maxSales * 1.28, axisLine: { show: false }, splitLine: { show: false }, axisLabel: { color: 'var(--saas-text-muted)', fontWeight: 600 } },
      ],
      series: [
        {
          type: 'bar',
          name: '售价',
          data: competitors.map((p, i) => ({ value: p.price, itemStyle: { color: softPalette[i % softPalette.length], borderRadius: [6, 6, 0, 0] } })),
          barWidth: '45%',
          label: { show: true, position: 'top', formatter: '${c}', color: 'var(--saas-text)', fontSize: 10, fontWeight: 700 },
        },
        {
          type: 'line',
          name: '月销量',
          yAxisIndex: 1,
          data: competitors.map((p) => p.estimated_monthly_sales),
          smooth: true,
          lineStyle: { color: '#f59e0b', width: 3 },
          itemStyle: { color: '#f59e0b', borderColor: '#fff', borderWidth: 2 },
          label: { show: true, position: 'top', formatter: '{c}', color: '#b45309', fontSize: 10, fontWeight: 700 },
        },
      ],
    };
  }, [competitors]);

  return <ReactECharts option={option} style={{ height: 360 }} />;
}

function CompetitorCard({ product, index }: { product: any; index: number }) {
  const parts = product.subtitle?.split(' · ') || [];
  const subtitle = parts[1] || product.subtitle || '';
  const accent = softPalette[index % softPalette.length];

  return (
    <div className="competitor-card" style={{ ['--competitor-accent' as string]: accent } as React.CSSProperties}>
      <div className="competitor-rank">{index + 1}</div>
      <a href={product.link} target="_blank" rel="noreferrer" className="competitor-image-link">
        <img src={product.image} alt="" className="competitor-image" />
      </a>
      <div className="competitor-info">
        <a href={product.link} target="_blank" rel="noreferrer" className="competitor-title-link">
          <div className="competitor-title">{product.title}</div>
        </a>
        <div className="competitor-store">{product.store} · {subtitle}</div>
        <div className="competitor-metrics">
          <Tag className="competitor-price-tag">${product.price}</Tag>
          <span className="competitor-metric"><StarFilled style={{ color: '#f59e0b' }} /> {product.rating}</span>
          <span className="competitor-metric">{product.review_count.toLocaleString()} 评论</span>
          <span className="competitor-metric"><ShoppingOutlined style={{ color: 'var(--saas-primary)' }} /> 月销 {product.estimated_monthly_sales.toLocaleString()}</span>
        </div>
      </div>
      <a href={product.link} target="_blank" rel="noreferrer" className="competitor-link-btn">
        <LinkOutlined /> 查看
      </a>
    </div>
  );
}

// 选品行业配色法则：红色 = 上升/热门/积极；绿色/蓝色 = 下降/冷却/消极；黄色 = 警惕/稳定
const TREND_COLORS: Record<string, { color: string; bg: string; border: string; icon: React.ReactNode; label: string }> = {
  rising: { color: '#dc2626', bg: '#fef2f2', border: '#fee2e2', icon: <RiseOutlined />, label: '上升' },
  stable: { color: '#d97706', bg: '#fffbeb', border: '#fde68a', icon: <FireOutlined />, label: '稳定' },
  falling: { color: '#059669', bg: '#ecfdf5', border: '#d1fae5', icon: <FallOutlined />, label: '下滑' },
};

const COMPETITION_COLORS: Record<string, { color: string; bg: string; border: string; label: string }> = {
  low: { color: '#059669', bg: '#ecfdf5', border: '#d1fae5', label: '低竞争' },
  medium: { color: '#d97706', bg: '#fffbeb', border: '#fde68a', label: '中等' },
  high: { color: '#dc2626', bg: '#fef2f2', border: '#fee2e2', label: '高竞争' },
};

function OpportunityProduct({ product }: { product: any }) {
  return (
    <a
      href={product.link}
      target="_blank"
      rel="noreferrer"
      className="opportunity-product"
      title={product.title}
    >
      <img src={product.image} alt="" className="opportunity-product-image" />
      <div className="opportunity-product-info">
        <div className="opportunity-product-title">{product.title}</div>
        <div className="opportunity-product-meta">
          <span>${product.price}</span>
          <span>·</span>
          <span><StarFilled style={{ color: '#f59e0b' }} /> {product.rating}</span>
        </div>
        <div className="opportunity-product-sales">月销 {product.estimated_monthly_sales.toLocaleString()}</div>
      </div>
    </a>
  );
}

function exportCompetitorsCsv(report: AnalysisReport) {
  const competitors = report.market_analysis.competitors;
  const headers = ['rank', 'brand', 'store', 'title', 'price', 'rating', 'review_count', 'bsr', 'estimated_monthly_sales'];
  const rows = competitors.map((p, i) => [i + 1, p.brand, p.store, p.title, p.price, p.rating, p.review_count, p.bsr, p.estimated_monthly_sales]);
  const csvContent = [headers.join(','), ...rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n');
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${report.keyword.replace(/\s+/g, '_').toLowerCase()}_${report.market.toLowerCase()}_competitors.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function KeywordSummary({ report }: { report: AnalysisReport }) {
  let summary = report.market_analysis.keyword_summary;
  const opportunities = report.market_analysis.keyword_opportunities || [];

  // 旧版本报告或 API 返回缺少 keyword_summary 时，从 opportunities 推导兜底数据
  if (!summary && opportunities.length > 0) {
    summary = {
      search_volume: opportunities.reduce((sum, o) => sum + o.search_volume, 0),
      trend: opportunities[0].trend,
      competition: opportunities[0].competition,
      cpc: opportunities.reduce((sum, o) => sum + o.cpc, 0) / opportunities.length,
      opportunity_score: Math.round(opportunities.reduce((sum, o) => sum + o.opportunity_score, 0) / opportunities.length),
      top_niche_keywords: opportunities.slice(0, 5).map((o) => o.keyword),
    };
  }

  if (!summary) return null;

  const trend = TREND_COLORS[summary.trend];
  const comp = COMPETITION_COLORS[summary.competition];
  const scoreColor = summary.opportunity_score >= 70 ? '#dc2626' : summary.opportunity_score >= 45 ? '#d97706' : '#059669';

  return (
    <div className="info-card" style={{ marginBottom: 24 }}>
      <div className="info-card-title">
        <SearchOutlined style={{ color: 'var(--saas-primary)' }} /> 关键词数据概览
      </div>
      <div className="section-desc">
        「{report.keyword}」在 {report.market_analysis.market_profile.name} 的搜索热度、竞争度与流量成本核心指标。
      </div>
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}>
          <div style={{ textAlign: 'center', padding: 16, background: '#f8fafc', borderRadius: 10, border: '1px solid var(--saas-border-subtle)' }}>
            <div style={{ fontSize: 11, color: 'var(--saas-text-muted)', fontWeight: 800, marginBottom: 6 }}>月搜索量</div>
            <div style={{ fontSize: 22, fontWeight: 900, color: '#2563eb' }}>{summary.search_volume.toLocaleString()}</div>
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div style={{ textAlign: 'center', padding: 16, background: trend.bg, borderRadius: 10, border: `1px solid ${trend.border}` }}>
            <div style={{ fontSize: 11, color: trend.color, fontWeight: 800, marginBottom: 6 }}>趋势</div>
            <div style={{ fontSize: 22, fontWeight: 900, color: trend.color }}>{trend.icon} {trend.label}</div>
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div style={{ textAlign: 'center', padding: 16, background: comp.bg, borderRadius: 10, border: `1px solid ${comp.border}` }}>
            <div style={{ fontSize: 11, color: comp.color, fontWeight: 800, marginBottom: 6 }}>竞争度</div>
            <div style={{ fontSize: 22, fontWeight: 900, color: comp.color }}>{comp.label}</div>
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div style={{ textAlign: 'center', padding: 16, background: '#fffbeb', borderRadius: 10, border: '1px solid #fde68a' }}>
            <div style={{ fontSize: 11, color: '#d97706', fontWeight: 800, marginBottom: 6 }}>参考 CPC</div>
            <div style={{ fontSize: 22, fontWeight: 900, color: '#d97706' }}>${summary.cpc}</div>
          </div>
        </Col>
      </Row>
      <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--saas-text-secondary)' }}>机会评分：</span>
        <span style={{ padding: '5px 14px', borderRadius: 20, fontSize: 14, fontWeight: 900, background: scoreColor + '12', color: scoreColor, border: `1px solid ${scoreColor}30` }}>
          <TrophyOutlined /> {summary.opportunity_score}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--saas-text-secondary)' }}>热门细分词：</span>
        {summary.top_niche_keywords.map((kw, i) => (
          <span key={i} className="badge" style={{ background: '#eff6ff', color: '#1d4ed8', border: '1px solid #dbeafe' }}>{kw}</span>
        ))}
      </div>
    </div>
  );
}

function KeywordOpportunityRow({ opp, index }: { opp: any; index: number }) {
  const trend = TREND_COLORS[opp.trend];
  const comp = COMPETITION_COLORS[opp.competition];
  const scoreColor = opp.opportunity_score >= 70 ? '#dc2626' : opp.opportunity_score >= 45 ? '#d97706' : '#059669';
  const displayProduct = opp.products[0];

  return (
    <div key={index} className="keyword-opportunity-card">
      <div className="keyword-opportunity-rank" style={{ color: scoreColor, background: scoreColor + '10' }}>
        <div className="keyword-opportunity-rank-num">{index + 1}</div>
        <div className="keyword-opportunity-rank-label">TOP</div>
      </div>

      <div className="keyword-opportunity-keyword-block">
        <div className="keyword-opportunity-keyword" style={{ color: scoreColor }} title={opp.keyword}>
          {opp.keyword}
        </div>
        <div className="keyword-opportunity-score" style={{ color: scoreColor }}>
          <TrophyOutlined /> 机会分 {opp.opportunity_score}
        </div>
      </div>

      <div className="keyword-opportunity-metrics">
        <div className="keyword-opportunity-metric">
          <div className="keyword-opportunity-metric-label">月搜索量</div>
          <div className="keyword-opportunity-metric-value" style={{ color: '#2563eb' }}>
            <SearchOutlined style={{ fontSize: 12, marginRight: 4 }} />
            {opp.search_volume.toLocaleString()}
          </div>
        </div>
        <div className="keyword-opportunity-metric">
          <div className="keyword-opportunity-metric-label">趋势</div>
          <div className="keyword-opportunity-metric-value" style={{ color: trend.color }}>
            {trend.icon} {trend.label}
          </div>
        </div>
        <div className="keyword-opportunity-metric">
          <div className="keyword-opportunity-metric-label">竞争度</div>
          <div className="keyword-opportunity-metric-value" style={{ color: comp.color }}>
            {comp.label}
          </div>
        </div>
        <div className="keyword-opportunity-metric">
          <div className="keyword-opportunity-metric-label">CPC</div>
          <div className="keyword-opportunity-metric-value" style={{ color: '#d97706' }}>
            <DollarOutlined style={{ fontSize: 12, marginRight: 4 }} />
            ${opp.cpc}
          </div>
        </div>
      </div>

      <div className="keyword-opportunity-product">
        {displayProduct && <OpportunityProduct product={displayProduct} />}
      </div>
    </div>
  );
}

function KeywordOpportunities({ report }: { report: AnalysisReport }) {
  const opportunities = report.market_analysis.keyword_opportunities || [];

  return (
    <div className="info-card">
      <div className="info-card-title">
        <SearchOutlined style={{ color: 'var(--saas-primary)' }} /> 细分关键词机会
      </div>
      <div className="section-desc">
        基于搜索量、竞争度与趋势热度，挖掘「{report.keyword}」类目下具备差异化进入机会的细分关键词及对应参考产品。
      </div>
      <div className="keyword-opportunity-grid">
        {opportunities.map((opp, i) => (
          <KeywordOpportunityRow key={i} opp={opp} index={i} />
        ))}
      </div>
    </div>
  );
}

export default function MarketAnalysis() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();

  useEffect(() => {
    dispatch(setPageTitle('市场分析'));
  }, [dispatch]);

  return (
    <div className="page-container">
      <div className="page-hero">
        <div>
          <div className="page-header">市场分析</div>
          <div className="page-subtitle">竞品价格带、销量分布与头部 Listing 对比，定位市场机会</div>
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
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>正在分析市场数据...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="市场分析" />}

      {!loading && report && (
        <>
          <div className="market-summary-banner">
            <div className="market-summary-main">
              <div className="market-summary-label">分析对象</div>
              <div className="market-summary-title">{report.keyword} · {report.market_analysis.market_profile.name}</div>
              <div className="market-summary-tags">
                <span className="market-summary-tag">市场 {report.market}</span>
                <span className="market-summary-tag">均价 USD {report.market_analysis.avg_price}</span>
                <span className="market-summary-tag">平均评分 {report.market_analysis.avg_rating} / 5.0</span>
              </div>
            </div>
          </div>

          <KeywordSummary report={report} />

          <div className="info-card" style={{ marginBottom: 24, padding: '18px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
              <div>
                <div className="info-card-title" style={{ marginBottom: 4, paddingBottom: 0, borderBottom: 'none' }}>
                  <BarChartOutlined style={{ color: 'var(--saas-primary)' }} /> 市场竞争格局
                </div>
                <div style={{ color: 'var(--saas-text-muted)', fontSize: 13, fontWeight: 500 }}>
                  已分析 <strong style={{ color: 'var(--saas-text)' }}>{report.market_analysis.competitors.length}</strong> 款竞品 · 当前展示 TOP10 · 导出可获取全部数据
                </div>
              </div>
              <Button type="primary" icon={<DownloadOutlined />} onClick={() => exportCompetitorsCsv(report)} size="large">
                导出竞品对比表 (CSV)
              </Button>
            </div>
          </div>

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={15}>
              <div className="info-card">
                <div className="info-card-title">竞品价格带与月销量分布</div>
                <div className="section-desc">
                  柱状图展示头部竞品售价，折线叠加月销量；识别高价高销与低价走量的机会区间。
                </div>
                <PriceSalesChart report={report} />
              </div>
            </Col>
            <Col xs={24} lg={9}>
              <div className="info-card" style={{ maxHeight: 640, overflow: 'auto' }}>
                <div className="info-card-title">头部竞品 TOP10</div>
                <div className="section-desc" style={{ marginBottom: 14 }}>
                  已分析 {report.market_analysis.competitors.length} 款竞品，当前展示按销量与 relevance 排序的头部 TOP10。
                </div>
                {report.market_analysis.competitors.slice(0, 10).map((p: any, i: number) => (
                  <CompetitorCard key={i} product={p} index={i} />
                ))}
              </div>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
            <Col xs={24}>
              <KeywordOpportunities report={report} />
            </Col>
          </Row>
        </>
      )}
    </div>
  );
}
