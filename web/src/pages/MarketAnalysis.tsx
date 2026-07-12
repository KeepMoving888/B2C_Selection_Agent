import { Button, Card, Col, Row, Select, Space, Spin, Tag } from 'antd';
import {
  ApartmentOutlined,
  BarChartOutlined,
  BulbOutlined,
  DollarOutlined,
  DownloadOutlined,
  FallOutlined,
  FireOutlined,
  GlobalOutlined,
  LinkOutlined,
  RiseOutlined,
  SearchOutlined,
  ShoppingOutlined,
  StarFilled,
  TrophyOutlined,
} from '@ant-design/icons';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import { useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useMobile } from '../hooks/useMobile';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';
import { getMarketCurrency } from '../utils/currency';

const softPalette = ['#93c5fd', '#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af'];

const COUNTRY_COLORS: Record<string, string> = {
  US: '#dc2626',
  UK: '#2563eb',
  DE: '#f59e0b',
  JP: '#0891b2',
  CA: '#7c3aed',
};

const SEGMENT_COLORS = ['#2563eb', '#059669', '#d97706', '#7c3aed', '#0891b2', '#db2777', '#64748b'];

function PriceSalesChart({ report }: { report: AnalysisReport }) {
  const competitors = report.market_analysis.competitors.slice(0, 10);
  const isMobile = useMobile();
  const { symbol } = getMarketCurrency(report.market);

  const option: EChartsOption = useMemo(() => {
    const maxPrice = Math.max(...competitors.map((p) => p.price));
    const maxSales = Math.max(...competitors.map((p) => p.estimated_monthly_sales));

    return {
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(30, 41, 59, 0.92)', borderWidth: 0, padding: [5, 8], confine: true, textStyle: { color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: 11 }, extraCssText: 'max-width:180px !important;width:auto !important;min-width:0 !important;word-wrap:break-word !important;white-space:normal !important;border-radius:4px !important;box-shadow:0 2px 8px rgba(0,0,0,0.15) !important;backdrop-filter:blur(4px) !important;' },
      legend: { orient: 'horizontal', top: 0, right: isMobile ? undefined : 0, left: isMobile ? 'center' : undefined, itemGap: isMobile ? 12 : 20, textStyle: { color: 'var(--saas-text-secondary)', fontWeight: 700, fontSize: isMobile ? 10 : 12 } },
      grid: { left: isMobile ? 6 : 14, right: isMobile ? 6 : 60, top: isMobile ? 34 : 46, bottom: isMobile ? 16 : 20, containLabel: true },
      xAxis: { type: 'category', data: competitors.map((p) => p.brand), axisLine: { lineStyle: { color: 'var(--saas-border)' } }, axisLabel: { color: 'var(--saas-text-muted)', fontWeight: 600, fontSize: isMobile ? 9 : 11, interval: isMobile ? 1 : 0, rotate: isMobile ? 30 : 0 } },
      yAxis: [
        { type: 'value', name: `售价 (${symbol})`, nameTextStyle: { color: 'var(--saas-text-muted)', fontSize: isMobile ? 10 : 11, padding: isMobile ? [0, 0, 0, -20] : undefined }, max: maxPrice * 1.28, axisLine: { show: false }, splitLine: { lineStyle: { color: 'var(--saas-border)' } }, axisLabel: { color: 'var(--saas-text-muted)', fontWeight: 600, fontSize: isMobile ? 9 : 11 } },
        { type: 'value', name: '月销量', nameTextStyle: { color: 'var(--saas-text-muted)', fontSize: isMobile ? 10 : 11 }, max: maxSales * 1.28, axisLine: { show: false }, splitLine: { show: false }, axisLabel: { color: 'var(--saas-text-muted)', fontWeight: 600, fontSize: isMobile ? 9 : 11 } },
      ],
      series: [
        {
          type: 'bar',
          name: '售价',
          data: competitors.map((p, i) => ({ value: p.price, itemStyle: { color: softPalette[i % softPalette.length], borderRadius: [6, 6, 0, 0] } })),
          barWidth: isMobile ? '40%' : '45%',
          label: { show: !isMobile, position: 'top', formatter: `${symbol}{c}`, color: 'var(--saas-text)', fontSize: 10, fontWeight: 700 },
        },
        {
          type: 'line',
          name: '月销量',
          yAxisIndex: 1,
          data: competitors.map((p) => p.estimated_monthly_sales),
          smooth: true,
          lineStyle: { color: '#f59e0b', width: 3 },
          itemStyle: { color: '#f59e0b', borderColor: '#fff', borderWidth: 2 },
          label: { show: !isMobile, position: 'top', formatter: '{c}', color: '#b45309', fontSize: 10, fontWeight: 700 },
        },
      ],
    };
  }, [competitors, isMobile, symbol]);

  return <ReactECharts option={option} style={{ height: isMobile ? 300 : 360, width: '100%' }} />;
}

