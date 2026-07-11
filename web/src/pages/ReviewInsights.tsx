import {
  BulbOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CommentOutlined,
  ExclamationCircleOutlined,
  RiseOutlined,
  TagOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Spin, Typography } from 'antd';
import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

const { Text } = Typography;

const REVIEW_THEMES = {
  pain: {
    accent: '#dc2626',
    accentLight: '#ef4444',
    bg: '#fef2f2',
    border: '#fee2e2',
    badgeBg: '#fecaca',
    badgeText: '高提及痛点',
    icon: <CloseCircleOutlined />,
    title: '用户痛点',
  },
  praise: {
    accent: '#059669',
    accentLight: '#10b981',
    bg: '#ecfdf5',
    border: '#d1fae5',
    badgeBg: '#a7f3d0',
    badgeText: '核心好评',
    icon: <CheckCircleOutlined />,
    title: '用户好评',
  },
};

function ReviewCard({ text, i, kind }: { text: string; i: number; kind: 'pain' | 'praise' }) {
  const theme = REVIEW_THEMES[kind];

  return (
    <div className="review-card-accent" style={{ borderLeft: `4px solid ${theme.accent}`, borderColor: theme.border, background: '#ffffff' }}>
      <div className="review-number" style={{ background: theme.bg, color: theme.accent, border: `1px solid ${theme.border}` }}>
        {i}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, color: 'var(--saas-text)', fontWeight: 500, lineHeight: 1.7, marginBottom: 8 }}>
          {text}
        </div>
        <span className="review-badge" style={{ background: theme.bg, color: theme.accent, borderColor: theme.badgeBg }}>
          {theme.badgeText}
        </span>
      </div>
    </div>
  );
}

function StatBadge({ label, value, color, bg, border, icon }: { label: string; value: string; color: string; bg: string; border: string; icon: React.ReactNode }) {
  return (
    <div className="review-stat-badge" style={{ background: bg, borderColor: border }}>
      <span className="review-stat-icon" style={{ color }}>{icon}</span>
      <div>
        <div className="review-stat-label" style={{ color: 'var(--saas-text-muted)' }}>{label}</div>
        <div className="review-stat-value" style={{ color }}>{value}</div>
      </div>
    </div>
  );
}

function extractOpportunityTag(opp: string): string {
  // 按优先级匹配更具体的机会动作，避免全部落入“卖点强化”
  const priorityTags: { patterns: string[]; tag: string }[] = [
    { patterns: ['Listing', '广告', '核心卖点'], tag: 'Listing 优化' },
    { patterns: ['密封', '防漏', '漏水'], tag: '防漏强化' },
    { patterns: ['异味', '材质', '食品级', '掉色', '发黄', '掉毛', '扎'], tag: '材质升级' },
    { patterns: ['尺寸', '大小'], tag: '尺寸优化' },
    { patterns: ['容量'], tag: '容量优化' },
    { patterns: ['清洗', '可拆卸', '宽口'], tag: '结构优化' },
    { patterns: ['耐用', '耐咬', '抗磨损', '断裂'], tag: '耐用性提升' },
    { patterns: ['连接', '稳定', '信号', '兼容'], tag: '连接优化' },
    { patterns: ['续航', '电池', '充电'], tag: '续航提升' },
    { patterns: ['安装', '设置'], tag: '体验优化' },
    { patterns: ['便携', '轻量化'], tag: '便携设计' },
    { patterns: ['散热', '发热', '温控'], tag: '散热优化' },
    { patterns: ['物流', '履约', '时效'], tag: '物流优化' },
    { patterns: ['售后', '响应'], tag: '售后提升' },
    { patterns: ['价格', '成本'], tag: '价格优化' },
    { patterns: ['安全', '合规'], tag: '安全合规' },
    { patterns: ['功能', '升级'], tag: '功能创新' },
    { patterns: ['包装'], tag: '包装升级' },
    { patterns: ['质量'], tag: '质量升级' },
  ];
  for (const { patterns, tag } of priorityTags) {
    if (patterns.some((p) => opp.includes(p))) return tag;
  }
  return '差异化机会';
}

