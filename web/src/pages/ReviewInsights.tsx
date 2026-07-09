import { Card, Col, Row, Spin } from 'antd';
import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';

function ReviewCard({ text, i, kind }: { text: string; i: number; kind: 'pain' | 'praise' }) {
  const isPain = kind === 'pain';
  const bg = '#fff';
  const border = isPain ? '#fee2e2' : '#dcfce7';
  const numBg = isPain ? '#fee2e2' : '#dcfce7';
  const numColor = isPain ? '#991b1b' : '#166534';
  const badgeBg = isPain ? '#fee2e2' : '#dcfce7';
  const badgeColor = isPain ? '#991b1b' : '#166534';
  const badgeText = isPain ? '高提及' : '卖点';

  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: 8,
      padding: '7px 10px',
      marginBottom: 6,
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 10,
      borderLeft: `3px solid ${numColor}`,
    }}>
      <span style={{
        flexShrink: 0,
        width: 18,
        height: 18,
        background: numBg,
        color: numColor,
        borderRadius: '50%',
        fontSize: 11,
        fontWeight: 800,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginTop: 1,
      }}>{i}</span>
      <span style={{ fontSize: 13, color: '#334155', fontWeight: 500, lineHeight: 1.45, flex: 1 }}>{text}</span>
      <span className="badge" style={{ background: badgeBg, color: badgeColor, flexShrink: 0, marginTop: 1 }}>{badgeText}</span>
    </div>
  );
}

function OpportunityCard({ opp, refProduct }: { opp: string; refProduct: any }) {
  if (!refProduct) {
    return (
      <div className="product-card" style={{ borderLeft: '4px solid #2563eb', padding: '12px 14px', marginBottom: 10 }}>
        <div style={{ color: '#0f172a', fontWeight: 700, fontSize: 14, marginBottom: 4 }}>🎯 {opp}</div>
      </div>
    );
  }

  return (
    <div className="product-card" style={{ display: 'flex', alignItems: 'center', gap: 12, borderLeft: '4px solid #2563eb', padding: '12px 14px', marginBottom: 10 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: '#0f172a', fontWeight: 700, fontSize: 14, marginBottom: 4 }}>🎯 {opp}</div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <span className="badge" style={{ background: '#eff6ff', color: '#1d4ed8' }}>差异化</span>
          <span className="badge" style={{ background: '#f1f5f9', color: '#475569' }}>参考竞品</span>
        </div>
      </div>
      <a href={refProduct.link} target="_blank" rel="noreferrer" style={{
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        textDecoration: 'none',
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: 10,
        padding: '6px 10px',
      }}>
        <img src={refProduct.image} alt="" style={{ width: 40, height: 40, borderRadius: 8, objectFit: 'cover', background: '#fff' }} />
        <div style={{ textAlign: 'left', minWidth: 0 }}>
          <div style={{ color: '#0f172a', fontWeight: 700, fontSize: 11, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 120 }}>{refProduct.title}</div>
          <div style={{ color: '#2563eb', fontWeight: 800, fontSize: 11 }}>${refProduct.price} · 查看 →</div>
        </div>
      </a>
    </div>
  );
}

export default function ReviewInsights() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();

  useEffect(() => {
    dispatch(setPageTitle('评论洞察'));
  }, [dispatch]);

  return (
    <div className="page-container">
      <div className="page-header">评论洞察</div>
      <Card style={{ borderRadius: 16, marginBottom: 24 }}>
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>正在分析评论数据...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="评论洞察" />}

      {!loading && report && (
        <>
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <div className="info-card">
                <div className="info-card-title">🔴 用户痛点</div>
                {report.review_insights.pain_points.slice(0, 5).map((p: string, i: number) => (
                  <ReviewCard key={i} text={p} i={i + 1} kind="pain" />
                ))}
              </div>
            </Col>
            <Col xs={24} lg={12}>
              <div className="info-card">
                <div className="info-card-title">🟢 用户好评</div>
                {report.review_insights.praised_features.slice(0, 5).map((p: string, i: number) => (
                  <ReviewCard key={i} text={p} i={i + 1} kind="praise" />
                ))}
              </div>
            </Col>
          </Row>

          <div className="info-card" style={{ marginTop: 24 }}>
            <div className="info-card-title">💡 差异化机会</div>
            <div style={{
              padding: '12px 14px',
              background: '#f8fafc',
              borderRadius: 12,
              marginBottom: 12,
              fontSize: 13,
              color: '#475569',
              lineHeight: 1.6,
            }}>
              基于「<strong style={{ color: '#2563eb' }}>{report.keyword}</strong>」用户评论洞察，围绕下方痛点做定向升级，可形成核心差异化卖点。
            </div>
            {report.review_insights.opportunities.map((opp: string, idx: number) => {
              const competitors = report.market_analysis.competitors;
              const ref = competitors[idx % Math.min(3, competitors.length)] || null;
              return <OpportunityCard key={idx} opp={opp} refProduct={ref} />;
            })}
          </div>
        </>
      )}
    </div>
  );
}