function CompetitorCard({ product, index, market }: { product: any; index: number; market: string }) {
  const parts = product.subtitle?.split(' · ') || [];
  const subtitle = parts[1] || product.subtitle || '';
  const accent = softPalette[index % softPalette.length];
  const { symbol } = getMarketCurrency(market);

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
          <Tag className="competitor-price-tag">{symbol}{product.price.toFixed(2)}</Tag>
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
  const { symbol } = getMarketCurrency(report.market);

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
            <div style={{ fontSize: 22, fontWeight: 900, color: '#d97706' }}>{symbol}{summary.cpc.toFixed(2)}</div>
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

function KeywordOpportunityRow({ opp, index, market, budget }: { opp: any; index: number; market: string; budget: string }) {
  const trend = TREND_COLORS[opp.trend];
  const comp = COMPETITION_COLORS[opp.competition];
  // 关键词统一使用柔和蓝灰色调，避免刺眼红色
  const keywordAccent = '#2563eb';
  const displayProduct = opp.products[0];

  const openNewAnalysis = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const params = new URLSearchParams({
      keyword: opp.keyword,
      market,
      budget,
      auto: '1',
      nopersist: '1',
    });
    const url = `${window.location.origin}/dashboard?${params.toString()}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <div key={index} className="keyword-opportunity-card">
      <div className="keyword-opportunity-rank" style={{ color: '#475569', background: '#f1f5f9' }}>
        <div className="keyword-opportunity-rank-num">{index + 1}</div>
        <div className="keyword-opportunity-rank-label">TOP</div>
      </div>

      <div className="keyword-opportunity-keyword-block">
        <button
          className="keyword-opportunity-keyword keyword-opportunity-keyword-link"
          style={{ color: keywordAccent }}
          title={`点击分析「${opp.keyword}」`}
          onClick={openNewAnalysis}
        >
          {opp.keyword}
        </button>
        <div className="keyword-opportunity-score" style={{ color: '#64748b' }}>
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
          <KeywordOpportunityRow key={i} opp={opp} index={i} market={report.market} budget={report.budget} />
        ))}
      </div>
    </div>
  );
}

function GlobalTrendsChart({ report }: { report: AnalysisReport }) {
  const trends = useMemo(() => report.market_analysis.global_trends || [], [report.market_analysis.global_trends]);
  const [selected, setSelected] = useState<string[]>(() => trends.map((t) => t.code));
  const isMobile = useMobile();

  const options = useMemo(
    () =>
      trends.map((t) => ({
        value: t.code,
        label: `${t.name}（规模指数 ${t.market_size_index}）`,
      })),
    [trends]
  );

  const chartOption: EChartsOption = useMemo(() => {
    const months = trends[0]?.months || [];
    const active = trends.filter((t) => selected.includes(t.code));
    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30, 41, 59, 0.92)',
        borderWidth: 0,
        padding: [5, 8],
        confine: true,
        textStyle: { color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: 11 },
        extraCssText: 'max-width:180px !important;width:auto !important;min-width:0 !important;word-wrap:break-word !important;white-space:normal !important;border-radius:4px !important;box-shadow:0 2px 8px rgba(0,0,0,0.15) !important;backdrop-filter:blur(4px) !important;',
        formatter: (params: any) => {
          const lines = params.map((p: any) => `<span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:${p.color};margin-right:5px;vertical-align:middle"></span><span style="font-size:10px;color:rgba(255,255,255,0.8)">${p.seriesName}: ${p.data[1] ?? p.data}%</span>`);
          return `<div style="font-weight:800;font-size:12px;color:#fff;margin-bottom:3px">${params[0].axisValue}</div><div style="line-height:1.45">${lines.join('<br/>')}</div>`;
        },
      },
      legend: {
        data: active.map((t) => t.name),
        bottom: 0,
        left: 'center',
        itemGap: isMobile ? 10 : 20,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: 'var(--saas-text-secondary)', fontWeight: 700, fontSize: isMobile ? 9 : 11 },
      },
      grid: { left: isMobile ? 6 : 16, right: isMobile ? 6 : 20, top: isMobile ? 34 : 44, bottom: isMobile ? 34 : 44, containLabel: true },
      xAxis: {
        type: 'category',
        data: months,
        boundaryGap: false,
        axisLine: { lineStyle: { color: 'var(--saas-border)' } },
        axisLabel: { color: 'var(--saas-text-muted)', fontWeight: 600, fontSize: isMobile ? 9 : 11 },
      },
      yAxis: {
        type: 'value',
        name: '搜索热度指数',
        nameTextStyle: { color: 'var(--saas-text-muted)', fontSize: isMobile ? 10 : 11 },
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: 'var(--saas-border)' } },
        axisLabel: { color: 'var(--saas-text-muted)', fontWeight: 600, fontSize: isMobile ? 9 : 11 },
      },
      series: active.map((t) => {
        const color = COUNTRY_COLORS[t.code] || '#64748b';
        return {
          type: 'line' as const,
          name: t.name,
          data: t.values,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 3, color },
          itemStyle: { color },
          areaStyle: { opacity: 0.08, color },
        };
      }),
    };
  }, [trends, selected, isMobile]);

  if (trends.length === 0) return null;

  return (
    <div className="info-card" style={{ marginBottom: 24 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          marginBottom: 16,
        }}
      >
        <div className="info-card-title" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>
          <GlobalOutlined style={{ color: 'var(--saas-primary)' }} /> 全球市场走势
        </div>
        <Select
          mode="multiple"
          allowClear
          placeholder="选择国家/地区"
          style={{ minWidth: 280, maxWidth: '100%' }}
          value={selected}
          onChange={setSelected}
          options={options}
          maxTagCount={3}
          size="middle"
        />
      </div>
      <div className="section-desc" style={{ marginBottom: 14 }}>
        对比「{report.keyword}」在主要目标市场（亚马逊站点）的月度搜索热度走势；数值为相对热度指数，可通过上方多选筛选重点国家。数据源：亚马逊站内搜索与销量综合指数。
      </div>
      <ReactECharts option={chartOption} style={{ height: isMobile ? 280 : 360, width: '100%' }} />
    </div>
  );
}

