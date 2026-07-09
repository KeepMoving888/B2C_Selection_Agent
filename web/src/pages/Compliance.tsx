import { Card, Col, Row, Spin } from 'antd';
import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';

const riskColors: Record<string, { bg: string; text: string; border: string }> = {
  低: { bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe' },
  中: { bg: '#fff7ed', text: '#9a3412', border: '#fed7aa' },
  高: { bg: '#fee2e2', text: '#991b1b', border: '#fecaca' },
};

function ComplianceCard({ title, items, accent, statusOk, statusNote }: { title: string; items: string[]; accent: string; statusOk: string; statusNote: string }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="compliance-card" style={{ borderLeft: `4px solid ${accent}`, height: '100%', minHeight: 170, display: 'flex', flexDirection: 'column' }}>
      <div className="compliance-card-header">
        <div className="compliance-card-title">{title}</div>
        <span className="compliance-status" style={{ background: `${accent}33`, color: accent }}>{statusOk}</span>
      </div>
      <ul className="compliance-list" style={{ flex: 1 }}>
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
      <div style={{ marginTop: 'auto', padding: '8px 10px', background: '#f8fafc', borderRadius: 8, fontSize: 12, color: '#64748b', fontWeight: 600 }}>
        💡 {statusNote}
      </div>
    </div>
  );
}

export default function Compliance() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();

  useEffect(() => {
    dispatch(setPageTitle('合规检查'));
  }, [dispatch]);

  const comp = report?.compliance;
  const rc = comp ? (riskColors[comp.risk_level] || { bg: '#f1f5f9', text: '#475569', border: '#e2e8f0' }) : null;

  const sections = comp ? [
    { title: '🎯 品类专属合规风险', items: comp.category_risks || [], accent: '#dc2626', statusOk: '重点关注', statusNote: '与关键词行业精准匹配' },
    { title: '📋 强制认证', items: comp.certifications || [], accent: '#2563eb', statusOk: '通过', statusNote: '建议尽早上架前准备' },
    { title: '🎨 外观设计专利风险', items: comp.design_patent_risks || [], accent: '#d97706', statusOk: '需检索', statusNote: '避免 TRO 与下架' },
    { title: '™️ 商标/品牌侵权风险', items: comp.brand_risks || [], accent: '#7c3aed', statusOk: '需筛查', statusNote: 'Listing 文案/图片自查' },
    { title: '⚙️ 行业/功能专利风险', items: comp.industry_patent_risks || [], accent: '#0f766e', statusOk: '需 FTO', statusNote: '工厂授权链确认' },
    { title: '🌍 目标市场特殊合规', items: comp.market_specific || [], accent: '#0369a1', statusOk: '需适配', statusNote: `${comp.market} 当地法规` },
  ] : [];

  return (
    <div className="page-container">
      <div className="page-header">合规检查</div>
      <Card style={{ borderRadius: 16, marginBottom: 24 }}>
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>正在检查合规风险...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="合规检查" />}

      {!loading && report && comp && rc && (
        <>
          <div className="info-card" style={{ marginBottom: 16 }}>
            <div className="info-card-title">🛡️ 合规与知识产权风险检查</div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <span className="badge" style={{ background: rc.bg, color: rc.text, border: `1px solid ${rc.border}` }}>风险等级：{comp.risk_level}</span>
              <span className="badge" style={{ background: '#f1f5f9', color: '#475569' }}>预估认证费用 ${comp.estimated_cert_cost}</span>
              <span className="badge" style={{ background: '#f1f5f9', color: '#475569' }}>预估周期 {comp.estimated_cert_time}</span>
            </div>
          </div>

          <Row gutter={[24, 24]}>
            {sections.filter((s) => s.items.length > 0).map((s, i) => (
              <Col xs={24} md={12} key={i}>
                <ComplianceCard {...s} />
              </Col>
            ))}
          </Row>
        </>
      )}
    </div>
  );
}
