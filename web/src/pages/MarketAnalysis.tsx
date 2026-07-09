import { Card, Col, Row, Spin, Typography } from 'antd';
import type { EChartsOption } from 'echarts';
import ReactECharts from 'echarts-for-react';
import { useEffect, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

const { Text } = Typography;

const softPalette = ['#bfdbfe', '#93c5fd', '#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8'];

function PriceSalesChart({ report }: { report: AnalysisReport }) {
  const competitors = report.market_analysis.competitors;

  const option: EChartsOption = useMemo(() => {
    const maxPrice = Math.max(...competitors.map((p) => p.price));
    const maxSales = Math.max(...competitors.map((p) => p.estimated_monthly_sales));

    return {
      tooltip: { trigger: 'axis' },
      legend: { orient: 'horizontal', top: 0, right: 0 },
      grid: { left: 20, right: 60, top: 50, bottom: 20, containLabel: true },
      xAxis: { type: 'category', data: competitors.map((p) => p.brand), axisLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' } },
      yAxis: [
        { type: 'value', name: '售价 (USD)', max: maxPrice * 1.28, axisLine: { show: false }, splitLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' } },
        { type: 'value', name: '月销量', max: maxSales * 1.28, axisLine: { show: false }, splitLine: { show: false }, axisLabel: { color: '#64748b' } },
      ],
      series: [
        {
          type: 'bar',
          name: '售价',
          data: competitors.map((p, i) => ({ value: p.price, itemStyle: { color: softPalette[i % softPalette.length] } })),
          barWidth: '45%',
          label: { show: true, position: 'top', formatter: '${c}', color: '#0f172a', fontSize: 10 },
        },
        {
          type: 'line',
          name: '月销量',
          yAxisIndex: 1,
          data: competitors.map((p) => p.estimated_monthly_sales),
          lineStyle: { color: '#f59e0b', width: 2.5 },
          itemStyle: { color: '#f59e0b' },
          label: { show: true, position: 'top', formatter: '{c}', color: '#b45309', fontSize: 10 },
        },
      ],
    };
  }, [competitors]);

  return <ReactECharts option={option} style={{ height: 360 }} />;
}

function CompetitorCard({ product, index }: { product: any; index: number }) {
  const parts = product.subtitle?.split(' · ') || [];
  const subtitle = parts[1] || product.subtitle || '';

  return (
    <div className="product-card" style={{ borderLeft: `4px solid ${softPalette[index % softPalette.length]}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <a href={product.link} target="_blank" rel="noreferrer" style={{ flexShrink: 0 }}>
          <img src={product.image} alt="" style={{ width: 64, height: 64, borderRadius: 12, objectFit: 'cover', background: '#f1f5f9', border: '1px solid #e2e8f0' }} />
        </a>
        <div style={{ flex: 1, minWidth: 0 }}>
          <a href={product.link} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="product-title" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{product.title}</div>
          </a>
          <div className="product-meta" style={{ fontSize: 12, marginBottom: 5 }}>{product.store} · {subtitle}</div>
          <div className="product-meta">
            <strong style={{ color: '#2563eb' }}>${product.price}</strong> ·
            ⭐ {product.rating} · {product.review_count.toLocaleString()} 评论 · 月销 {product.estimated_monthly_sales.toLocaleString()}
          </div>
        </div>
        <a href={product.link} target="_blank" rel="noreferrer" style={{
          textDecoration: 'none',
          background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
          color: '#fff',
          padding: '8px 14px',
          borderRadius: 10,
          fontSize: 12,
          fontWeight: 700,
          flexShrink: 0,
          whiteSpace: 'nowrap',
          boxShadow: '0 2px 8px rgba(37,99,235,0.25)',
        }}>
          查看链接 →
        </a>
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
      <div className="page-header">市场分析</div>
      <Card style={{ borderRadius: 16, marginBottom: 24 }}>
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>正在分析市场数据...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="市场分析" />}

      {!loading && report && (
        <>
          <div className="verdict-banner" style={{ marginBottom: 24 }}>
            <Text strong style={{ fontSize: 18 }}>{report.keyword.toUpperCase()}</Text>
            <span className="badge" style={{ marginLeft: 12, background: '#eff6ff', color: '#1d4ed8' }}>{report.market_analysis.market_profile.name}</span>
          </div>

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={15}>
              <div className="info-card">
                <div className="info-card-title">竞品价格带与月销量分布</div>
                <PriceSalesChart report={report} />
              </div>
            </Col>
            <Col xs={24} lg={9}>
              <div className="info-card" style={{ maxHeight: 620, overflow: 'auto' }}>
                <div className="info-card-title">头部竞品 TOP10</div>
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