function KeywordRelationshipGraph({ report }: { report: AnalysisReport }) {
  const rel = report.market_analysis.keyword_relationships;
  const isMobile = useMobile();

  const { categories, data, links, nameMap } = useMemo(() => {
    const rawNodes = rel?.nodes || [];
    if (rawNodes.length === 0) return { categories: [], data: [], links: [], nameMap: new Map<string, string>() };

    const rootNode = rawNodes.find((n) => n.type === 'root');
    // 只保留真实关键词节点：本类目细分词 + 跨行业相关词（过滤掉中文品类名节点）
    const keywordNodes = rawNodes.filter(
      (n) =>
        n.type === 'niche' ||
        (n.type === 'root' && n.id === report.keyword)
    );

    const sameCategory = keywordNodes.filter((n) => n.type === 'niche' && !String(n.id).startsWith('niche::'));
    const crossCategory = keywordNodes.filter((n) => n.type === 'niche' && String(n.id).startsWith('niche::'));

    const categories = [
      { name: '本类目细分词' },
      { name: '跨行业拓品词' },
    ];

    const nameMap = new Map<string, string>();
    rawNodes.forEach((n) => nameMap.set(n.id, n.name));

    const maxVal = Math.max(...keywordNodes.map((n) => n.value), 1);
    const data: any[] = [];
    const links: any[] = [];

    // 径向布局：中心词在 (0,0)，关联度越高（机会分越高）离中心越近
    const innerRMin = isMobile ? 55 : 75;
    const innerRMax = isMobile ? 110 : 155;
    const outerRMin = isMobile ? 140 : 190;
    const outerRMax = isMobile ? 210 : 280;

    const placeNodes = (nodes: typeof sameCategory, rMin: number, rMax: number, catIndex: number, palette: string[]) => {
      const count = nodes.length || 1;
      nodes.forEach((n, idx) => {
        const score = Math.max(0, Math.min(100, n.opportunity_score || 50));
        // 分数越高半径越小（离中心越近）
        const r = rMax - ((score / 100) * (rMax - rMin));
        const angle = (idx / count) * 2 * Math.PI - Math.PI / 2;
        const x = Math.cos(angle) * r;
        const y = Math.sin(angle) * r;
        const displayName = n.name.replace(/^niche::/, '');
        data.push({
          ...n,
          id: n.id,
          name: displayName,
          value: n.value,
          category: catIndex,
          x,
          y,
          symbolSize: Math.max(isMobile ? 16 : 18, (n.value / maxVal) * (isMobile ? 32 : 40)),
          label: {
            show: true,
            position: x >= 0 ? 'right' : 'left',
            distance: 8,
            fontSize: isMobile ? 11 : 12,
            fontWeight: 800,
            color: '#1e293b',
            backgroundColor: 'rgba(255,255,255,0.78)',
            borderColor: 'rgba(0,0,0,0.06)',
            borderWidth: 1,
            borderRadius: 6,
            padding: [2, 6],
            shadowBlur: 4,
            shadowColor: 'rgba(0,0,0,0.08)',
            textBorderColor: 'rgba(255,255,255,0.85)',
            textBorderWidth: 2,
            formatter: (p: any) => {
              const name: string = p.name;
              return name.length > 24 ? name.slice(0, 22) + '…' : name;
            },
          },
          itemStyle: {
            color: palette[idx % palette.length],
            borderWidth: 2,
            borderColor: '#fff',
            shadowBlur: 8,
            shadowColor: 'rgba(0,0,0,0.12)',
          },
        });
        links.push({
          source: rootNode?.id,
          target: n.id,
          value: score,
          lineStyle: { width: Math.max(1, score / 25), opacity: 0.45 },
        });
      });
    };

    if (rootNode) {
      data.push({
        id: rootNode.id,
        name: rootNode.name,
        value: rootNode.value,
        x: 0,
        y: 0,
        symbolSize: isMobile ? 52 : 66,
        label: { show: true, fontSize: isMobile ? 13 : 14, fontWeight: 800, color: '#fff' },
        itemStyle: {
          color: '#dc2626',
          shadowBlur: 24,
          shadowColor: 'rgba(220,38,38,0.4)',
        },
        category: undefined,
        fixed: true,
      });
    }

    placeNodes(sameCategory, innerRMin, innerRMax, 0, SEGMENT_COLORS);
    placeNodes(crossCategory, outerRMin, outerRMax, 1, ['#7c3aed', '#d97706', '#0891b2', '#db2777', '#64748b']);

    return { categories, data, links, nameMap };
  }, [rel, report.keyword, isMobile]);

  const chartOption: EChartsOption = useMemo(() => {
    if (data.length === 0) return {};

    return {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(30, 41, 59, 0.92)',
        borderWidth: 0,
        padding: [6, 10],
        textStyle: { color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: 11 },
        extraCssText: 'max-width:180px !important;width:auto !important;min-width:0 !important;word-wrap:break-word !important;white-space:normal !important;border-radius:4px !important;box-shadow:0 2px 8px rgba(0,0,0,0.15) !important;backdrop-filter:blur(4px) !important;',
        confine: true,
        formatter: (params: any) => {
          if (params.dataType === 'edge') {
            const sName = nameMap.get(params.data.source) || params.data.source;
            const tName = nameMap.get(params.data.target) || params.data.target;
            return `<div style="font-weight:800;font-size:12px;color:#fff">${sName} → ${tName}</div><div style="color:rgba(255,255,255,0.75);font-size:10px;margin-top:2px">关联分 ${params.data.value}</div>`;
          }
          const node = params.data;
          if (node.id === report.keyword) {
            return `<div style="font-weight:800;font-size:12px;color:#fff">${node.name}</div><div style="color:rgba(255,255,255,0.75);font-size:10px;margin-top:2px">搜索量 ${node.value.toLocaleString()}</div>`;
          }
          const trendLabel = node.trend === 'rising' ? '上升' : node.trend === 'falling' ? '下滑' : '稳定';
          const compLabel = node.competition === 'low' ? '低' : node.competition === 'high' ? '高' : '中';
          const typeLabel = String(node.id).startsWith('niche::') ? '拓品词' : '细分词';
          return `<div style="font-weight:800;font-size:12px;color:#fff;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px">${node.name}</div><div style="color:rgba(255,255,255,0.75);font-size:10px;line-height:1.45">搜索 ${node.value.toLocaleString()} · 机会 ${node.opportunity_score || '-'}<br/>趋势 ${trendLabel} · 竞争 ${compLabel} · ${typeLabel}</div>`;
        },
      },
      legend: {
        data: categories.map((c) => c.name),
        top: 0,
        left: 0,
        orient: 'horizontal',
        itemGap: 16,
        textStyle: { color: 'var(--saas-text-secondary)', fontWeight: 700, fontSize: 12 },
      },
      series: [
        {
          type: 'graph' as const,
          layout: 'none',
          data,
          links,
          categories,
          roam: true,
          draggable: true,
          label: { show: true, position: 'right', distance: 6 },
          labelLayout: { hideOverlap: false },
          lineStyle: { color: 'source', curveness: 0.1, opacity: 0.45 },
          emphasis: {
            focus: 'adjacency',
            label: { show: true, fontSize: isMobile ? 12 : 13 },
            lineStyle: { width: 3, opacity: 0.85 },
          },
        },
      ],
    };
  }, [data, links, categories, report.keyword, isMobile, nameMap]);

  if (!rel || rel.nodes.length === 0) return null;

  return (
    <div className="info-card" style={{ marginBottom: 24 }}>
      <div className="info-card-title">
        <ApartmentOutlined style={{ color: 'var(--saas-primary)' }} /> 关键词关系网络与拓品建议
      </div>
      <div className="section-desc">
        以「{report.keyword}」为核心，直接展示真实细分关键词与跨行业拓品关键词；<strong>圆球越大代表搜索热度越高，离中心越近代表关联度越强</strong>。右侧为基于聚类的拓品方向建议。
      </div>
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <ReactECharts option={chartOption} style={{ height: isMobile ? 320 : 420, width: '100%' }} />
        </Col>
        <Col xs={24} lg={8}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {(rel?.expansion_suggestions || []).map((s, i) => (
              <div
                key={i}
                style={{
                  padding: 14,
                  background: '#f8fafc',
                  border: '1px solid var(--saas-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 800,
                    color: 'var(--saas-text)',
                    marginBottom: 6,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <BulbOutlined style={{ color: SEGMENT_COLORS[i % SEGMENT_COLORS.length] }} />
                  {s.segment}
                  <span style={{ marginLeft: 'auto', fontSize: 12, color: s.avg_score >= 60 ? '#dc2626' : '#d97706' }}>
                    平均机会分 {s.avg_score}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--saas-text-secondary)', lineHeight: 1.6, marginBottom: 8 }}>
                  {s.rationale}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {s.keywords.map((kw, j) => (
                    <Tag key={j} style={{ fontSize: 11, fontWeight: 700, background: '#eff6ff', color: '#1d4ed8', border: '1px solid #dbeafe' }}>
                      {kw}
                    </Tag>
                  ))}
                </div>
              </div>
            ))}
          </Space>
        </Col>
      </Row>
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
          <div className="page-subtitle">全球市场走势、关键词关系网络、细分机会与竞品格局综合分析，支撑选品决策</div>
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
                <span className="market-summary-tag">均价 {getMarketCurrency(report.market).symbol}{report.market_analysis.avg_price}</span>
                <span className="market-summary-tag">平均评分 {report.market_analysis.avg_rating} / 5.0</span>
              </div>
            </div>
          </div>

          <KeywordSummary report={report} />

          <GlobalTrendsChart report={report} />

          <KeywordRelationshipGraph report={report} />

          <KeywordOpportunities report={report} />

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
                  <CompetitorCard key={i} product={p} index={i} market={report.market} />
                ))}
              </div>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
}