function OpportunityCard({ opp, refProduct, index }: { opp: string; refProduct: any; index: number }) {
  const themes = [
    { border: '#bfdbfe', bg: '#eff6ff', accent: '#2563eb', light: '#dbeafe' },
    { border: '#d1fae5', bg: '#ecfdf5', accent: '#059669', light: '#a7f3d0' },
    { border: '#fde68a', bg: '#fffbeb', accent: '#d97706', light: '#fef3c7' },
    { border: '#ddd6fe', bg: '#f5f3ff', accent: '#7c3aed', light: '#ede9fe' },
  ];
  const theme = themes[index % themes.length];
  const tag = extractOpportunityTag(opp);

  return (
    <div
      className="opportunity-card"
      style={{ borderLeftColor: theme.accent, borderColor: theme.border, background: theme.bg }}
    >
      <div className="opportunity-index" style={{ color: theme.accent, borderColor: theme.border, background: '#ffffff' }}>
        {index + 1}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="opportunity-title">{opp}</div>
        <span className="badge" style={{ background: '#ffffff', color: theme.accent, border: `1px solid ${theme.border}` }}>
          <TagOutlined style={{ fontSize: 10, marginRight: 4 }} />{tag}
        </span>
      </div>
      {refProduct && (
        <a href={refProduct.link} target="_blank" rel="noreferrer" className="opportunity-ref" style={{ '--accent': theme.accent, '--bg': theme.bg, '--border': theme.border } as React.CSSProperties}>
          <img src={refProduct.image} alt="" style={{ width: 44, height: 44, borderRadius: 'var(--radius-sm)', objectFit: 'cover', background: 'var(--saas-card)' }} />
          <div style={{ textAlign: 'left', minWidth: 0 }}>
            <div className="opportunity-ref-title">{refProduct.title}</div>
            <div className="opportunity-ref-action" style={{ color: theme.accent }}>${refProduct.price} · 查看 →</div>
          </div>
        </a>
      )}
    </div>
  );
}

