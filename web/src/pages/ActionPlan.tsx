import { Button, Card, Col, Row, Spin } from 'antd';
import { CarryOutOutlined, DownloadOutlined, PushpinOutlined, SolutionOutlined, UserOutlined, CheckCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useDispatch } from 'react-redux';
import AnalysisSearchForm from '../components/AnalysisSearchForm';
import EmptyReport from '../components/EmptyReport';
import { useReport } from '../hooks/useReport';
import { setPageTitle } from '../store/slices/uiSlice';
import type { AnalysisReport } from '../types';

const accents = ['var(--saas-primary)', 'var(--saas-info)', 'var(--saas-purple)', 'var(--saas-success)', 'var(--saas-warning)'];

interface ActionStepItem {
  phase: string;
  title: string;
  owner: string;
  tasks: string[];
  value: string;
}

const phaseIcons: Record<string, React.ReactNode> = {
  '市场验证': <PushpinOutlined />,
  '供应链': <SolutionOutlined />,
  '利润测算': <CarryOutOutlined />,
  '合规': <CheckCircleOutlined />,
  '上线准备': <ThunderboltOutlined />,
};

function ActionStep({ step, accent, index }: { step: ActionStepItem; accent: string; index: number }) {
  return (
    <div className="action-step-card" style={{ ['--step-accent' as string]: accent } as React.CSSProperties}>
      <div className="action-step-marker">
        <div className="action-step-number">{index + 1}</div>
        <div className="action-step-line" />
      </div>
      <div className="action-step-body">
        <div className="action-step-header">
          <span className="action-step-phase">
            {phaseIcons[step.phase] || <CarryOutOutlined />}
            {step.phase}
          </span>
          <span className="action-step-owner">
            <UserOutlined /> {step.owner}
          </span>
        </div>
        <div className="action-step-title">{step.title}</div>
        <ul className="action-step-tasks">
          {step.tasks.map((t: string, i: number) => <li key={i}>{t}</li>)}
        </ul>
        <div className="action-step-value">
          <CheckCircleOutlined style={{ color: 'var(--saas-success)' }} />
          价值：{step.value}
        </div>
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

  const steps = report?.next_steps || [];

  return (
    <div className="page-container">
      <div className="page-hero">
        <div>
          <div className="page-header">行动计划</div>
          <div className="page-subtitle">基于分析结果拆解为可执行步骤，明确责任人、验收标准与业务价值</div>
        </div>
        {report && (
          <span className="section-badge">
            <CarryOutOutlined /> 当前分析：{report.keyword}
          </span>
        )}
      </div>
      <Card className="search-card">
        <AnalysisSearchForm initialValues={lastSearch} onSubmit={analyze} loading={loading} />
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--saas-text-muted)', fontWeight: 500 }}>正在生成行动计划...</div>
        </div>
      )}

      {!loading && !report && <EmptyReport pageName="行动计划" />}

      {!loading && report && (
        <>
          <div className="info-card" style={{ marginBottom: 24 }}>
            <div className="info-card-title">
              <CarryOutOutlined style={{ color: 'var(--saas-primary)' }} />
              可落地行动计划
            </div>
            <div className="section-desc">
              以下是为「{report.keyword}」生成的执行路径，共 {steps.length} 个阶段。每个阶段已标注负责角色与预期价值，可直接用于团队排期或飞书审批。
            </div>
            <div className="action-timeline">
              {steps.map((step: ActionStepItem, i: number) => (
                <ActionStep key={i} step={step} accent={accents[i % accents.length]} index={i} />
              ))}
            </div>
          </div>

          <Row gutter={[24, 24]}>
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
                <div className="action-approval-toast">
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
