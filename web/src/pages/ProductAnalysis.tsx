import {
  ArrowLeftOutlined,
  AuditOutlined,
  LineChartOutlined,
  RiseOutlined,
  SearchOutlined,
  ShopOutlined,
  SmileOutlined,
} from '@ant-design/icons';
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { EChartsOption } from 'echarts'
import ReactECharts from 'echarts-for-react'
import { useEffect, useMemo, useState } from 'react'
import { useDispatch } from 'react-redux'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { analysisApi } from '../services/api'
import { setPageTitle } from '../store/slices/uiSlice'
import type { AnalysisReport } from '../types'

const { Title, Text } = Typography

const COST_COLORS: Record<string, string> = {
  '产品成本': '#1976d2',
  '头程物流': '#4caf50',
  'FBA 费用': '#ff9800',
  '平台佣金': '#f44336',
  '广告费用': '#9c27b0',
  '退货预留': '#00bcd4',
  '其他杂费': '#607d8b',
}

export default function ProductAnalysis() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<AnalysisReport | null>(null)

  useEffect(() => {
    dispatch(setPageTitle('商品分析'))
  }, [dispatch])

  useEffect(() => {
    const id = searchParams.get('id')
    if (id) {
      setLoading(true)
      analysisApi
        .get(id)
        .then((res) => setReport(res.data.report))
        .finally(() => setLoading(false))
    }
  }, [searchParams])

  const onFinish = async (values: {
    keyword: string
    market: string
    budget: string
    selling_price?: number
    unit_cost?: number
  }) => {
    setLoading(true)
    try {
      const payload: {
        keyword: string
        market: string
        budget: string
        selling_price?: number
        unit_cost?: number
      } = {
        keyword: values.keyword,
        market: values.market,
        budget: values.budget,
      }
      if (values.selling_price) payload.selling_price = values.selling_price
      if (values.unit_cost) payload.unit_cost = values.unit_cost
      const res = await analysisApi.create(payload)
      setReport(res.data.report)
      navigate(`/product-analysis?id=${res.data.id}`, { replace: true })
    } finally {
      setLoading(false)
    }
  }

  const radarOption: EChartsOption | null = useMemo(() => {
    if (!report) return null
    const bd = report.score_breakdown
    const indicators = [
      { name: '利润空间', max: 50 },
      { name: '趋势热度', max: 25 },
      { name: '竞争强度', max: 20 },
      { name: '评论洞察', max: 15 },
    ]
    return {
      tooltip: { trigger: 'item' },
      radar: {
        indicator: indicators,
        radius: '65%',
        splitNumber: 4,
        axisName: { color: '#666' },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: [bd['利润空间'], bd['趋势热度'], bd['竞争强度'], bd['评论洞察']],
              name: report.keyword,
              areaStyle: { color: 'rgba(25, 118, 210, 0.2)' },
              lineStyle: { color: '#1976d2', width: 2 },
              itemStyle: { color: '#1976d2' },
              symbolSize: 6,
            },
          ],
        },
      ],
    }
  }, [report])

  const trendOption: EChartsOption | null = useMemo(() => {
    if (!report) return null
    const s = report.trend_analysis.series
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['今年热度', '去年同期', '未来3月预测'], bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
      xAxis: { type: 'category', data: [...s.months, ...s.forecast_months] },
      yAxis: { type: 'value', min: 0, max: 100 },
      series: [
        {
          name: '今年热度',
          type: 'line',
          data: s.values,
          itemStyle: { color: '#1976d2' },
          smooth: true,
        },
        {
          name: '去年同期',
          type: 'line',
          data: s.last_year_values,
          itemStyle: { color: '#9e9e9e' },
          lineStyle: { type: 'dashed' },
          smooth: true,
        },
        {
          name: '未来3月预测',
          type: 'line',
          data: [...Array(11).fill(null), s.values[11], ...s.forecast_values],
          itemStyle: { color: '#4caf50' },
          lineStyle: { type: 'dashed' },
          smooth: true,
        },
      ],
    }
  }, [report])

  const costBarOption: EChartsOption | null = useMemo(() => {
    if (!report) return null
    const bd = report.profit_analysis.cost_breakdown
    const entries = Object.entries(bd).sort((a, b) => b[1] - a[1])
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: entries.map(([k]) => k) },
      series: [
        {
          type: 'bar',
          data: entries.map(([k, v]) => ({ value: v, itemStyle: { color: COST_COLORS[k] || '#1976d2' } })),
          label: { show: true, formatter: '${c}' },
          barWidth: '60%',
        },
      ],
    }
  }, [report])

  const competitorColumns = [
    { title: '品牌', dataIndex: 'brand', key: 'brand' },
    { title: '价格', dataIndex: 'price', key: 'price', render: (v: number) => `$${v.toFixed(2)}` },
    { title: '评分', dataIndex: 'rating', key: 'rating' },
    { title: '评论数', dataIndex: 'review_count', key: 'review_count' },
    { title: 'BSR', dataIndex: 'bsr', key: 'bsr' },
    { title: '月销量', dataIndex: 'estimated_monthly_sales', key: 'sales' },
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: <Link to="/dashboard">首页</Link> },
          { title: '商品分析' },
        ]}
        style={{ marginBottom: 16 }}
      />
      <Title level={3}>商品分析</Title>

      <Card style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="inline"
          onFinish={onFinish}
          onFinishFailed={(errors) => console.error('表单验证失败', errors)}
          initialValues={{ market: 'US', budget: 'medium' }}
        >
          <Form.Item
            name="keyword"
            rules={[{ required: true, message: '请输入关键词' }]}
            style={{ flex: 1, minWidth: 220 }}
          >
            <Input prefix={<SearchOutlined />} placeholder="输入关键词（支持英文空格，多个用逗号/分号分隔）" />
          </Form.Item>
          <Form.Item name="market">
            <Select style={{ width: 120 }} options={[
              { value: 'US', label: '美国站' },
              { value: 'UK', label: '英国站' },
              { value: 'DE', label: '德国站' },
              { value: 'JP', label: '日本站' },
              { value: 'CA', label: '加拿大站' },
            ]} />
          </Form.Item>
          <Form.Item name="budget">
            <Select style={{ width: 120 }} options={[
              { value: 'low', label: '低预算' },
              { value: 'medium', label: '中等预算' },
              { value: 'high', label: '高预算' },
            ]} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
              开始分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>正在生成分析报告...</div>
        </div>
      )}

      {!loading && !report && (
        <Empty description="输入关键词开始分析" style={{ padding: 80 }} />
      )}

      {!loading && report && (
        <>
          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={18}>
              <Card>
                <Row align="middle" gutter={16}>
                  <Col>
                    <div
                      style={{
                        width: 64,
                        height: 64,
                        borderRadius: 12,
                        background: report.verdict_color,
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 28,
                        fontWeight: 800,
                      }}
                    >
                      {report.grade}
                    </div>
                  </Col>
                  <Col flex="auto">
                    <Title level={4} style={{ margin: 0 }}>
                      {report.keyword}
                    </Title>
                    <Space size={16} style={{ marginTop: 8 }}>
                      <Text>市场：{report.market_analysis.market_profile.name}</Text>
                      <Text>预算：{report.budget}</Text>
                      <Tag color={report.verdict_color}>{report.verdict}</Tag>
                    </Space>
                  </Col>
                  <Col>
                    <Statistic title="综合评分" value={report.overall_score} suffix={`/${report.max_score}`} />
                  </Col>
                </Row>
              </Card>
            </Col>
            <Col xs={24} lg={6}>
              <Card style={{ height: '100%' }}>
                <Statistic
                  title="毛利率"
                  value={report.profit_analysis.gross_margin_pct}
                  valueStyle={{ color: report.profit_analysis.gross_margin >= 0.2 ? '#4caf50' : '#ff9800' }}
                  prefix={<RiseOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card title="综合评分雷达图">
                {radarOption && <ReactECharts option={radarOption} style={{ height: 320 }} />}
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="五维评分拆解">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {Object.entries(report.score_breakdown).map(([key, value]) => {
                    const maxMap: Record<string, number> = {
                      '利润空间': 50,
                      '趋势热度': 25,
                      '竞争强度': 20,
                      '评论洞察': 15,
                    };
                    const pct = Math.round((value / (maxMap[key] || 40)) * 100);
                    return (
                      <div key={key}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Text>{key}</Text>
                          <Text strong>{value}</Text>
                        </div>
                        <Progress
                          percent={pct}
                          showInfo={false}
                          strokeColor={
                            key === '利润空间'
                              ? '#1976d2'
                              : key === '趋势热度'
                              ? '#4caf50'
                              : key === '竞争强度'
                              ? '#ff9800'
                              : '#9c27b0'
                          }
                        />
                      </div>
                    );
                  })}
                </Space>
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card title="利润测算">
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="售价">${report.profit_analysis.selling_price.toFixed(2)}</Descriptions.Item>
                  <Descriptions.Item label="产品成本">${report.profit_analysis.unit_cost.toFixed(2)}</Descriptions.Item>
                  <Descriptions.Item label="单件总成本">${report.profit_analysis.total_cost_per_unit.toFixed(2)}</Descriptions.Item>
                  <Descriptions.Item label="单件毛利">${report.profit_analysis.gross_profit_per_unit.toFixed(2)}</Descriptions.Item>
                  <Descriptions.Item label="毛利率">{report.profit_analysis.gross_margin_pct}</Descriptions.Item>
                  <Descriptions.Item label="盈亏平衡">{report.profit_analysis.breakeven_units ?? '-'} 件</Descriptions.Item>
                </Descriptions>
                <div style={{ marginTop: 16 }}>
                  <Text strong>成本结构</Text>
                  {costBarOption && <ReactECharts option={costBarOption} style={{ height: 220, marginTop: 8 }} />}
                </div>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="ROI 情景分析">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {Object.entries(report.profit_analysis.roi_scenarios).map(([name, s]: [string, any]) => (
                    <Card key={name} size="small" style={{ background: '#fafafa' }}>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Text strong>{name}</Text>
                          <div style={{ fontSize: 18, fontWeight: 700, color: s.ROI >= 50 ? '#4caf50' : '#ff9800' }}>
                            ROI {s.ROI}%
                          </div>
                        </Col>
                        <Col span={8}>
                          <Text type="secondary">月销量</Text>
                          <div style={{ fontWeight: 600 }}>{s['月销量']}</div>
                        </Col>
                        <Col span={8}>
                          <Text type="secondary">月毛利</Text>
                          <div style={{ fontWeight: 600 }}>${s['月毛利']}</div>
                        </Col>
                      </Row>
                    </Card>
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card title="市场洞察">
                <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="平均售价">${report.market_analysis.avg_price.toFixed(2)}</Descriptions.Item>
                  <Descriptions.Item label="平均评分">{report.market_analysis.avg_rating}</Descriptions.Item>
                  <Descriptions.Item label="平均评论数">{report.market_analysis.avg_reviews}</Descriptions.Item>
                </Descriptions>
                <Text strong>Top 竞品</Text>
                <Table
                  size="small"
                  columns={competitorColumns}
                  dataSource={report.market_analysis.competitors.slice(0, 5)}
                  rowKey={(r) => r.title}
                  pagination={false}
                  style={{ marginTop: 8 }}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="趋势热度">
                {trendOption && <ReactECharts option={trendOption} style={{ height: 280 }} />}
                <div style={{ marginTop: 12 }}>
                  <Text strong>旺季月份：</Text>
                  <Text>{report.trend_analysis.season_narrative.peak_months}</Text>
                  <br />
                  <Text strong>入局窗口：</Text>
                  <Text>{report.trend_analysis.season_narrative.entry_months}</Text>
                  <br />
                  <Text>{report.trend_analysis.season_narrative.season_desc}</Text>
                  <br />
                  <Text type="secondary">{report.trend_analysis.season_narrative.trend_desc}</Text>
                </div>
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card title={<><SmileOutlined /> 评论洞察</>}>
                <Text strong>用户痛点</Text>
                <ul>
                  {report.review_insights.pain_points.map((p: string, i: number) => (
                    <li key={i}><Text>{p}</Text></li>
                  ))}
                </ul>
                <Text strong>好评亮点</Text>
                <ul>
                  {report.review_insights.praised_features.map((p: string, i: number) => (
                    <li key={i}><Text type="success">{p}</Text></li>
                  ))}
                </ul>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title={<><AuditOutlined /> 合规风险</>}>
                <div style={{ marginBottom: 12 }}>
                  <Text strong>风险等级：</Text>
                  <Tag color={report.compliance.risk_level === '高' ? '#f44336' : report.compliance.risk_level === '中' ? '#ff9800' : '#4caf50'}>
                    {report.compliance.risk_level}
                  </Tag>
                  <Text type="secondary" style={{ marginLeft: 12 }}>
                    预估认证成本 ${report.compliance.estimated_cert_cost.toFixed(2)} / {report.compliance.estimated_cert_time}
                  </Text>
                </div>
                <Text strong>类目风险</Text>
                <ul>
                  {report.compliance.category_risks.map((r: string, i: number) => (
                    <li key={i}><Text>{r}</Text></li>
                  ))}
                </ul>
                <Text strong>强制认证</Text>
                <div style={{ marginTop: 8 }}>
                  {report.compliance.certifications.map((c: string, i: number) => (
                    <Tag key={i} color="blue" style={{ marginBottom: 4 }}>{c}</Tag>
                  ))}
                </div>
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card title={<><ShopOutlined /> 供应商推荐</>}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {report.suppliers.slice(0, 3).map((s: any, i: number) => (
                    <Card key={i} size="small">
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text strong>{s.name}</Text>
                        <Tag color="green">评分 {s.rating}</Tag>
                      </div>
                      <Text type="secondary">起订量 {s.moq} · 交期 {s.lead_time} · 产能 {s.capacity}</Text>
                      <div style={{ marginTop: 4 }}>
                        <Text>参考成本 ${s.unit_cost} · 样品费 ${s.sample_cost} · 响应率 {s.response_rate}%</Text>
                      </div>
                    </Card>
                  ))}
                </Space>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title={<><LineChartOutlined /> 行动计划</>}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {report.next_steps.map((s, i: number) => (
                    <Card key={i} size="small" style={{ background: '#fafafa' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text strong>{s.title}</Text>
                        <Tag color="blue">{s.phase}</Tag>
                      </div>
                      <Text type="secondary">负责人：{s.owner}</Text>
                      <ul style={{ marginBottom: 0 }}>
                        {s.tasks.map((t: string, j: number) => (
                          <li key={j}><Text>{t}</Text></li>
                        ))}
                      </ul>
                    </Card>
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>

          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>
            返回仪表板
          </Button>
        </>
      )}
    </div>
  )
}
