import {
  ApartmentOutlined,
  BarChartOutlined,
  BulbOutlined,
  CalendarOutlined,
  CarryOutOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  DollarOutlined,
  EyeOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  FilterOutlined,
  FlagOutlined,
  GlobalOutlined,
  RiseOutlined,
  SafetyOutlined,
  ShareAltOutlined,
  StockOutlined,
  TrophyOutlined,
} from '@ant-design/icons'
import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import ReactECharts from 'echarts-for-react'
import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
import { analysisApi } from '../services/api'
import { getReportHistory } from '../hooks/useReport'
import { useMobile } from '../hooks/useMobile'
import { generateMockReport } from '../services/mockData'
import { setCurrentReport, setPageTitle } from '../store/slices/uiSlice'
import type { AnalysisHistoryItem, AnalysisReport } from '../types'
import { getMarketCurrency } from '../utils/currency'

const { Text, Title } = Typography

const DARK_TOOLTIP = {
  backgroundColor: 'rgba(30, 41, 59, 0.92)',
  borderWidth: 0,
  padding: [5, 8],
  confine: true,
  textStyle: { color: '#ffffff', fontFamily: 'var(--font-sans)', fontSize: 11 },
  extraCssText: 'max-width:240px !important;width:auto !important;min-width:0 !important;word-wrap:break-word !important;white-space:normal !important;border-radius:4px !important;box-shadow:0 2px 8px rgba(0,0,0,0.15) !important;backdrop-filter:blur(4px) !important;',
}

const GRADE_COLORS: Record<string, string> = {
  A: '#16a34a',
  B: '#2563eb',
  C: '#d97706',
  D: '#dc2626',
}

const COUNTRY_COLORS: Record<string, string> = {
  US: '#dc2626',
  UK: '#2563eb',
  DE: '#f59e0b',
  JP: '#0891b2',
  CA: '#7c3aed',
}

const SEGMENT_COLORS = ['#2563eb', '#059669', '#d97706', '#7c3aed', '#0891b2', '#db2777', '#64748b']