function SentimentSummary({ report }: { report: AnalysisReport }) {
  const painCount = report.review_insights.pain_points.length;
  const praiseCount = report.review_insights.praised_features.length;
  const total = painCount + praiseCount || 1;
  const painPct = Math.round((painCount / total) * 100);
  const praisePct = Math.round((praiseCount / total) * 100);

  return (
    <div className="sentiment-grid">
      <div className="sentiment-card sentiment-pain">
        <div className="sentiment-card-header">
          <div className="sentiment-icon" style={{ background: '#fef2f2', color: '#dc2626' }}>
            <ExclamationCircleOutlined />
          </div>
          <div>
            <div className="sentiment-label" style={{ color: '#dc2626' }}>痛点提及占比</div>
            <div className="sentiment-value" style={{ color: '#b91c1c' }}>{painPct}%</div>
          </div>
        </div>
        <div className="sentiment-bar-row">
          <div className="big-bar-bg">
            <div className="big-bar-fill" style={{ width: `${painPct}%`, ['--bar-start' as string]: '#dc2626', ['--bar-end' as string]: '#f87171' }} />
          </div>
          <span className="sentiment-count">{painCount} 项</span>
        </div>
      </div>
      <div className="sentiment-card sentiment-praise">
        <div className="sentiment-card-header">
          <div className="sentiment-icon" style={{ background: '#ecfdf5', color: '#059669' }}>
            <CheckCircleOutlined />
          </div>
          <div>
            <div className="sentiment-label" style={{ color: '#059669' }}>好评提及占比</div>
            <div className="sentiment-value" style={{ color: '#047857' }}>{praisePct}%</div>
          </div>
        </div>
        <div className="sentiment-bar-row">
          <div className="big-bar-bg">
            <div className="big-bar-fill" style={{ width: `${praisePct}%`, ['--bar-start' as string]: '#059669', ['--bar-end' as string]: '#34d399' }} />
          </div>
          <span className="sentiment-count">{praiseCount} 项</span>
        </div>
      </div>
      <div className="sentiment-card sentiment-opportunity">
        <div className="sentiment-card-header">
          <div className="sentiment-icon" style={{ background: '#eff6ff', color: '#2563eb' }}>
            <BulbOutlined />
          </div>
          <div>
            <div className="sentiment-label" style={{ color: '#2563eb' }}>潜在机会</div>
            <div className="sentiment-value" style={{ color: '#1d4ed8' }}>{report.review_insights.opportunities.length} 项</div>
          </div>
        </div>
        <div className="sentiment-desc">
          基于痛点与好评提炼的差异化方向
        </div>
      </div>
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
      <div className="page-hero">
        <div>
          <div className="page-header">评论洞察</div>
          <div className="page-subtitle">基于用户评价挖掘痛点、卖点与差异化机会</div>
        </div>
        {report && (
          <span className="section-badge">
            <CommentOutlined /> 当前分析：{report.keyword}
          </span>
        )}
      </div>
      <Card className="search-card">
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>正在分析评论数据...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="评论洞察" />}

      {!loading && report && (
        <>
          <div className="info-card" style={{ marginBottom: 24, padding: '22px 24px' }}>
            <div className="review-overview">
              <div className="review-overview-main">
                <div className="info-card-title" style={{ marginBottom: 4, paddingBottom: 0, borderBottom: 'none' }}>
                  <CommentOutlined style={{ color: 'var(--saas-primary)' }} /> 评论洞察总览
                </div>
                <Text style={{ color: 'var(--saas-text-muted)', fontSize: 13, fontWeight: 500 }}>
                  基于「<Text strong style={{ color: 'var(--saas-primary)' }}>{report.keyword}</Text>」用户评论提取的高频痛点、好评卖点与潜在机会。
                </Text>
              </div>
              <div className="review-overview-stats">
                <StatBadge label="痛点" value={`${report.review_insights.pain_points.length} 项`} color="#dc2626" bg="#fef2f2" border="#fee2e2" icon={<CloseCircleOutlined />} />
                <StatBadge label="好评" value={`${report.review_insights.praised_features.length} 项`} color="#059669" bg="#ecfdf5" border="#d1fae5" icon={<CheckCircleOutlined />} />
                <StatBadge label="机会" value={`${report.review_insights.opportunities.length} 项`} color="#2563eb" bg="#eff6ff" border="#bfdbfe" icon={<RiseOutlined />} />
              </div>
            </div>
          </div>

          <SentimentSummary report={report} />

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <div className="info-card">
                <div className="info-card-title" style={{ color: '#dc2626' }}>
                  <CloseCircleOutlined style={{ marginRight: 8 }} /> 用户痛点
                </div>
                <div className="section-desc">
                  这些是用户反复提及的不满点，是产品升级与差异化最直接的切入口。
                </div>
                {report.review_insights.pain_points.slice(0, 5).map((p: string, i: number) => (
                  <ReviewCard key={i} text={p} i={i + 1} kind="pain" />
                ))}
              </div>
            </Col>
            <Col xs={24} lg={12}>
              <div className="info-card">
                <div className="info-card-title" style={{ color: '#059669' }}>
                  <CheckCircleOutlined style={{ marginRight: 8 }} /> 用户好评
                </div>
                <div className="section-desc">
                  这些是用户认可的核心卖点，应在 Listing 与广告投放中重点突出。
                </div>
                {report.review_insights.praised_features.slice(0, 5).map((p: string, i: number) => (
                  <ReviewCard key={i} text={p} i={i + 1} kind="praise" />
                ))}
              </div>
            </Col>
          </Row>

          <div className="info-card" style={{ marginTop: 24 }}>
            <div className="info-card-title">
              <BulbOutlined style={{ color: 'var(--saas-warning)' }} /> 差异化机会
            </div>
            <div className="section-desc">
              基于「<strong style={{ color: 'var(--saas-primary)' }}>{report.keyword}</strong>」用户评论洞察，围绕痛点做定向升级，可形成核心差异化卖点。
            </div>
            {report.review_insights.opportunities.map((opp: string, idx: number) => {
              const competitors = report.market_analysis.competitors;
              const ref = competitors[idx % Math.min(3, competitors.length)] || null;
              return <OpportunityCard key={idx} opp={opp} refProduct={ref} index={idx} />;
            })}
          </div>
        </>
      )}
    </div>
  );
}
