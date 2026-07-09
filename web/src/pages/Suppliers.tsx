import { Button, Card, Select, Spin } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
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

function SupplierCard({ supplier, index }: { supplier: any; index: number }) {
  const rank = index + 1;
  const rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
  const ratingPct = Math.min(100, (supplier.rating / 5) * 100);
  const responsePct = supplier.response_rate;
  const ratingColor = 'linear-gradient(90deg, #ea580c, #fbbf24)';
  const responseColor = 'linear-gradient(90deg, #0f766e, #2dd4bf)';

  return (
    <div className="product-card" style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <div className={`supplier-rank ${rankClass}`}>{rank}</div>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div className="product-title" style={{ fontSize: 16, marginBottom: 5 }}>{supplier.name}</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
            <span className="badge" style={{ background: '#eff6ff', color: '#1d4ed8' }}>{supplier.moq}</span>
            <span className="badge" style={{ background: '#dbeafe', color: '#1e40af' }}>交期 {supplier.lead_time}</span>
            <span className="badge" style={{ background: '#f1f5f9', color: '#334155' }}>{supplier.capacity}</span>
            <span className="badge" style={{ background: '#ecfdf5', color: '#047857' }}>打样 {supplier.sample_days} 天</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 120 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#475569', whiteSpace: 'nowrap' }}>评分</span>
              <div className="big-bar-bg"><div className="big-bar-fill" style={{ width: `${ratingPct}%`, background: ratingColor }} /></div>
              <span style={{ fontSize: 12, fontWeight: 800, color: '#0f172a', whiteSpace: 'nowrap' }}>{supplier.rating}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 120 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#475569', whiteSpace: 'nowrap' }}>响应</span>
              <div className="big-bar-bg"><div className="big-bar-fill" style={{ width: `${responsePct}%`, background: responseColor }} /></div>
              <span style={{ fontSize: 12, fontWeight: 800, color: '#0f172a', whiteSpace: 'nowrap' }}>{supplier.response_rate}%</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#475569', whiteSpace: 'nowrap' }}>主营热卖：</span>
            {supplier.hot_categories?.map((c: string, i: number) => (
              <span key={i} className="badge" style={{ background: '#fff7ed', color: '#9a3412', border: '1px solid #fed7aa' }}>🔥 {c}</span>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <div className="supplier-metric">
              <div className="supplier-metric-value" style={{ color: '#2563eb' }}>${supplier.unit_cost}</div>
              <div className="supplier-metric-label">单价</div>
            </div>
            <div className="supplier-metric">
              <div className="supplier-metric-value">${supplier.sample_cost}</div>
              <div className="supplier-metric-label">样品</div>
            </div>
            <div className="supplier-metric">
              <div className="supplier-metric-value">{supplier.years}年</div>
              <div className="supplier-metric-label">经营</div>
            </div>
            <div className="supplier-metric">
              <div className="supplier-metric-value">{supplier.transactions}</div>
              <div className="supplier-metric-label">成交</div>
            </div>
          </div>
          <a href={supplier.link_1688 || '#'} target="_blank" rel="noreferrer" style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 12, padding: '8px 12px', minWidth: 150 }}>
            <img src={supplier.hot_product_image} alt="" style={{ width: 44, height: 44, borderRadius: 8, objectFit: 'cover', background: '#fff' }} />
            <div style={{ textAlign: 'left', minWidth: 0 }}>
              <div style={{ color: '#9a3412', fontWeight: 800, fontSize: 11, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 110 }}>{supplier.hot_product_name || '热卖品'}</div>
              <div style={{ color: '#d97706', fontWeight: 800, fontSize: 12 }}>1688 搜索 →</div>
            </div>
          </a>
        </div>
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

  return (
    <div className="page-container">
      <div className="page-header">供应商</div>
      <Card style={{ borderRadius: 16, marginBottom: 24 }}>
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>正在匹配供应商...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="供应商" />}

      {!loading && report && (
        <>
          <div className="info-card" style={{ marginBottom: 16, padding: '18px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <div className="info-card-title" style={{ marginBottom: 4 }}>🏭 供应商竞争力 TOP10</div>
                <div style={{ color: '#64748b', fontSize: 13, fontWeight: 500 }}>综合评分 · 产能 · 响应 · 报价多维度对比</div>
              </div>
              <span className="badge" style={{ background: '#eff6ff', color: '#1d4ed8' }}>已匹配 {report.suppliers.length} 家</span>
            </div>
          </div>

          <div style={{ marginBottom: 16, maxWidth: 280 }}>
            <Select value={sortBy} options={sortOptions} onChange={setSortBy} style={{ width: '100%' }} />
          </div>

          {sortedSuppliers.map((s, i) => (
            <SupplierCard key={i} supplier={s} index={i} />
          ))}

          <div style={{ marginTop: 24, textAlign: 'right' }}>
            <Button type="primary" icon={<DownloadOutlined />} onClick={() => exportSuppliersCsv(report, sortedSuppliers)}>
              导出供应商对比表 (CSV)
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
