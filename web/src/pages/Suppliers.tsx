import {
  ClockCircleOutlined,
  DownloadOutlined,
  FireOutlined,
  ShopOutlined,
  StarFilled,
  SwapOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Button, Card, Select, Spin } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

const sortOptions = [
  { value: 'default', label: '综合评分（默认）' },
  { value: 'price_asc', label: '单价从低到高' },
  { value: 'price_desc', label: '单价从高到低' },
  { value: 'response_desc', label: '响应率从高到低' },
];

function MiniBar({ value, color, label }: { value: number; color: string; label: React.ReactNode }) {
  return (
    <div className="supplier-mini-bar">
      <span className="supplier-mini-bar-label">{label}</span>
      <div className="supplier-mini-bar-track">
        <div
          className="supplier-mini-bar-fill"
          style={{
            width: `${Math.min(100, Math.max(0, value))}%`,
            background: color,
          }}
        />
      </div>
      <span className="supplier-mini-bar-value">{value.toFixed(0)}%</span>
    </div>
  );
}

function SupplierCard({ supplier, index }: { supplier: any; index: number }) {
  const rank = index + 1;
  const rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
  const ratingPct = Math.min(100, (supplier.rating / 5) * 100);

  return (
    <div className="supplier-card">
      <div className="supplier-card-top">
        <div className="supplier-identity">
          <div className={`supplier-rank ${rankClass}`}>{rank}</div>
          <div className="supplier-title-block">
            <div className="supplier-name">{supplier.name}</div>
            <div className="supplier-tags">
              <span className="badge" style={{ background: 'var(--primary-50)', color: 'var(--saas-primary)' }}>
                {supplier.moq}
              </span>
              <span className="badge" style={{ background: 'var(--gray-100)', color: 'var(--gray-600)' }}>
                <ClockCircleOutlined style={{ fontSize: 10 }} /> 交期 {supplier.lead_time}
              </span>
              <span className="badge" style={{ background: 'var(--success-50)', color: 'var(--saas-success)' }}>
                打样 {supplier.sample_days} 天
              </span>
              <span className="badge" style={{ background: 'var(--purple-50)', color: 'var(--saas-purple)' }}>
                {supplier.capacity}
              </span>
            </div>
          </div>
        </div>

        <a href={supplier.link_1688 || '#'} target="_blank" rel="noreferrer" className="supplier-product-link">
          <img src={supplier.hot_product_image} alt="" className="supplier-product-img" />
          <div className="supplier-product-info">
            <div className="supplier-product-title">{supplier.hot_product_name || '热卖品'}</div>
            <div className="supplier-product-action">1688 搜索 →</div>
          </div>
        </a>
      </div>

      <div className="supplier-card-middle">
        <div className="supplier-metric-compact">
          <span className="supplier-metric-compact-label">单价</span>
          <span className="supplier-metric-compact-value" style={{ color: 'var(--saas-primary)' }}>
            ${supplier.unit_cost}
          </span>
        </div>
        <div className="supplier-metric-compact">
          <span className="supplier-metric-compact-label">样品</span>
          <span className="supplier-metric-compact-value">${supplier.sample_cost}</span>
        </div>
        <div className="supplier-metric-compact">
          <span className="supplier-metric-compact-label">经营年限</span>
          <span className="supplier-metric-compact-value">{supplier.years} 年</span>
        </div>
        <div className="supplier-metric-compact">
          <span className="supplier-metric-compact-label">成交数</span>
          <span className="supplier-metric-compact-value">{supplier.transactions}</span>
        </div>
      </div>

      <div className="supplier-card-bottom">
        <div className="supplier-bars-group">
          <MiniBar value={ratingPct} color="#f59e0b" label={<><StarFilled style={{ fontSize: 10, marginRight: 4 }} />评分 {supplier.rating}</>} />
          <MiniBar value={supplier.response_rate} color="#0891b2" label={<><TeamOutlined style={{ fontSize: 10, marginRight: 4 }} />响应率</>} />
        </div>
        {supplier.hot_categories?.length > 0 && (
          <div className="supplier-categories-row">
            {supplier.hot_categories.map((c: string, i: number) => (
              <span key={i} className="badge" style={{ background: 'var(--warning-50)', color: 'var(--saas-warning)', border: '1px solid #fde68a' }}>
                <FireOutlined style={{ fontSize: 10 }} /> {c}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function exportSuppliersCsv(report: AnalysisReport, suppliers: any[]) {
  const headers = ['display_rank', 'name', 'moq', 'lead_time', 'rating', 'response_rate', 'unit_cost', 'sample_cost', 'capacity', 'sample_days', 'years', 'transactions', 'hot_categories', 'hot_product_name', 'link_1688'];
  const rows = suppliers.map((s, i) => [i + 1, s.name, s.moq, s.lead_time, s.rating, s.response_rate, s.unit_cost, s.sample_cost, s.capacity, s.sample_days, s.years, s.transactions, (s.hot_categories || []).join(';'), s.hot_product_name, s.link_1688]);
  const csvContent = [headers.join(','), ...rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n');
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${report.keyword.replace(/\s+/g, '_').toLowerCase()}_${report.market.toLowerCase()}_suppliers.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default function Suppliers() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();
  const [sortBy, setSortBy] = useState('default');

  useEffect(() => {
    dispatch(setPageTitle('供应商'));
  }, [dispatch]);

  const sortedSuppliers = useMemo(() => {
    if (!report) return [];
    const list = [...report.suppliers];
    if (sortBy === 'price_asc') list.sort((a, b) => a.unit_cost - b.unit_cost);
    else if (sortBy === 'price_desc') list.sort((a, b) => b.unit_cost - a.unit_cost);
    else if (sortBy === 'response_desc') list.sort((a, b) => b.response_rate - a.response_rate);
    return list;
  }, [report, sortBy]);

  const displaySuppliers = useMemo(() => sortedSuppliers.slice(0, 10), [sortedSuppliers]);

  return (
    <div className="page-container">
      <div className="page-hero">
        <div>
          <div className="page-header">供应商</div>
          <div className="page-subtitle">综合评分、产能、响应、报价多维度对比，锁定优质供应商</div>
        </div>
        {report && (
          <span className="section-badge">
            <ShopOutlined /> 当前分析：{report.keyword}
          </span>
        )}
      </div>
      <Card className="search-card">
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>正在匹配供应商...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="供应商" />}

      {!loading && report && (
        <>
          <div className="info-card" style={{ marginBottom: 20, padding: '18px 22px' }}>
            <div className="supplier-header-row">
              <div>
                <div className="info-card-title" style={{ marginBottom: 4, paddingBottom: 0, borderBottom: 'none' }}>
                  <ShopOutlined style={{ color: 'var(--saas-primary)' }} /> 供应商竞争力 TOP10
                </div>
                <div style={{ color: 'var(--saas-text-muted)', fontSize: 13, fontWeight: 500 }}>
                  已匹配 <strong style={{ color: 'var(--saas-text)' }}>{report.suppliers.length}</strong> 家供应商 · 当前展示 TOP10 · 导出可获取全部数据
                </div>
              </div>
              <div className="supplier-sort">
                <SwapOutlined style={{ color: 'var(--saas-text-muted)' }} />
                <Select value={sortBy} options={sortOptions} onChange={setSortBy} style={{ width: 180 }} />
              </div>
            </div>
          </div>

          <div className="supplier-list">
            {displaySuppliers.map((s, i) => (
              <SupplierCard key={i} supplier={s} index={i} />
            ))}
          </div>

          <div style={{ marginTop: 24, textAlign: 'right' }}>
            <Button type="primary" icon={<DownloadOutlined />} onClick={() => exportSuppliersCsv(report, sortedSuppliers)} size="large">
              导出供应商对比表 (CSV)
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
