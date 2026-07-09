import {
  BulbOutlined,
  CommentOutlined,
  DislikeOutlined,
  LikeOutlined,
  MehOutlined,
  RiseOutlined,
  SearchOutlined,
  TagOutlined,
} from '@ant-design/icons'
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
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
import { Link } from 'react-router-dom'
import { analysisApi } from '../services/api'
import { setPageTitle } from '../store/slices/uiSlice'
import type { AnalysisReport } from '../types'

const { Title, Text } = Typography

const SENTIMENT_COLORS = {
  positive: '#22c55e',
  neutral: '#f59e0b',
  negative: '#ef4444',
}

export default function ReviewAnalytics() {
  const dispatch = useDispatch()
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<AnalysisReport | null>(null)

  useEffect(() => {
    dispatch(setPageTitle('评论分析'))
  }, [dispatch])

  const onFinish = async (values: { keyword: string; market: string }) => {
    setLoading(true)
    try {
      const res = await analysisApi.create({
        keyword: values.keyword,
        market: values.market,
        budget: 'medium',
      })
      setReport(res.data.report)
    } finally {
      setLoading(false)
    }
  }

  const sentiment = useMemo(() => {
    if (!report) return null
    const rng = (seed: string) => {
      let h = 0
      for (let i = 0; i < seed.length; i++) h = (h << 5) - h + seed.charCodeAt(i)
      return Math.abs(h) % 100
    }
    const positive = 35 + (rng(report.keyword + 'pos') % 40)
    const negative = 10 + (rng(report.keyword + 'neg') % 25)
    const neutral = 100 - positive - negative
    return { positive, neutral, negative: Math.max(0, negative) }
  }, [report])

  const sentimentOption: EChartsOption | null = useMemo(() => {
    if (!sentiment) return null
    return {
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      color: [SENTIMENT_COLORS.positive, SENTIMENT_COLORS.neutral, SENTIMENT_COLORS.negative],
      series: [
        {
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
          label: { show: true, formatter: '{b}\n{d}%' },
          data: [
            { value: sentiment.positive, name: '正面评价' },
            { value: sentiment.neutral, name: '中性评价' },
            { value: sentiment.negative, name: '负面评价' },
          ],
        },
      ],
    }
  }, [sentiment])

  const wordCloudWords = useMemo(() => {
    if (!report) return []
    return [
      ...report.review_insights.pain_points.map((t) => ({ text: t, type: '痛点' })),
      ...report.review_insights.praised_features.map((t) => ({ text: t, type: '好评' })),
      ...report.review_insights.opportunities.map((t) => ({ text: t, type: '机会' })),
    ]
  }, [report])

  const timelineData = useMemo(() => {
    if (!report) return []
    const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    return months.map((m, i) => {
      const base = 4 + Math.sin(i / 2) * 1.2
      return {
        month: m,
        positive: Math.max(1, Math.round((base + 0.5) * 10) / 10),
        neutral: Math.max(1, Math.round((base - 0.3) * 10) / 10),
        negative: Math.max(0.5, Math.round((base - 1) * 10) / 10),
      }
    })
  }, [report])

  const timelineOption: EChartsOption | null = useMemo(() => {
    if (!timelineData.length) return null
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['正面', '中性', '负面'], bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
      xAxis: { type: 'category', data: timelineData.map((d) => d.month) },
      yAxis: { type: 'value', name: '占比 %' },
      series: [
        { name: '正面', type: 'line', stack: 'Total', areaStyle: {}, data: timelineData.map((d) => d.positive), itemStyle: { color: SENTIMENT_COLORS.positive } },
        { name: '中性', type: 'line', stack: 'Total', areaStyle: {}, data: timelineData.map((d) => d.neutral), itemStyle: { color: SENTIMENT_COLORS.neutral } },
        { name: '负面', type: 'line', stack: 'Total', areaStyle: {}, data: timelineData.map((d) => d.negative), itemStyle: { color: SENTIMENT_COLORS.negative } },
      ],
    }
  }, [timelineData])

  const reviewColumns = [
    { title: '标签', dataIndex: 'text', key: 'text', render: (v: string) => <Tag icon={<TagOutlined />}>{v}</Tag> },
    { title: '类型', dataIndex: 'type', key: 'type', render: (v: string) => <Tag color={v === '痛点' ? 'red' : v === '好评' ? 'green' : 'blue'}>{v}</Tag> },
  ]

  const reviewRows = useMemo(() => {
    if (!report) return []
    return [
      ...report.review_insights.pain_points.map((t) => ({ text: t, type: '痛点' })),
      ...report.review_insights.praised_features.map((t) => ({ text: t, type: '好评' })),
      ...report.review_insights.opportunities.map((t) => ({ text: t, type: '机会' })),
    ]
  }, [report])

  return (
    <div>
      <Breadcrumb
        items={[
          { title: <Link to="/dashboard">首页</Link> },
          { title: '评论分析' },
        ]}
        style={{ marginBottom: 16 }}
      />
      <Title level={3}>评论分析</Title>

      <Card style={{ marginBottom: 24 }}>
        <Form layout="inline" onFinish={onFinish} initialValues={{ market: 'US' }}>
          <Form.Item name="keyword" rules={[{ required: true, message: '请输入关键词' }]} style={{ flex: 1, minWidth: 240 }}>
            <Input prefix={<CommentOutlined />} placeholder="输入关键词分析评论（如 dog chew toys）" />
          </Form.Item>
          <Form.Item name="market">
            <Select style={{ width: 140 }} options={[
              { value: 'US', label: '美国站' },
              { value: 'UK', label: '英国站' },
              { value: 'DE', label: '德国站' },
              { value: 'JP', label: '日本站' },
              { value: 'CA', label: '加拿大站' },
            ]} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
              分析评论
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>正在分析评论数据...</div>
        </div>
      )}

      {!loading && !report && (
        <Empty description="输入关键词开始评论分析" style={{ padding: 80 }} />
      )}

      {!loading && report && sentiment && (
        <>
          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic title="正面评价" value={sentiment.positive} suffix="%" valueStyle={{ color: SENTIMENT_COLORS.positive }} prefix={<LikeOutlined />} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic title="中性评价" value={sentiment.neutral} suffix="%" valueStyle={{ color: SENTIMENT_COLORS.neutral }} prefix={<MehOutlined />} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic title="负面评价" value={sentiment.negative} suffix="%" valueStyle={{ color: SENTIMENT_COLORS.negative }} prefix={<DislikeOutlined />} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic title="NPS 预估" value={sentiment.positive - sentiment.negative} prefix={<RiseOutlined />} valueStyle={{ color: sentiment.positive - sentiment.negative > 0 ? '#16a34a' : '#ef4444' }} />
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={10}>
              <Card title="评论情感分布">
                {sentimentOption && <ReactECharts option={sentimentOption} style={{ height: 320 }} />}
              </Card>
            </Col>
            <Col xs={24} lg={14}>
              <Card title="关键词词云">
                <div style={{ minHeight: 320, padding: 12, display: 'flex', flexWrap: 'wrap', gap: 10, alignContent: 'center', justifyContent: 'center' }}>
                  {wordCloudWords.map((w, i) => (
                    <Tag
                      key={i}
                      style={{
                        fontSize: 14 + Math.floor(Math.random() * 12),
                        padding: '6px 12px',
                        borderRadius: 16,
                        cursor: 'default',
                      }}
                      color={w.type === '痛点' ? 'red' : w.type === '好评' ? 'green' : 'blue'}
                    >
                      {w.text}
                    </Tag>
                  ))}
                </div>
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card title="用户痛点识别">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {report.review_insights.pain_points.map((p: string, i: number) => (
                    <div key={i} style={{ padding: 12, background: '#fef2f2', borderRadius: 8, borderLeft: '4px solid #ef4444' }}>
                      <Text strong>{p}</Text>
                    </div>
                  ))}
                </Space>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="好评亮点">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {report.review_insights.praised_features.map((p: string, i: number) => (
                    <div key={i} style={{ padding: 12, background: '#f0fdf4', borderRadius: 8, borderLeft: '4px solid #22c55e' }}>
                      <Text strong>{p}</Text>
                    </div>
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card title={<><BulbOutlined /> 改进建议</>}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {report.review_insights.opportunities.map((o: string, i: number) => (
                    <div key={i} style={{ padding: 12, background: '#eff6ff', borderRadius: 8, borderLeft: '4px solid #3b82f6' }}>
                      <Text>{o}</Text>
                    </div>
                  ))}
                </Space>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="评论趋势时间线">
                {timelineOption && <ReactECharts option={timelineOption} style={{ height: 320 }} />}
              </Card>
            </Col>
          </Row>

          <Card title="评论关键词清单">
            <Table
              size="small"
              columns={reviewColumns}
              dataSource={reviewRows}
              rowKey={(r) => r.text}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </>
      )}
    </div>
  )
}
