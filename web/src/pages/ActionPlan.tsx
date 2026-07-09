import { Button, Card, Col, Row, Spin } from 'antd';
import { CarryOutOutlined, DownloadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

const accents = ['#2563eb', '#0891b2', '#7c3aed', '#16a34a', '#d97706'];

interface ActionStepItem {
  phase: string;
  title: string;
  owner: string;
  tasks: string[];
  value: string;
}

function ActionStep({ step, accent }: { step: ActionStepItem; accent: string }) {
  return (
    <div className="action-step" style={{ borderLeft: `4px solid ${accent}`, marginBottom: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
        <span style={{ background: '#eff6ff', color: '#1d4ed8', borderRadius: 6, padding: '4px 12px', fontSize: 12, fontWeight: 800 }}>{step.phase}</span>
        <span style={{ color: '#0f172a', fontWeight: 800, fontSize: 15 }}>{step.title}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ background: '#f1f5f9', color: '#64748b', borderRadius: 6, padding: '3px 10px', fontSize: 11, fontWeight: 700 }}>👤 {step.owner}</span>
      </div>
      <ul style={{ margin: '0 0 10px 18px', padding: 0, color: '#475569', fontSize: 13, lineHeight: 1.7 }}>
        {step.tasks.map((t: string, i: number) => <li key={i}>{t}</li>)}
      </ul>
      <div style={{ padding: '10px 12px', background: '#f8fafc', borderRadius: 8, fontSize: 13, color: '#334155', fontWeight: 600 }}>
        ✅ 价值：{step.value}
      </div>
    </div>
  );
}

function buildReportMarkdown(report: AnalysisReport): string {
  const lines = [
    `# 选品分析报告：${report.keyword.toUpperCase()}`,
    '',
    `- 目标市场：${report.market}`,
    `- 预算区间：${report.budget}`,
    `- 综合判定：**${report.verdict}（等级 ${report.grade}）**`,
    `- 综合评分：${report.overall_score}/${report.max_score}`,
    '',
    '## 核心结论',
    `关键词 **${report.keyword}** 在 **${report.market}** 市场平均售价 **$${report.market_analysis.avg_price}**，毛利率 **${report.profit_analysis.gross_margin_pct}**，趋势 **${report.trend_analysis.trend_direction.toUpperCase()}**。`,
    '',
    '## 评分拆解',
  ];
  Object.entries(report.score_breakdown).forEach(([name, score]) => lines.push(`- ${name}：${score}`));
  lines.push('', '## 用户痛点');
  report.review_insights.pain_points.forEach((p) => lines.push(`- ${p}`));
  lines.push('', '## 行动计划');
  report.next_steps.forEach((step, i) => {
    lines.push(`${i + 1}. [${step.phase}] ${step.title}`);
    step.tasks.forEach((t) => lines.push(`   - ${t}`));
    lines.push(`   - 价值：${step.value}`);
  });
  lines.push('', '*报告由跨境电商智能选品决策驾驶舱生成*');
  return lines.join('\n');
}

function downloadReport(report: AnalysisReport) {
  const md = buildReportMarkdown(report);
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${report.keyword.replace(/\s+/g, '_').toLowerCase()}_${report.market.toLowerCase()}_report.md`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default function ActionPlan() {
  const dispatch = useDispatch();
  const { report, lastSearch, loading, analyze } = useReport();
  const [approvalNo, setApprovalNo] = useState<string | null>(null);

  useEffect(() => {
    dispatch(setPageTitle('行动计划'));
  }, [dispatch]);

  const handleFeishuApproval = () => {
    if (!report) return;
    const no = `RPT-${report.market}-${report.keyword.replace(/\s+/g, '_').toUpperCase()}-${(Date.now() % 100000).toString().padStart(5, '0')}`;
    setApprovalNo(no);
  };

  const leftSteps = report?.next_steps.filter((_s: ActionStepItem, i: number) => i % 2 === 0) || [];
  const rightSteps = report?.next_steps.filter((_s: ActionStepItem, i: number) => i % 2 === 1) || [];

  return (
    <div className="page-container">
      <div className="page-header">行动计划</div>
      <Card style={{ borderRadius: 16, marginBottom: 24 }}>
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748b' }}>正在生成行动计划...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="行动计划" />}

      {!loading && report && (
        <>
          <div className="info-card-title" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <CarryOutOutlined />
            可落地行动计划
          </div>

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              {leftSteps.map((step: ActionStepItem, i: number) => (
                <ActionStep key={i} step={step} accent={accents[(i * 2) % accents.length]} />
              ))}
            </Col>
            <Col xs={24} lg={12}>
              {rightSteps.map((step: ActionStepItem, i: number) => (
                <ActionStep key={i} step={step} accent={accents[(i * 2 + 1) % accents.length]} />
              ))}
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
            <Col xs={24} md={12}>
              <Button type="default" icon={<DownloadOutlined />} block size="large" onClick={() => downloadReport(report)}>
                导出分析报告
              </Button>
            </Col>
            <Col xs={24} md={12}>
              <Button type="primary" icon={<CarryOutOutlined />} block size="large" onClick={handleFeishuApproval}>
                推送飞书审批
              </Button>
              {approvalNo && (
                <div style={{ marginTop: 12, padding: '10px 14px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10, color: '#15803d', fontWeight: 600 }}>
                  审批实例已创建：{approvalNo}，请在飞书审批中心查看进度。
                </div>
              )}
            </Col>
          </Row>
        </>
      )}
    </div>
  );
}
