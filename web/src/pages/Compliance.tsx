import {
  AuditOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  FileProtectOutlined,
  FlagOutlined,
  GlobalOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Spin } from 'antd';
import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';

const riskColors: Record<string, { bg: string; text: string; border: string }> = {
  低: { bg: 'var(--primary-50)', text: 'var(--saas-primary)', border: 'var(--primary-200)' },
  中: { bg: 'var(--warning-50)', text: 'var(--saas-warning)', border: 'color-mix(in srgb, var(--saas-warning) 25%, transparent)' },
  高: { bg: 'var(--danger-50)', text: 'var(--saas-danger)', border: 'color-mix(in srgb, var(--saas-danger) 25%, transparent)' },
};

const sectionIcons: Record<string, React.ReactNode> = {
  '品类专属合规风险': <ExclamationCircleOutlined />,
  '强制认证': <SafetyCertificateOutlined />,
  '外观设计专利风险': <FileProtectOutlined />,
  '商标/品牌侵权风险': <FlagOutlined />,
  '行业/功能专利风险': <AuditOutlined />,
  '目标市场特殊合规': <GlobalOutlined />,
};

function ComplianceCard({ title, items, accent, statusOk, statusNote }: { title: string; items: string[]; accent: string; statusOk: string; statusNote: string }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="compliance-card" style={{ borderTop: `4px solid ${accent}`, height: '100%', minHeight: 170, display: 'flex', flexDirection: 'column' }}>
      <div className="compliance-card-header">
        <div className="compliance-card-title">
          <span style={{ color: accent, fontSize: 18 }}>{sectionIcons[title] || <CheckCircleOutlined />}</span>
          {title}
        </div>
        <span className="compliance-status" style={{ background: `color-mix(in srgb, ${accent} 12%, transparent)`, color: accent, border: `1px solid color-mix(in srgb, ${accent} 25%, transparent)` }}>{statusOk}</span>
      </div>
      <ul className="compliance-list" style={{ flex: 1 }}>
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
      <div className="compliance-note">
        <BulbOutlined style={{ color: accent, marginRight: 6 }} />
        {statusNote}
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
  const rc = comp ? (riskColors[comp.risk_level] || { bg: 'var(--gray-100)', text: 'var(--saas-text-secondary)', border: 'var(--saas-border)' }) : null;

  const sections = comp ? [
    { title: '品类专属合规风险', items: comp.category_risks || [], accent: 'var(--saas-danger)', statusOk: '重点关注', statusNote: '与关键词行业精准匹配' },
    { title: '强制认证', items: comp.certifications || [], accent: 'var(--saas-primary)', statusOk: '通过', statusNote: '建议尽早上架前准备' },
    { title: '外观设计专利风险', items: comp.design_patent_risks || [], accent: 'var(--saas-warning)', statusOk: '需检索', statusNote: '避免 TRO 与下架' },
    { title: '商标/品牌侵权风险', items: comp.brand_risks || [], accent: 'var(--saas-purple)', statusOk: '需筛查', statusNote: 'Listing 文案/图片自查' },
    { title: '行业/功能专利风险', items: comp.industry_patent_risks || [], accent: 'var(--saas-info)', statusOk: '需 FTO', statusNote: '工厂授权链确认' },
    { title: '目标市场特殊合规', items: comp.market_specific || [], accent: 'var(--saas-info)', statusOk: '需适配', statusNote: `${comp.market} 当地法规` },
  ] : [];

  return (
    <div className="page-container">
      <div className="page-hero">
        <div>
          <div className="page-header">合规检查</div>
          <div className="page-subtitle">识别品类合规、认证、专利与侵权风险，提前规避下架与 TRO</div>
        </div>
        {report && (
          <span className="section-badge">
            <AuditOutlined /> 当前分析：{report.keyword}
          </span>
        )}
      </div>
      <Card className="search-card">
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>正在检查合规风险...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="合规检查" />}

      {!loading && report && comp && rc && (
        <>
          <div className="compliance-summary-banner" style={{ ['--summary-accent' as string]: rc.text } as React.CSSProperties}>
            <div className="compliance-summary-main">
              <div className="compliance-summary-label">合规与知识产权风险检查</div>
              <div className="compliance-summary-title">
                <WarningOutlined style={{ color: rc.text }} /> 风险等级：{comp.risk_level}
              </div>
              <div className="compliance-summary-meta">
                针对「{report.keyword}」在 {comp.market} 市场的合规风险扫描结果，建议按以下维度逐项排查。
              </div>
            </div>
            <div className="compliance-summary-stats">
              <div className="compliance-summary-stat">
                <div className="compliance-summary-stat-label">预估认证费用</div>
                <div className="compliance-summary-stat-value">${comp.estimated_cert_cost}</div>
              </div>
              <div className="compliance-summary-stat">
                <div className="compliance-summary-stat-label">预估认证周期</div>
                <div className="compliance-summary-stat-value">{comp.estimated_cert_time}</div>
              </div>
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
