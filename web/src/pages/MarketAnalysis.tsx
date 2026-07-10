import { Card, Col, Row, Spin, Tag } from 'antd';
import { BarChartOutlined, StarFilled, ShoppingOutlined, LinkOutlined } from '@ant-design/icons';
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
  const competitors = report.market_analysis.competitors;

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
                  按销量与 relevance 排序的头部 Listing，点击可跳转亚马逊详情页。
                </div>
                {report.market_analysis.competitors.map((p: any, i: number) => (
                  <CompetitorCard key={i} product={p} index={i} />
                ))}
              </div>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
}