export default function ReportCenter() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([])
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [filterGrade, setFilterGrade] = useState<string>('')
  const [filterKeyword, setFilterKeyword] = useState('')
  const [detailId, setDetailId] = useState<string | null>(null)
  const [detail, setDetail] = useState<AnalysisReport | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const isMobile = useMobile()

  useEffect(() => {
    dispatch(setPageTitle('报告中心'))
  }, [dispatch])

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = () => {
    setLoading(true)
    analysisApi
      .history()
      .then((res) => {
        const items = res.data.items || []
        // 合并本地历史（离线/Mock 模式下有数据可展示）
        const localItems = getReportHistory()
        const merged = [...items]
        localItems.forEach((local) => {
          if (!merged.some((h) => h.id === local.id)) merged.push(local)
        })
        merged.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        setHistory(merged)
      })
      .catch(() => {
        // API 不可用则完全使用本地存储
        setHistory(getReportHistory())
      })
      .finally(() => setLoading(false))
  }

  const createSampleReports = () => {
    const samples = [
      { keyword: 'dog chew toys', market: 'US', budget: '$5,000 - $10,000' },
      { keyword: 'sports water bottle', market: 'US', budget: '$5,000 - $10,000' },
      { keyword: 'wireless earbuds', market: 'US', budget: '$10,000 - $50,000' },
    ]
    const newItems: AnalysisHistoryItem[] = []
    const now = Date.now()
    samples.forEach((s, i) => {
      const report = generateMockReport(s.keyword, s.market, s.budget)
      const item: AnalysisHistoryItem = {
        id: `${now}_${i}_${Math.random().toString(36).slice(2, 8)}`,
        keyword: report.keyword,
        market: report.market,
        grade: report.grade,
        overall_score: report.overall_score,
        created_at: new Date(now - i * 3600000).toISOString(),
      }
      localStorage.setItem(`xuanpin_report_detail_${item.id}`, JSON.stringify(report))
      newItems.push(item)
    })
    setHistory((prev) => {
      const next = [...newItems, ...prev]
      try {
        localStorage.setItem('xuanpin_report_history', JSON.stringify(next.slice(0, 50)))
      } catch {}
      return next
    })
    message.success(`已生成 ${newItems.length} 条示例报告，可点击详情查看综合分析`)
  }

  const filteredHistory = useMemo(() => {
    return history.filter((h) => {
      const matchGrade = filterGrade ? h.grade === filterGrade : true
      const matchKeyword = filterKeyword ? h.keyword.toLowerCase().includes(filterKeyword.toLowerCase()) : true
      return matchGrade && matchKeyword
    })
  }, [history, filterGrade, filterKeyword])

  const showDetail = (id: string) => {
    setDetailId(id)
    // 优先从本地存储读取完整报告详情
    try {
      const local = localStorage.getItem(`xuanpin_report_detail_${id}`)
      if (local) {
        const parsed = JSON.parse(local) as AnalysisReport
        const hasEnoughOpportunities = (parsed.market_analysis?.keyword_opportunities?.length || 0) >= 10
        if (parsed.version === 3 && hasEnoughOpportunities) {
          setDetail(parsed)
          return
        }
        // 旧版本或数据不完整报告迁移
        if (parsed.keyword && parsed.market && parsed.budget) {
          const migrated = generateMockReport(parsed.keyword, parsed.market, parsed.budget)
          localStorage.setItem(`xuanpin_report_detail_${id}`, JSON.stringify(migrated))
          setDetail(migrated)
          return
        }
      }
    } catch {}
    analysisApi.get(id).then((res) => setDetail(res.data.report))
  }

  const exportCSV = (items: AnalysisHistoryItem[]) => {
    const rows = [
      ['报告ID', '关键词', '市场', '综合评分', '等级', '毛利率', '趋势', '创建时间'],
      ...items.map((h) => [h.id, h.keyword, h.market, h.overall_score, h.grade, '', '', new Date(h.created_at).toLocaleString()]),
    ]
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `reports_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
    message.success(`已导出 ${items.length} 条报告`)
  }

  const exportSinglePdfFromRecord = async (record: AnalysisHistoryItem) => {
    let report: AnalysisReport | null = null
    try {
      const local = localStorage.getItem(`xuanpin_report_detail_${record.id}`)
      if (local) {
        const parsed = JSON.parse(local) as AnalysisReport
        const hasEnoughOpportunities = (parsed.market_analysis?.keyword_opportunities?.length || 0) >= 10
        if (parsed.version === 3 && hasEnoughOpportunities) {
          report = parsed
        } else if (parsed.keyword && parsed.market && parsed.budget) {
          report = generateMockReport(parsed.keyword, parsed.market, parsed.budget)
        }
      }
    } catch {}
    if (!report) {
      report = generateMockReport(record.keyword, record.market, '$5,000 - $10,000')
    }
    await downloadReportPdf(report)
  }

  const exportSelectedPDF = async () => {
    const items = selectedRowKeys.length > 0
      ? filteredHistory.filter((h) => selectedRowKeys.includes(h.id))
      : filteredHistory.slice(0, 1)
    if (items.length === 0) {
      message.warning('没有可导出的报告')
      return
    }
    setPdfLoading(true)
    try {
      for (const item of items) {
        await exportSinglePdfFromRecord(item)
      }
      message.success(`已导出 ${items.length} 条报告 PDF`)
    } catch (error) {
      console.error('批量 PDF 导出失败:', error)
      message.error('PDF 导出失败')
    } finally {
      setPdfLoading(false)
    }
  }

  const shareReport = (id: string) => {
    const url = `${window.location.origin}/dashboard?id=${id}`
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(url).then(() => message.success('分享链接已复制到剪贴板'))
    } else {
      message.info(`分享链接：${url}`)
    }
  }

  const deleteReport = (id: string) => {
    setHistory((prev) => prev.filter((h) => h.id !== id))
    message.success('报告已删除')
  }

  const columns = useMemo(() => {
    const base: any[] = [
      { title: '关键词', dataIndex: 'keyword', key: 'keyword', width: isMobile ? 140 : 180, ellipsis: true },
      { title: '市场', dataIndex: 'market', key: 'market', width: 80, align: 'center' as const },
      {
        title: '等级',
        dataIndex: 'grade',
        key: 'grade',
        width: 70,
        align: 'center' as const,
        render: (v: string) => (
          <Tag color={GRADE_COLORS[v] || '#64748b'} style={{ fontWeight: 800 }}>{v}</Tag>
        ),
      },
      {
        title: '评分',
        dataIndex: 'overall_score',
        key: 'overall_score',
        width: 80,
        align: 'center' as const,
        render: (v: number) => (
          <Text strong style={{ color: v >= 70 ? '#16a34a' : v >= 50 ? '#d97706' : '#dc2626' }}>
            {v}
          </Text>
        ),
      },
    ]
    if (!isMobile) {
      base.push({
        title: '时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: 160,
        render: (v: string) => new Date(v).toLocaleString(),
      })
    }
    base.push({
      title: '操作',
      key: 'action',
      width: isMobile ? 170 : 260,
      render: (_: unknown, record: AnalysisHistoryItem) => (
        <Space size="small">
          <Button type="link" icon={<EyeOutlined />} onClick={() => showDetail(record.id)} size={isMobile ? 'small' : 'middle'}>
            {isMobile ? '' : '详情'}
          </Button>
          <Button type="link" icon={<FilePdfOutlined />} onClick={() => exportSinglePdfFromRecord(record)} size={isMobile ? 'small' : 'middle'}>
            {isMobile ? '' : 'PDF'}
          </Button>
          <Button type="link" icon={<ShareAltOutlined />} onClick={() => shareReport(record.id)} size={isMobile ? 'small' : 'middle'}>
            {isMobile ? '' : '分享'}
          </Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => deleteReport(record.id)} size={isMobile ? 'small' : 'middle'}>
            {isMobile ? '' : '删除'}
          </Button>
        </Space>
      ),
    })
    return base
  }, [isMobile])

  return (
    <div className="page-container">
      <div className="page-header">报告中心</div>
      <div className="page-subtitle">管理历史分析报告，支持筛选、导出与分享</div>

      <Card className="search-card" style={{ borderRadius: 'var(--radius-lg)', marginBottom: 24, boxShadow: 'var(--shadow-card)' }} title={<><FilterOutlined /> 筛选</>}>
        <Form layout="inline">
          <Form.Item label="关键词">
            <Input placeholder="搜索关键词" value={filterKeyword} onChange={(e) => setFilterKeyword(e.target.value)} allowClear />
          </Form.Item>
          <Form.Item label="等级">
            <Select style={{ width: 120 }} allowClear value={filterGrade} onChange={setFilterGrade} placeholder="全部等级">
              <Select.Option value="A">A</Select.Option>
              <Select.Option value="B">B</Select.Option>
              <Select.Option value="C">C</Select.Option>
              <Select.Option value="D">D</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button icon={<FileTextOutlined />} onClick={() => navigate('/dashboard')}>
              新建分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title={`报告列表（共 ${filteredHistory.length} 条）`}
        extra={
          <Space>
            <Button icon={<FileTextOutlined />} onClick={createSampleReports}>
              生成示例报告
            </Button>
            <Button icon={<FileExcelOutlined />} onClick={() => exportCSV(filteredHistory)}>
              导出 Excel
            </Button>
            <Button icon={<FilePdfOutlined />} loading={pdfLoading} onClick={exportSelectedPDF}>
              导出 PDF
            </Button>
          </Space>
        }
      >
        <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          <Table
            rowKey="id"
            columns={columns}
            dataSource={filteredHistory}
            loading={loading}
            pagination={{ pageSize: 10 }}
            scroll={{ x: isMobile ? 540 : 'max-content' }}
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
          />
        </div>
        {filteredHistory.length === 0 && !loading && (
          <Empty description="暂无报告">
            <Button type="primary" icon={<FileTextOutlined />} onClick={createSampleReports}>
              生成示例报告
            </Button>
          </Empty>
        )}
      </Card>

      <Modal
        title={
          <Space>
            <FileTextOutlined style={{ color: 'var(--saas-primary)' }} />
            <span>综合分析报告</span>
          </Space>
        }
        open={!!detailId}
        onCancel={() => { setDetailId(null); setDetail(null) }}
        width={960}
        footer={[
          <Button key="close" onClick={() => { setDetailId(null); setDetail(null) }}>关闭</Button>,
          detail && (
            <Button key="export" type="primary" icon={<FilePdfOutlined />} loading={pdfLoading} onClick={() => downloadReportPdf(detail, setPdfLoading)}>
              导出 PDF
            </Button>
          ),
          detail && (
            <Button key="view" type="primary" onClick={() => { dispatch(setCurrentReport(detail)); navigate('/dashboard'); setDetailId(null); setDetail(null) }}>
              查看完整报告
            </Button>
          ),
        ]}
      >
        {detail ? (
          <ReportDetailView report={detail} />
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        )}
      </Modal>
    </div>
  )
}

function ReportDetailView({ report }: { report: AnalysisReport }) {
  const trendText = report.trend_analysis.trend_direction === 'rising' ? '上升' : report.trend_analysis.trend_direction === 'stable' ? '稳定' : '下滑'
  const trendColor = report.trend_analysis.trend_direction === 'rising' ? '#16a34a' : report.trend_analysis.trend_direction === 'stable' ? '#d97706' : '#dc2626'
  const profit = report.profit_analysis
  const market = report.market_analysis

  const tabItems = [
    {
      key: 'overview',
      label: '报告概览',
      children: <ReportOverviewTab report={report} />,
    },
    {
      key: 'market',
      label: '市场分析',
      children: <ReportMarketTab market={market} currencySymbol={getMarketCurrency(report.market).symbol} />,
    },
    {
      key: 'trend',
      label: '趋势与合规',
      children: <ReportTrendComplianceTab report={report} />,
    },
    {
      key: 'profit',
      label: '利润测算',
      children: <ReportProfitTab profit={profit} currencySymbol={getMarketCurrency(report.market).symbol} />,
    },
    {
      key: 'review',
      label: '评论洞察',
      children: <ReportReviewTab report={report} />,
    },
    {
      key: 'action',
      label: '行动计划',
      children: <ReportActionTab report={report} />,
    },
  ]

  return (
    <div style={{ marginTop: 8 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
          padding: 20,
          background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #eff6ff 100%)',
          border: '1px solid rgba(37, 99, 235, 0.1)',
          borderRadius: 12,
          marginBottom: 20,
        }}
      >
        <div>
          <Title level={4} style={{ margin: 0, marginBottom: 8 }}>
            {report.keyword}
            <Tag color={report.verdict_color} style={{ marginLeft: 12, fontWeight: 800 }}>{report.verdict}</Tag>
          </Title>
          <Text type="secondary">
            {market.market_profile.name} · 预算 {report.budget} · 综合评分 {report.overall_score}/{report.max_score}
          </Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ textAlign: 'center', minWidth: 80 }}>
            <div style={{ fontSize: 11, color: '#64748b', fontWeight: 800, marginBottom: 4 }}>等级</div>
            <Tag color={GRADE_COLORS[report.grade] || '#64748b'} style={{ fontSize: 16, fontWeight: 900, padding: '2px 12px' }}>{report.grade}</Tag>
          </div>
          <div style={{ textAlign: 'center', minWidth: 90 }}>
            <div style={{ fontSize: 11, color: '#64748b', fontWeight: 800, marginBottom: 4 }}>毛利率</div>
            <div style={{ fontSize: 18, fontWeight: 900, color: profit.gross_margin >= 0.2 ? '#16a34a' : profit.gross_margin >= 0.1 ? '#d97706' : '#dc2626' }}>
              {profit.gross_margin_pct}
            </div>
          </div>
          <div style={{ textAlign: 'center', minWidth: 80 }}>
            <div style={{ fontSize: 11, color: '#64748b', fontWeight: 800, marginBottom: 4 }}>趋势</div>
            <div style={{ fontSize: 14, fontWeight: 800, color: trendColor }}>{trendText}</div>
          </div>
          <Button type="primary" icon={<FilePdfOutlined />} onClick={() => downloadReportPdf(report)} style={{ marginLeft: 8 }}>
            导出 PDF
          </Button>
        </div>
      </div>

      <Tabs items={tabItems} defaultActiveKey="overview" />
    </div>
  )
}

function ReportOverviewTab({ report }: { report: AnalysisReport }) {
  const market = report.market_analysis
  const profit = report.profit_analysis
  const trend = report.trend_analysis
  const { symbol } = getMarketCurrency(report.market)
  const radarOption = useMemo(() => buildReportRadarOption(report), [report])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={8}>
          <MetricCard label="市场均价" value={`${market.market_profile.currency}${market.avg_price}`} icon={<DollarOutlined />} color="#2563eb" />
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <MetricCard label="平均评分" value={`${market.avg_rating} / 5.0`} icon={<TrophyOutlined />} color="#d97706" />
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <MetricCard label="评论基数" value={`${market.avg_reviews.toLocaleString()}+`} icon={<BarChartOutlined />} color="#7c3aed" />
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <MetricCard label="单件毛利" value={`${symbol}${profit.gross_profit_per_unit.toFixed(2)}`} icon={<RiseOutlined />} color="#16a34a" />
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <MetricCard label="盈亏平衡" value={`${profit.breakeven_units ?? 'N/A'} 件`} icon={<StockOutlined />} color="#0891b2" />
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <MetricCard label="旺季月份" value={trend.peak_months.slice(0, 3).join('、') + '月'} icon={<CalendarOutlined />} color="#dc2626" />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card size="small" title={<><BarChartOutlined /> 五维能力雷达</>}>
            <ReactECharts key={`report-radar-${report.keyword}`} option={radarOption} style={{ height: 320 }} notMerge={true} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title={<><FlagOutlined /> 核心结论</>}>
            <Text>
              关键词 <strong>{report.keyword}</strong> 在 <strong>{market.market_profile.name}</strong> 市场平均售价
              <strong> {market.market_profile.currency}{market.avg_price}</strong>，毛利率
              <strong style={{ color: report.verdict_color }}> {profit.gross_margin_pct}</strong>，
              趋势 <strong>{trend.trend_direction === 'rising' ? '上升' : trend.trend_direction === 'stable' ? '稳定' : '下滑'}</strong>。
              综合判定为 <strong style={{ color: report.verdict_color }}>{report.verdict}</strong>。
            </Text>
          </Card>
          <Card size="small" title={<><BulbOutlined /> 关键建议</>} style={{ marginTop: 16 }}>
            <ul style={{ margin: 0, paddingLeft: 18, color: '#475569', lineHeight: 1.9 }}>
              {report.next_steps.slice(0, 3).map((step, i) => (
                <li key={i}><strong>{step.phase}</strong>：{step.title} — {step.value}</li>
              ))}
            </ul>
          </Card>
        </Col>
      </Row>
    </Space>
  )
}

function GlobalTrendsMiniChart({ trends }: { trends: NonNullable<AnalysisReport['market_analysis']['global_trends']> }) {
  const option = useMemo(() => {
    const months = trends[0].months
    return {
      tooltip: { trigger: 'axis' as const, ...DARK_TOOLTIP },
      legend: { data: trends.map((t) => t.name), top: 0, right: 0, textStyle: { color: 'var(--saas-text-secondary)', fontSize: 11, fontWeight: 700 } },
      grid: { left: 10, right: 10, top: 34, bottom: 10, containLabel: true },
      xAxis: { type: 'category' as const, data: months, axisLine: { lineStyle: { color: 'var(--saas-border)' } }, axisLabel: { color: 'var(--saas-text-muted)', fontSize: 11 } },
      yAxis: { type: 'value' as const, name: '热度', min: 0, max: 100, splitLine: { lineStyle: { color: 'var(--saas-border)' } }, axisLabel: { color: 'var(--saas-text-muted)', fontSize: 11 } },
      series: trends.map((t) => ({
        type: 'line' as const,
        name: t.name,
        data: t.values,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: COUNTRY_COLORS[t.code] || '#64748b' },
        itemStyle: { color: COUNTRY_COLORS[t.code] || '#64748b' },
      })),
    }
  }, [trends])

  return <ReactECharts option={option} style={{ height: 200 }} />
}

function KeywordRelationSuggestions({ rel }: { rel: NonNullable<AnalysisReport['market_analysis']['keyword_relationships']> }) {
  return (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      {rel.expansion_suggestions.map((s, i) => (
        <div
          key={i}
          style={{
            padding: 10,
            background: '#f8fafc',
            border: '1px solid var(--saas-border-subtle)',
            borderRadius: 8,
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--saas-text)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <BulbOutlined style={{ color: SEGMENT_COLORS[i % SEGMENT_COLORS.length] }} />
            {s.segment}
            <span style={{ marginLeft: 'auto', fontSize: 11, color: s.avg_score >= 60 ? '#dc2626' : '#d97706' }}>平均机会分 {s.avg_score}</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--saas-text-secondary)', lineHeight: 1.5, marginBottom: 6 }}>{s.rationale}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {s.keywords.map((kw, j) => (
              <Tag key={j} style={{ fontSize: 10, fontWeight: 700, background: '#eff6ff', color: '#1d4ed8', border: '1px solid #dbeafe' }}>
                {kw}
              </Tag>
            ))}
          </div>
        </div>
      ))}
    </Space>
  )
}

function ReportMarketTab({ market, currencySymbol }: { market: AnalysisReport['market_analysis']; currencySymbol: string }) {
  const top5 = market.competitors.slice(0, 5)
  const data = top5.map((c: any, i: number) => ({
    rank: i + 1,
    title: c.title,
    brand: c.brand,
    price: `${currencySymbol}${c.price.toFixed(2)}`,
    rating: c.rating,
    reviews: c.review_count.toLocaleString(),
    bsr: c.bsr,
    sales: c.estimated_monthly_sales.toLocaleString(),
  }))
  const barOption = useMemo(() => buildCompetitorBarOption(top5), [top5])

  const cols = [
    { title: '排名', dataIndex: 'rank', width: 60, align: 'center' as const },
    { title: '产品', dataIndex: 'title', ellipsis: true },
    { title: '品牌', dataIndex: 'brand', width: 100 },
    { title: '价格', dataIndex: 'price', width: 80, align: 'right' as const },
    { title: '评分', dataIndex: 'rating', width: 70, align: 'center' as const },
    { title: '评论数', dataIndex: 'reviews', width: 90, align: 'right' as const },
    { title: 'BSR', dataIndex: 'bsr', width: 90, align: 'right' as const },
    { title: '月销量', dataIndex: 'sales', width: 100, align: 'right' as const },
  ]

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}>
          <MiniMetric label="竞品数量" value={`${market.competitors.length} 款`} />
        </Col>
        <Col xs={12} sm={6}>
          <MiniMetric label="市场均价" value={`${market.market_profile.currency}${market.avg_price}`} />
        </Col>
        <Col xs={12} sm={6}>
          <MiniMetric label="平均评分" value={market.avg_rating} />
        </Col>
        <Col xs={12} sm={6}>
          <MiniMetric label="平均评论" value={market.avg_reviews.toLocaleString()} />
        </Col>
      </Row>
      {market.global_trends && market.global_trends.length > 0 && (
        <Row gutter={[16, 16]}>
          <Col xs={24}>
            <Card size="small" title={<><GlobalOutlined style={{ color: 'var(--saas-primary)' }} /> 全球市场走势</>}>
              <GlobalTrendsMiniChart trends={market.global_trends} />
            </Card>
          </Col>
        </Row>
      )}
      {market.keyword_relationships && market.keyword_relationships.expansion_suggestions.length > 0 && (
        <Row gutter={[16, 16]}>
          <Col xs={24}>
            <Card size="small" title={<><ApartmentOutlined style={{ color: 'var(--saas-primary)' }} /> 关键词关系与拓品建议</>}>
              <KeywordRelationSuggestions rel={market.keyword_relationships} />
            </Card>
          </Col>
        </Row>
      )}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card size="small" title="TOP5 竞品">
            <Table rowKey="rank" columns={cols} dataSource={data} pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card size="small" title="月销量对比">
            <ReactECharts option={barOption} style={{ height: 260 }} />
          </Card>
        </Col>
      </Row>
    </Space>
  )
}

function ReportProfitTab({ profit, currencySymbol }: { profit: AnalysisReport['profit_analysis']; currencySymbol: string }) {
  const costRows = Object.entries(profit.cost_breakdown).map(([name, value]) => ({
    name,
    value,
    pct: profit.cost_breakdown_pct[name] || '0.0%',
  }))
  const donutOption = useMemo(() => buildCostDonutOption(profit, currencySymbol), [profit, currencySymbol])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8}>
          <MiniMetric label="售价" value={`${currencySymbol}${profit.selling_price.toFixed(2)}`} />
        </Col>
        <Col xs={12} sm={8}>
          <MiniMetric label="单件成本" value={`${currencySymbol}${profit.total_cost_per_unit.toFixed(2)}`} />
        </Col>
        <Col xs={12} sm={8}>
          <MiniMetric label="毛利率" value={profit.gross_margin_pct} highlight />
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card size="small" title="单件成本结构">
            <Table
              rowKey="name"
              columns={[
                { title: '成本项', dataIndex: 'name' },
                { title: '金额', dataIndex: 'value', render: (v: number) => `${currencySymbol}${v.toFixed(2)}`, align: 'right' as const },
                { title: '占比', dataIndex: 'pct', align: 'right' as const },
              ]}
              dataSource={costRows}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title="成本构成可视化">
            <ReactECharts option={donutOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>
      <Card size="small" title="ROI 情景测算">
        <Row gutter={[16, 16]}>
          {Object.entries(profit.roi_scenarios).map(([name, s]: [string, any]) => (
            <Col xs={24} sm={8} key={name}>
              <div style={{ textAlign: 'center', padding: 16, background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: 12, color: '#64748b', fontWeight: 800, marginBottom: 8 }}>{name}</div>
                <div style={{ fontSize: 20, fontWeight: 900, color: '#1e40af' }}>ROI {s['ROI']}%</div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>月毛利 {currencySymbol}{s['月毛利'].toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
              </div>
            </Col>
          ))}
        </Row>
      </Card>
    </Space>
  )
}

function ReportReviewTab({ report }: { report: AnalysisReport }) {
  const review = report.review_insights
  const tagColors = ['#2563eb', '#0891b2', '#059669', '#d97706', '#7c3aed', '#dc2626']
  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <MiniMetric label="痛点" value={`${review.pain_points.length} 项`} color="#dc2626" />
        </Col>
        <Col xs={24} sm={8}>
          <MiniMetric label="好评" value={`${review.praised_features.length} 项`} color="#16a34a" />
        </Col>
        <Col xs={24} sm={8}>
          <MiniMetric label="机会" value={`${review.opportunities.length} 项`} color="#2563eb" />
        </Col>
      </Row>
      <Card size="small" title={<><CloseCircleOutlined style={{ color: '#dc2626' }} /> 用户痛点</>}>
        <ul style={{ margin: 0, paddingLeft: 18, color: '#475569', lineHeight: 1.9 }}>
          {review.pain_points.map((p, i) => <li key={i}>{p}</li>)}
        </ul>
      </Card>
      <Card size="small" title={<><CheckCircleOutlined style={{ color: '#16a34a' }} /> 用户好评</>}>
        <ul style={{ margin: 0, paddingLeft: 18, color: '#475569', lineHeight: 1.9 }}>
          {review.praised_features.map((p, i) => <li key={i}>{p}</li>)}
        </ul>
      </Card>
      <Card size="small" title={<><BulbOutlined style={{ color: '#d97706' }} /> 差异化机会</>}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {review.opportunities.map((opp, i) => {
            const tag = extractOpportunityTag(opp)
            const color = tagColors[i % tagColors.length]
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: 14, background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                <div style={{ width: 28, height: 28, borderRadius: '50%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: `${color}15`, color, fontSize: 13, fontWeight: 900, flexShrink: 0 }}>{i + 1}</div>
                <div style={{ flex: 1 }}>
                  <Tag color={color} style={{ fontWeight: 800, marginBottom: 6 }}>{tag}</Tag>
                  <div style={{ color: '#475569', fontSize: 13, lineHeight: 1.7 }}>{opp}</div>
                </div>
              </div>
            )
          })}
        </div>
      </Card>
    </Space>
  )
}

function ReportTrendComplianceTab({ report }: { report: AnalysisReport }) {
  const trend = report.trend_analysis
  const compliance = report.compliance
  const market = report.market_analysis
  const trendOption = useMemo(() => buildTrendLineOption(trend), [trend])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card size="small" title={<><CalendarOutlined /> 季节趋势</>}>
            <ReactECharts option={trendOption} style={{ height: 240 }} />
            <div style={{ marginTop: 12, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <Text strong>旺季高峰：</Text>
                <Tag color="#dc2626">{trend.peak_months.join('、')} 月</Tag>
              </div>
              <div>
                <Text strong>备货窗口：</Text>
                <Tag color="#16a34a">{trend.entry_windows.join('、')} 月</Tag>
              </div>
            </div>
            <div style={{ color: '#475569', lineHeight: 1.8, marginTop: 12 }}>
              <p style={{ margin: '0 0 8px' }}><strong>季节洞察：</strong>{trend.season_narrative.season_desc}</p>
              <p style={{ margin: 0 }}><strong>趋势判断：</strong>{trend.season_narrative.trend_desc}</p>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title={<><SafetyOutlined /> 合规风险</>}>
            <div style={{ marginBottom: 12 }}>
              <Text strong>风险等级：</Text>
              <Tag color={compliance.risk_level === '高' ? '#dc2626' : compliance.risk_level === '中' ? '#d97706' : '#16a34a'}>{compliance.risk_level}</Tag>
            </div>
            <div style={{ marginBottom: 12 }}>
              <Text strong>认证预算：</Text>
              <Text>{market.market_profile.currency}{compliance.estimated_cert_cost} · {compliance.estimated_cert_time}</Text>
            </div>
            <div style={{ color: '#475569', lineHeight: 1.8 }}>
              <p style={{ margin: '0 0 8px' }}><strong>关键认证：</strong>{compliance.certifications.slice(0, 4).join('、')}</p>
              <p style={{ margin: 0 }}><strong>核心风险：</strong>{compliance.category_risks[0]}</p>
            </div>
          </Card>
        </Col>
      </Row>
    </Space>
  )
}

function ReportActionTab({ report }: { report: AnalysisReport }) {
  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {report.next_steps.map((step, i) => (
        <Card size="small" key={i}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, #2563eb 0%, #60a5fa 100%)',
                color: '#fff',
                fontWeight: 900,
                flexShrink: 0,
              }}
            >
              {i + 1}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
                <Text strong style={{ fontSize: 15 }}>{step.title}</Text>
                <Tag color="blue">{step.phase}</Tag>
                <Tag color="default">{step.owner}</Tag>
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, color: '#475569', lineHeight: 1.8, fontSize: 13 }}>
                {step.tasks.map((t, j) => <li key={j}>{t}</li>)}
              </ul>
              <div style={{ marginTop: 8, padding: '8px 12px', background: '#f0fdf4', borderRadius: 6, color: '#166534', fontSize: 13, fontWeight: 600 }}>
                <CarryOutOutlined style={{ marginRight: 6 }} />
                {step.value}
              </div>
            </div>
          </div>
        </Card>
      ))}
    </Space>
  )
}

function MetricCard({ label, value, icon, color }: { label: string; value: string; icon: React.ReactNode; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 16, background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 10 }}>
      <div style={{ width: 42, height: 42, borderRadius: 10, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: `${color}15`, color, fontSize: 18 }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 12, color: '#64748b', fontWeight: 800, marginBottom: 2 }}>{label}</div>
        <div style={{ fontSize: 18, fontWeight: 900, color: '#1e293b' }}>{value}</div>
      </div>
    </div>
  )
}

function MiniMetric({ label, value, color, highlight }: { label: string; value: string | number; color?: string; highlight?: boolean }) {
  return (
    <div style={{ textAlign: 'center', padding: 14, background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
      <div style={{ fontSize: 11, color: '#64748b', fontWeight: 800, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 900, color: highlight ? '#16a34a' : color || '#1e293b' }}>{value}</div>
    </div>
  )
}

function getPrintStyles(report: AnalysisReport) {
  return `
    @page { size: A4; margin: 16mm; }
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #1e293b; line-height: 1.55; margin: 0; padding: 0; font-size: 11px; }
    .p-header { text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 14px; margin-bottom: 18px; page-break-inside: avoid; break-inside: avoid; }
    .p-header h1 { margin: 0 0 6px; font-size: 22px; color: #1e293b; }
    .p-header .p-meta { color: #64748b; font-size: 11px; }
    .p-section { margin-bottom: 18px; color: #1e293b; }
    .p-title { font-size: 14px; font-weight: 900; color: #1e293b; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; page-break-after: avoid; break-after: avoid; page-break-inside: avoid; break-inside: avoid; }
    .p-subtitle { font-size: 12px; font-weight: 800; color: #334155; margin: 12px 0 8px; page-break-after: avoid; break-after: avoid; }
    .p-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
    .p-metric { flex: 1 1 110px; min-width: 110px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 8px 12px; text-align: center; page-break-inside: avoid; break-inside: avoid; }
    .p-metric-label { font-size: 10px; color: #64748b; font-weight: 800; margin-bottom: 4px; }
    .p-metric-value { font-size: 16px; font-weight: 900; color: #2563eb; }
    .p-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; table-layout: auto; }
    .p-table th, .p-table td { border: 1px solid #e2e8f0; padding: 6px 8px; text-align: left; font-size: 10px; vertical-align: top; }
    .p-table th { background: #f1f5f9; font-weight: 800; }
    .p-table tr { page-break-inside: avoid; break-inside: avoid; }
    .p-table thead { display: table-header-group; }
    .p-trend-table th, .p-trend-table td { text-align: center; padding: 5px 3px; font-size: 9px; white-space: nowrap; }
    .p-list { margin: 0; padding-left: 16px; }
    .p-list li { margin-bottom: 4px; padding-bottom: 2px; page-break-inside: avoid; break-inside: avoid; }
    .p-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; margin-right: 4px; margin-bottom: 4px; background: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe; }
    .p-tag-risk { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
    .p-tag-cert { background: #f0fdf4; color: #166534; border-color: #bbf7d0; }
    .p-action { page-break-inside: avoid; break-inside: avoid; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 10px 12px; margin-bottom: 8px; }
    .p-action-title { font-weight: 900; margin-bottom: 3px; font-size: 12px; }
    .p-verdict { color: ${report.verdict_color}; font-weight: 900; }
    .p-grade { display: inline-block; padding: 3px 10px; border-radius: 12px; background: ${report.verdict_color}; color: #fff; font-weight: 900; font-size: 13px; }
    .p-score-row { display: flex; align-items: center; margin-bottom: 8px; page-break-inside: avoid; break-inside: avoid; }
    .p-score-name { width: 84px; font-weight: 800; font-size: 10px; }
    .p-score-bar { flex: 1; height: 9px; background: #e2e8f0; border-radius: 5px; overflow: hidden; }
    .p-score-fill { height: 100%; border-radius: 5px; }
    .p-score-value { width: 60px; text-align: right; font-weight: 900; font-size: 10px; }
    .p-suggestion { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; page-break-inside: avoid; break-inside: avoid; }
    .p-suggestion-title { font-weight: 900; margin-bottom: 4px; font-size: 12px; display: flex; align-items: center; gap: 8px; }
    .p-suggestion-desc { color: #475569; font-size: 10px; line-height: 1.5; margin-bottom: 6px; }
    .p-footer { margin-top: 24px; padding-top: 10px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 9px; text-align: center; }
  `
}

function ReportPdfContent({ report }: { report: AnalysisReport }) {
  return (
    <div style={{ width: '794px', padding: '16mm', backgroundColor: '#ffffff', boxSizing: 'border-box' }}>
      <style dangerouslySetInnerHTML={{ __html: getPrintStyles(report) }} />
      <ReportPrintContent report={report} />
      <div className="p-footer">本报告由跨境电商智能选品决策系统生成 · 仅供参考</div>
    </div>
  )
}

async function downloadReportPdf(report: AnalysisReport, setLoading?: (loading: boolean) => void) {
  setLoading?.(true)
  // 先让 UI 线程渲染加载态，再执行 PDF 生成，降低“卡住”感知
  const hideLoading = message.loading('正在生成 PDF，请稍候...', 0)
  await new Promise((resolve) => setTimeout(resolve, 80))

  const container = document.createElement('div')
  container.style.position = 'absolute'
  container.style.left = '-9999px'
  container.style.top = '0'
  container.style.width = '794px'
  container.style.zIndex = '-1'
  document.body.appendChild(container)

  const root = createRoot(container)
  root.render(<ReportPdfContent report={report} />)

  await new Promise((resolve) => setTimeout(resolve, 120))

  try {
    // scale 降至 1.5 可显著减少渲染耗时，同时保持打印清晰度
    const canvas = await html2canvas(container, {
      scale: 1.5,
      backgroundColor: '#ffffff',
      useCORS: true,
      logging: false,
    })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF('p', 'mm', 'a4')
    const pdfWidth = 210
    const pdfHeight = 297
    const imgWidth = pdfWidth
    const imgHeight = (canvas.height * pdfWidth) / canvas.width
    const pxToMm = pdfWidth / canvas.width
    const pageHeightPx = pdfHeight / pxToMm

    // 智能分页：收集所有可见块级元素的下边界作为候选切分点，
    // 每次在目标页高附近选择最合适的边界，避免行内截断或分页处内容重复。
    const protectedSelectors = [
      '.p-header', '.p-footer', '.p-section', '.p-section > *',
      '.p-title', '.p-grid', '.p-metric', '.p-action',
      '.p-table', '.p-table tr', '.p-list', 'li', 'p', 'h1', 'h2', 'h3',
    ]
    const candidateBreaks = new Set<number>()
    candidateBreaks.add(0)
    protectedSelectors.forEach((sel) => {
      container.querySelectorAll(sel).forEach((el) => {
        const htmlEl = el as HTMLElement
        if (!htmlEl.offsetParent) return
        const rect = htmlEl.getBoundingClientRect()
        const bottom = Math.round(rect.top + rect.height + container.scrollTop)
        if (bottom > 0) candidateBreaks.add(bottom)
      })
    })
    const sortedBreaks = Array.from(candidateBreaks)
      .filter((b) => b > 0 && b < container.scrollHeight)
      .sort((a, b) => a - b)

    const minPageHeight = pageHeightPx * 0.45
    const safetyMargin = 14
    const pageTops: number[] = [0]
    let currentTop = 0
    const minAdvance = 20

    while (currentTop + pageHeightPx < container.scrollHeight) {
      const targetBottom = currentTop + pageHeightPx
      // 优先找不超过目标底部的最大候选边界
      let bestBreak = sortedBreaks.reduce((best, b) => {
        if (b > currentTop + safetyMargin && b <= targetBottom - safetyMargin) {
          return b
        }
        return best
      }, -1)

      // 若候选边界导致页面过短，则 fallback 到目标底部硬切
      if (bestBreak < 0 || bestBreak - currentTop < minPageHeight) {
        bestBreak = targetBottom
      }

      // 确保分页点确实向前推进，防止死循环或内容重复
      if (bestBreak <= currentTop + minAdvance) {
        bestBreak = Math.min(currentTop + pageHeightPx, container.scrollHeight)
      }

      pageTops.push(bestBreak)
      currentTop = bestBreak
    }

    // 去重并排序，防止重复渲染同一区域
    const uniqueTops = Array.from(new Set(pageTops)).sort((a, b) => a - b)

    uniqueTops.forEach((top, index) => {
      if (index > 0) pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, -top * pxToMm, imgWidth, imgHeight)
    })

    pdf.save(`${report.keyword.replace(/\s+/g, '_').toLowerCase()}_${report.market.toLowerCase()}_report.pdf`)
    hideLoading()
    message.success('PDF 导出成功')
  } catch (error) {
    hideLoading()
    message.error('PDF 导出失败，请重试')
    console.error('PDF export error:', error)
  } finally {
    root.unmount()
    document.body.removeChild(container)
    setLoading?.(false)
  }
}

function ReportPrintContent({ report }: { report: AnalysisReport }) {
  const market = report.market_analysis
  const profit = report.profit_analysis
  const trend = report.trend_analysis
  const review = report.review_insights
  const compliance = report.compliance
  const suppliers = report.suppliers || []
  const { symbol } = getMarketCurrency(report.market)
  const trendText = trend.trend_direction === 'rising' ? '上升' : trend.trend_direction === 'stable' ? '稳定' : '下滑'
  const summary = market.keyword_summary
  const rel = market.keyword_relationships

  const allRisks = [
    ...(compliance.category_risks || []),
    ...(compliance.design_patent_risks || []),
    ...(compliance.brand_risks || []),
    ...(compliance.industry_patent_risks || []),
    ...(compliance.market_specific || []),
  ]

  return (
    <div>
      <div className="p-header">
        <h1>{report.keyword}</h1>
        <div className="p-meta">
          {market.market_profile.name} · 预算 {report.budget} · 生成时间 {new Date().toLocaleString('zh-CN')}
        </div>
      </div>

      <div className="p-section">
        <div className="p-title">一、报告概览</div>
        <div className="p-grid">
          <div className="p-metric"><div className="p-metric-label">综合评分</div><div className="p-metric-value">{report.overall_score}/{report.max_score}</div></div>
          <div className="p-metric"><div className="p-metric-label">等级</div><div className="p-metric-value"><span className="p-grade">{report.grade}</span></div></div>
          <div className="p-metric"><div className="p-metric-label">毛利率</div><div className="p-metric-value" style={{ color: profit.gross_margin >= 0.2 ? '#16a34a' : profit.gross_margin >= 0.1 ? '#d97706' : '#dc2626' }}>{profit.gross_margin_pct}</div></div>
          <div className="p-metric"><div className="p-metric-label">趋势</div><div className="p-metric-value">{trendText}</div></div>
          <div className="p-metric"><div className="p-metric-label">市场均价</div><div className="p-metric-value">{market.market_profile.currency}{market.avg_price}</div></div>
          <div className="p-metric"><div className="p-metric-label">单件毛利</div><div className="p-metric-value">{symbol}{profit.gross_profit_per_unit.toFixed(2)}</div></div>
          <div className="p-metric"><div className="p-metric-label">盈亏平衡</div><div className="p-metric-value">{profit.breakeven_units ?? '-'} 件</div></div>
          <div className="p-metric"><div className="p-metric-label">旺季月份</div><div className="p-metric-value">{trend.peak_months.slice(0, 3).join('、')} 月</div></div>
        </div>
        <p>关键词 <strong>{report.keyword}</strong> 在 <strong>{market.market_profile.name}</strong> 市场平均售价 <strong>{market.market_profile.currency}{market.avg_price}</strong>，毛利率 <strong className="p-verdict">{profit.gross_margin_pct}</strong>，趋势 <strong>{trendText}</strong>。综合判定为 <strong className="p-verdict">{report.verdict}</strong>。</p>
        <div className="p-subtitle">关键建议</div>
        <ul className="p-list">
          {report.next_steps.slice(0, 3).map((step, i) => (
            <li key={i}><strong>{step.phase}</strong>：{step.title} — {step.value}</li>
          ))}
        </ul>
        <div className="p-subtitle">五维评分拆解</div>
        {Object.entries(report.score_breakdown).map(([name, score]) => {
          const maxV = { 利润空间: 40, 趋势热度: 25, 竞争强度: 20, 评论洞察: 15, 供应链稳定性: 15 }[name] ?? 25
          const pct = Math.min(100, Math.max(0, (score / maxV) * 100))
          const colors: Record<string, string> = { 利润空间: '#059669', 趋势热度: '#7c3aed', 竞争强度: '#0891b2', 评论洞察: '#2563eb', 供应链稳定性: '#d97706' }
          return (
            <div key={name} className="p-score-row">
              <div className="p-score-name" style={{ color: colors[name] }}>{name}</div>
              <div className="p-score-bar"><div className="p-score-fill" style={{ width: `${pct}%`, background: colors[name] }} /></div>
              <div className="p-score-value" style={{ color: colors[name] }}>{score}/{maxV}</div>
            </div>
          )
        })}
      </div>

      <div className="p-section">
        <div className="p-title">二、市场分析</div>
        <div className="p-grid">
          <div className="p-metric"><div className="p-metric-label">竞品数量</div><div className="p-metric-value">{market.competitors.length} 款</div></div>
          <div className="p-metric"><div className="p-metric-label">市场均价</div><div className="p-metric-value">{market.market_profile.currency}{market.avg_price}</div></div>
          <div className="p-metric"><div className="p-metric-label">平均评分</div><div className="p-metric-value">{market.avg_rating}</div></div>
          <div className="p-metric"><div className="p-metric-label">平均评论</div><div className="p-metric-value">{market.avg_reviews.toLocaleString()}</div></div>
        </div>

        {summary && (
          <>
            <div className="p-subtitle">关键词画像</div>
            <div className="p-grid">
              <div className="p-metric"><div className="p-metric-label">搜索量</div><div className="p-metric-value">{summary.search_volume.toLocaleString()}</div></div>
              <div className="p-metric"><div className="p-metric-label">竞争度</div><div className="p-metric-value">{summary.competition}</div></div>
              <div className="p-metric"><div className="p-metric-label">CPC</div><div className="p-metric-value">{market.market_profile.currency}{summary.cpc.toFixed(2)}</div></div>
              <div className="p-metric"><div className="p-metric-label">机会分</div><div className="p-metric-value">{summary.opportunity_score}</div></div>
            </div>
          </>
        )}

        {market.global_trends && market.global_trends.length > 0 && (
          <>
            <div className="p-subtitle">全球市场月度热度</div>
            <table className="p-table">
              <thead>
                <tr><th>月份</th>{market.global_trends.map((t) => <th key={t.code}>{t.name}</th>)}</tr>
              </thead>
              <tbody>
                {(market.global_trends[0].months || []).map((m, i) => (
                  <tr key={i}>
                    <td>{m}</td>
                    {market.global_trends!.map((t) => <td key={t.code}>{t.values[i] ?? '-'}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {rel && rel.expansion_suggestions.length > 0 && (
          <>
            <div className="p-subtitle">关键词关系与拓品建议</div>
            {rel.expansion_suggestions.map((s, i) => (
              <div key={i} className="p-suggestion">
                <div className="p-suggestion-title">
                  <span>{s.segment}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: s.avg_score >= 60 ? '#dc2626' : '#d97706' }}>平均机会分 {s.avg_score}</span>
                </div>
                <div className="p-suggestion-desc">{s.rationale}</div>
                <div>{s.keywords.map((kw, j) => <span key={j} className="p-tag">{kw}</span>)}</div>
              </div>
            ))}
          </>
        )}

        {market.keyword_opportunities && market.keyword_opportunities.length > 0 && (
          <>
            <div className="p-subtitle">细分关键词机会 TOP10</div>
            <table className="p-table">
              <thead>
                <tr><th>排名</th><th>关键词</th><th>搜索量</th><th>趋势</th><th>竞争</th><th>机会分</th><th>CPC</th></tr>
              </thead>
              <tbody>
                {market.keyword_opportunities.slice(0, 10).map((o, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>{o.keyword}</td>
                    <td>{o.search_volume.toLocaleString()}</td>
                    <td>{o.trend === 'rising' ? '上升' : o.trend === 'stable' ? '稳定' : '下滑'}</td>
                    <td>{o.competition === 'low' ? '低' : o.competition === 'medium' ? '中' : '高'}</td>
                    <td>{o.opportunity_score}</td>
                    <td>{market.market_profile.currency}{o.cpc.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {report.trending_products && report.trending_products.length > 0 && (
          <>
            <div className="p-subtitle">趋势产品</div>
            <div className="p-grid">
              {report.trending_products.map((tp, i) => (
                <div key={i} className="p-metric" style={{ flex: '1 1 140px' }}>
                  <div className="p-metric-label" style={{ fontSize: 9, lineHeight: 1.4 }}>{tp.keyword}</div>
                  <div className="p-metric-value" style={{ fontSize: 13 }}>+{tp.growth_pct}%</div>
                  <div style={{ fontSize: 9, color: '#64748b', marginTop: 2 }}>竞争 {tp.competition} · 机会 {tp.opportunity}</div>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="p-subtitle">TOP10 竞品</div>
        <table className="p-table">
          <thead><tr><th>排名</th><th>产品</th><th>品牌</th><th>价格</th><th>评分</th><th>评论数</th><th>月销量</th></tr></thead>
          <tbody>
            {market.competitors.slice(0, 10).map((c: any, i: number) => (
              <tr key={i}><td>{i + 1}</td><td>{c.title}</td><td>{c.brand}</td><td>{market.market_profile.currency}{c.price}</td><td>{c.rating}</td><td>{c.review_count.toLocaleString()}</td><td>{c.estimated_monthly_sales.toLocaleString()}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-section">
        <div className="p-title">三、趋势与合规</div>
        <div className="p-grid">
          <div className="p-metric"><div className="p-metric-label">旺季高峰</div><div className="p-metric-value">{trend.peak_months.join('、')} 月</div></div>
          <div className="p-metric"><div className="p-metric-label">备货窗口</div><div className="p-metric-value">{trend.entry_windows.join('、')} 月</div></div>
          <div className="p-metric"><div className="p-metric-label">趋势方向</div><div className="p-metric-value">{trendText}</div></div>
          <div className="p-metric"><div className="p-metric-label">风险等级</div><div className="p-metric-value">{compliance.risk_level}</div></div>
        </div>
        <p><strong>季节洞察：</strong>{trend.season_narrative.season_desc}</p>
        <p><strong>趋势判断：</strong>{trend.season_narrative.trend_desc}</p>
        <div className="p-subtitle">月度热度走势</div>
        <table className="p-table p-trend-table">
          <thead>
            <tr>
              <th>月份</th>
              {trend.series.months.map((m, i) => <th key={i}>{m}</th>)}
              {trend.series.forecast_months.map((m, i) => <th key={`f-${i}`}>{m}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>热度</td>
              {trend.series.values.map((v, i) => <td key={i}>{v}</td>)}
              {trend.series.forecast_values.map((v, i) => <td key={`fv-${i}`} style={{ color: '#7c3aed', fontWeight: 800 }}>{v}</td>)}
            </tr>
            <tr>
              <td>去年同期</td>
              {trend.series.last_year_values.map((v, i) => <td key={i}>{v}</td>)}
              <td colSpan={trend.series.forecast_months.length} style={{ color: '#94a3b8' }}>—</td>
            </tr>
          </tbody>
        </table>
        <p><strong>认证预算：</strong>{market.market_profile.currency}{compliance.estimated_cert_cost} · {compliance.estimated_cert_time}</p>
        <div className="p-subtitle">关键认证</div>
        <div>{compliance.certifications.map((c, i) => <span key={i} className="p-tag p-tag-cert">{c}</span>)}</div>
        <div className="p-subtitle">合规与专利风险</div>
        <ul className="p-list">{allRisks.map((r, i) => <li key={i}>{r}</li>)}</ul>
      </div>

      <div className="p-section">
        <div className="p-title">四、利润测算</div>
        <div className="p-grid">
          <div className="p-metric"><div className="p-metric-label">售价</div><div className="p-metric-value">{symbol}{profit.selling_price.toFixed(2)}</div></div>
          <div className="p-metric"><div className="p-metric-label">单件总成本</div><div className="p-metric-value">{symbol}{profit.total_cost_per_unit.toFixed(2)}</div></div>
          <div className="p-metric"><div className="p-metric-label">单件毛利</div><div className="p-metric-value">{symbol}{profit.gross_profit_per_unit.toFixed(2)}</div></div>
          <div className="p-metric"><div className="p-metric-label">盈亏平衡</div><div className="p-metric-value">{profit.breakeven_units ?? '-'} 件</div></div>
        </div>
        <table className="p-table">
          <thead><tr><th>成本项</th><th>金额</th><th>占比</th></tr></thead>
          <tbody>
            {Object.entries(profit.cost_breakdown).map(([name, value]) => (
              <tr key={name}><td>{name}</td><td>{symbol}{(value as number).toFixed(2)}</td><td>{profit.cost_breakdown_pct[name] || '0%'}</td></tr>
            ))}
          </tbody>
        </table>
        <table className="p-table">
          <thead><tr><th>情景</th><th>月销量</th><th>毛利率</th><th>ROI</th><th>月毛利</th><th>回本周期</th></tr></thead>
          <tbody>
            {Object.entries(profit.roi_scenarios).map(([name, data]: [string, any]) => (
              <tr key={name}>
                <td>{name}</td>
                <td>{data['月销量']}</td>
                <td>{data['毛利率']}</td>
                <td>{data['ROI'].toFixed(2)}%</td>
                <td>{symbol}{data['月毛利'].toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                <td>{data['回本周期']} 月</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-section">
        <div className="p-title">五、评论洞察</div>
        <div className="p-grid">
          <div className="p-metric"><div className="p-metric-label">痛点</div><div className="p-metric-value">{review.pain_points.length} 项</div></div>
          <div className="p-metric"><div className="p-metric-label">好评</div><div className="p-metric-value">{review.praised_features.length} 项</div></div>
          <div className="p-metric"><div className="p-metric-label">机会</div><div className="p-metric-value">{review.opportunities.length} 项</div></div>
        </div>
        <div className="p-subtitle">用户痛点</div>
        <ul className="p-list">{review.pain_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
        <div className="p-subtitle">用户好评</div>
        <ul className="p-list">{review.praised_features.map((p, i) => <li key={i}>{p}</li>)}</ul>
        <div className="p-subtitle">差异化机会</div>
        {review.opportunities.map((opp, i) => {
          const tag = extractOpportunityTag(opp)
          const colors = ['#2563eb', '#0891b2', '#059669', '#d97706', '#7c3aed', '#dc2626']
          const color = colors[i % colors.length]
          return (
            <div key={i} className="p-suggestion">
              <div className="p-suggestion-title">
                <span style={{ display: 'inline-block', width: 20, height: 20, borderRadius: '50%', background: `${color}15`, color, fontSize: 11, fontWeight: 900, textAlign: 'center', lineHeight: '20px' }}>{i + 1}</span>
                <span className="p-tag" style={{ background: `${color}15`, color, borderColor: `${color}30` }}>{tag}</span>
              </div>
              <div className="p-suggestion-desc">{opp}</div>
            </div>
          )
        })}
      </div>

      {suppliers.length > 0 && (
        <div className="p-section">
          <div className="p-title">六、供应商推荐</div>
          <table className="p-table">
            <thead>
              <tr>
                <th>排名</th><th>供应商</th><th>MOQ</th><th>交期</th><th>评分</th><th>产能</th><th>单件成本</th><th>样品费</th><th>样品交期</th><th>响应率</th><th>成交数</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.slice(0, 5).map((s: any, i: number) => (
                <tr key={i}>
                  <td>{s.rank || i + 1}</td>
                  <td>{s.name}</td>
                  <td>{s.moq}</td>
                  <td>{s.lead_time}</td>
                  <td>{s.rating}</td>
                  <td>{s.capacity}</td>
                  <td>{symbol}{s.unit_cost?.toFixed(2) ?? '-'}</td>
                  <td>{symbol}{s.sample_cost}</td>
                  <td>{s.sample_days ?? '-'} 天</td>
                  <td>{s.response_rate}%</td>
                  <td>{s.transactions ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="p-subtitle">主营爆款</div>
          <div className="p-grid">
            {suppliers.slice(0, 3).map((s: any, i: number) => (
              <div key={i} className="p-metric" style={{ flex: '1 1 160px' }}>
                <div className="p-metric-label" style={{ fontSize: 9, lineHeight: 1.4 }}>{s.name}</div>
                <div className="p-metric-value" style={{ fontSize: 12 }}>{(s.hot_categories || []).join('、')}</div>
                <div style={{ fontSize: 9, color: '#64748b', marginTop: 2 }}>从业 {s.years ?? '-'} 年 · 产能 {s.capacity}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="p-section">
        <div className="p-title">{suppliers.length > 0 ? '七' : '六'}、行动计划</div>
        {report.next_steps.map((step, i) => (
          <div key={i} className="p-action">
            <div className="p-action-title">{step.phase} · {step.title}</div>
            <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}><strong>负责人：</strong>{step.owner}</div>
            <ul className="p-list">
              {step.tasks.map((t, j) => <li key={j}>{t}</li>)}
            </ul>
            <div style={{ marginTop: 6, padding: '6px 8px', background: '#f0fdf4', borderRadius: 6, color: '#166534', fontSize: 10, fontWeight: 700 }}>
              目标：{step.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const RADAR_MAX_VALUES: Record<string, number> = {
  利润空间: 40,
  趋势热度: 25,
  竞争强度: 20,
  评论洞察: 15,
  供应链稳定性: 15,
}

const RADAR_COLORS: Record<string, { start: string; end: string }> = {
  利润空间: { start: '#059669', end: '#34d399' },
  趋势热度: { start: '#7c3aed', end: '#a78bfa' },
  竞争强度: { start: '#0891b2', end: '#22d3ee' },
  评论洞察: { start: '#2563eb', end: '#60a5fa' },
  供应链稳定性: { start: '#d97706', end: '#fbbf24' },
}

function buildReportRadarOption(report: AnalysisReport): EChartsOption {
  const categories = Object.keys(report.score_breakdown)
  const values = Object.values(report.score_breakdown)
  const normalized = categories.map((cat, i) => Math.min(100, (values[i] / RADAR_MAX_VALUES[cat]) * 100))
  const avg = normalized.reduce((a, b) => a + b, 0) / normalized.length

  return {
    color: ['#2563eb'],
    tooltip: {
      trigger: 'item',
      ...DARK_TOOLTIP,
      formatter: (params: any) => {
        const list = params.value.map((v: number, i: number) => {
          const raw = values[i]
          const max = RADAR_MAX_VALUES[categories[i]]
          const color = RADAR_COLORS[categories[i]].start
          return `<div style="display:flex;align-items:center;gap:8px;margin:4px 0">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color}"></span>
            <span style="font-weight:700">${categories[i]}</span>
            <span style="color:rgba(255,255,255,0.75);font-size:12px;margin-left:auto">${raw}/${max} · ${v.toFixed(1)}%</span>
          </div>`
        }).join('')
        return `<div style="font-weight:800;margin-bottom:6px">综合评分 ${avg.toFixed(1)}</div>${list}`
      },
    },
    radar: {
      indicator: categories.map((cat) => ({ name: cat, max: 100, color: RADAR_COLORS[cat].start })),
      radius: '62%',
      center: ['50%', '50%'],
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        fontSize: 12,
        fontWeight: 800,
        fontFamily: 'var(--font-sans)',
      },
      axisLine: { lineStyle: { color: '#e2e8f0', width: 1.5 } },
      splitLine: { lineStyle: { color: '#e2e8f0', width: 1 } },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(255, 255, 255, 0.9)', 'rgba(241, 245, 249, 0.5)', 'rgba(255, 255, 255, 0.85)', 'rgba(241, 245, 249, 0.4)', 'rgba(255, 255, 255, 0.7)'],
        },
      },
    },
    series: [{
      type: 'radar',
      data: [{
        value: normalized,
        name: '五维评分',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.42)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.1)' },
          ]),
        },
        lineStyle: { color: '#2563eb', width: 2.5, shadowBlur: 10, shadowColor: 'rgba(37,99,235,0.2)' },
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: { color: '#2563eb', borderColor: '#fff', borderWidth: 2, shadowBlur: 8, shadowColor: 'rgba(37,99,235,0.3)' },
        label: { show: true, formatter: (params: any) => String(Math.round(params.value)), color: '#1e40af', fontSize: 11, fontWeight: 900 },
      }],
      animationDuration: 1000,
      animationEasing: 'cubicOut',
    }],
    graphic: [{
      type: 'group',
      left: 'center',
      top: '50%',
      z: 100,
      children: [
        {
          type: 'circle',
          shape: { cx: 0, cy: 0, r: 32 },
          style: { fill: 'rgba(255,255,255,0.95)', stroke: 'rgba(37,99,235,0.12)', lineWidth: 1 },
        },
        {
          type: 'text',
          left: 'center',
          top: 'center',
          style: { text: `${Math.round(avg)}`, fontSize: 22, fontWeight: 900, fill: '#1e40af', fontFamily: 'var(--font-sans)', y: -6 },
        },
        {
          type: 'text',
          left: 'center',
          top: 'center',
          style: { text: '综合均分', fontSize: 10, fontWeight: 800, fill: '#64748b', fontFamily: 'var(--font-sans)', y: 12 },
        },
      ],
    }],
  }
}

function buildCostDonutOption(profit: AnalysisReport['profit_analysis'], currencySymbol = '$'): EChartsOption {
  const data = Object.entries(profit.cost_breakdown)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value: Math.round(value * 100) / 100 }))
    .sort((a, b) => b.value - a.value)
  const palette = ['#2563eb', '#0891b2', '#d97706', '#7c3aed', '#059669', '#dc2626', '#94a3b8']

  return {
    color: palette,
    tooltip: {
      trigger: 'item',
      ...DARK_TOOLTIP,
      formatter: (params: any) => `<div style="font-weight:800">${params.name}</div><div style="color:rgba(255,255,255,0.75);font-size:12px">${currencySymbol}${params.value.toFixed(2)} · ${params.percent}%</div>`,
    },
    legend: { bottom: 0, icon: 'circle', itemWidth: 10, itemHeight: 10, textStyle: { color: '#64748b', fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%', color: '#475569', fontSize: 11, fontWeight: 700 },
      labelLine: { length: 10, length2: 8 },
      data,
      animationDuration: 800,
      animationEasing: 'cubicOut',
    }],
    graphic: [{
      type: 'group',
      left: 'center',
      top: '45%',
      z: 100,
      children: [
        {
          type: 'text',
          left: 'center',
          top: 'center',
          style: { text: `${currencySymbol}${profit.total_cost_per_unit.toFixed(2)}`, fontSize: 18, fontWeight: 900, fill: '#1e293b', fontFamily: 'var(--font-sans)', y: -4 },
        },
        {
          type: 'text',
          left: 'center',
          top: 'center',
          style: { text: '单件成本', fontSize: 10, fontWeight: 800, fill: '#64748b', fontFamily: 'var(--font-sans)', y: 12 },
        },
      ],
    }],
  }
}

function buildTrendLineOption(trend: AnalysisReport['trend_analysis']): EChartsOption {
  const months = trend.series.months
  const values = trend.series.values
  const max = Math.max(...values)
  const min = Math.min(...values)

  return {
    color: ['#2563eb'],
    tooltip: {
      trigger: 'axis',
      ...DARK_TOOLTIP,
      formatter: (params: any) => `<div style="font-weight:800;margin-bottom:4px">${params[0].name}</div><div style="color:rgba(255,255,255,0.75);font-size:12px">搜索热度 <strong style="color:#60a5fa">${params[0].value}</strong></div>`,
    },
    grid: { left: 16, right: 16, top: 24, bottom: 24, containLabel: true },
    xAxis: {
      type: 'category',
      data: months,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'var(--font-sans)' },
    },
    yAxis: {
      type: 'value',
      min: Math.max(0, Math.round(min * 0.8)),
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 3, shadowBlur: 10, shadowColor: 'rgba(37,99,235,0.2)' },
      itemStyle: { color: '#2563eb', borderColor: '#fff', borderWidth: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(37, 99, 235, 0.25)' },
          { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
        ]),
      },
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color: '#94a3b8', type: 'dashed', width: 1 },
        data: [{ yAxis: Math.round((max + min) / 2) }],
      },
      animationDuration: 1000,
      animationEasing: 'cubicOut',
    }],
  }
}

function buildCompetitorBarOption(competitors: any[]): EChartsOption {
  const names = competitors.map((c) => c.brand || c.title.slice(0, 12))
  const sales = competitors.map((c) => c.estimated_monthly_sales)

  return {
    color: ['#3b82f6'],
    tooltip: {
      trigger: 'axis',
      ...DARK_TOOLTIP,
      formatter: (params: any) => `<div style="font-weight:800;margin-bottom:4px">${params[0].name}</div><div style="color:rgba(255,255,255,0.75);font-size:12px">月销量 <strong style="color:#60a5fa">${Number(params[0].value).toLocaleString()}</strong></div>`,
    },
    grid: { left: 16, right: 24, top: 16, bottom: 16, containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, formatter: (v: number) => `${(v / 1000).toFixed(1)}k` },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#475569', fontSize: 11, fontWeight: 700, fontFamily: 'var(--font-sans)' },
    },
    series: [{
      type: 'bar',
      data: sales,
      barWidth: 18,
      itemStyle: { borderRadius: [0, 6, 6, 0], color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#60a5fa' }, { offset: 1, color: '#2563eb' }]) },
      label: { show: true, position: 'right', formatter: (params: any) => `${(params.value / 1000).toFixed(1)}k`, color: '#64748b', fontSize: 10, fontWeight: 800 },
      animationDuration: 800,
      animationEasing: 'cubicOut',
    }],
  }
}

function extractOpportunityTag(opp: string): string {
  const priorityTags: { patterns: string[]; tag: string }[] = [
    { patterns: ['Listing', '广告', '核心卖点'], tag: 'Listing 优化' },
    { patterns: ['密封', '防漏', '漏水'], tag: '防漏强化' },
    { patterns: ['异味', '材质', '食品级', '掉色', '发黄', '掉毛', '扎', '味'], tag: '材质升级' },
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
  ]
  for (const { patterns, tag } of priorityTags) {
    if (patterns.some((p) => opp.includes(p))) return tag
  }
  return '差异化机会'
}
