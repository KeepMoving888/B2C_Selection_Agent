import {
  EyeOutlined,
  GlobalOutlined,
  LineChartOutlined,
  RiseOutlined,
  SearchOutlined,
  StarOutlined,
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

export default function MarketInsights() {
  const dispatch = useDispatch()
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<AnalysisReport | null>(null)

  useEffect(() => {
    dispatch(setPageTitle('市场洞察'))
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

  const priceSalesOption: EChartsOption | null = useMemo(() => {
    if (!report) return null
    const competitors = report.market_analysis.competitors.slice(0, 10)
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['售价', '月销量'], top: 0 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: competitors.map((c) => c.brand || c.title.slice(0, 12)) },
      yAxis: [
        { type: 'value', name: '售价 USD' },
        { type: 'value', name: '月销量' },
      ],
      series: [
        {
          name: '售价',
          type: 'bar',
          data: competitors.map((c) => c.price),
          itemStyle: { color: '#60a5fa' },
          label: { show: true, formatter: '${c}' },
        },
        {
          name: '月销量',
          type: 'line',
          yAxisIndex: 1,
          data: competitors.map((c) => c.estimated_monthly_sales),
          itemStyle: { color: '#f59e0b' },
          lineStyle: { width: 2.5 },
        },
      ],
    }
  }, [report])

  const trendOption: EChartsOption | null = useMemo(() => {
    if (!report) return null
    const s = report.trend_analysis.series
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['今年热度', '去年同期', '未来3月预测', '提前备货窗口', '旺季高峰'], top: 0 },
      grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
      xAxis: { type: 'category', data: [...s.months, ...s.forecast_months] },
      yAxis: { type: 'value', name: '搜索热度', min: 0, max: 100 },
      series: [
        {
          name: '今年热度',
          type: 'line',
          data: s.values,
          itemStyle: { color: '#2563eb' },
          lineStyle: { width: 3 },
          smooth: true,
        },
        {
          name: '去年同期',
          type: 'line',
          data: s.last_year_values,
          itemStyle: { color: '#94a3b8' },
          lineStyle: { type: 'dotted' },
          smooth: true,
        },
        {
          name: '未来3月预测',
          type: 'line',
          data: [...Array(11).fill(null), s.values[11], ...s.forecast_values],
          itemStyle: { color: '#f59e0b' },
          lineStyle: { type: 'dashed' },
          smooth: true,
        },
        {
          name: '提前备货窗口',
          type: 'scatter',
          data: s.months.map((_m, i) => (report.trend_analysis.entry_windows.includes(i + 1) ? s.values[i] : null)),
          itemStyle: { color: '#14b8a6', opacity: 0.6 },
          symbolSize: 16,
        },
        {
          name: '旺季高峰',
          type: 'scatter',
          data: s.months.map((_m, i) => (report.trend_analysis.peak_months.includes(i + 1) ? s.values[i] : null)),
          itemStyle: { color: '#ef4444', opacity: 0.6 },
          symbolSize: 16,
        },
      ],
    }
  }, [report])

  const competitorColumns = [
    { title: '品牌/标题', dataIndex: 'brand', render: (_: unknown, r: any) => r.brand || r.title },
    { title: '店铺', dataIndex: 'store' },
    { title: '价格', dataIndex: 'price', render: (v: number) => `$${v.toFixed(2)}` },
    { title: '评分', dataIndex: 'rating' },
    { title: '评论数', dataIndex: 'review_count' },
    { title: '月销量', dataIndex: 'estimated_monthly_sales' },
    { title: 'BSR', dataIndex: 'bsr' },
    {
      title: '操作',
      render: (_: unknown, r: any) => (
        <Button type="link" href={r.link} target="_blank" icon={<EyeOutlined />}>
          查看
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: <Link to="/dashboard">首页</Link> },
          { title: '市场洞察' },
        ]}
        style={{ marginBottom: 16 }}
      />
      <Title level={3}>市场洞察</Title>

      <Card style={{ marginBottom: 24 }}>
        <Form layout="inline" onFinish={onFinish} initialValues={{ market: 'US' }}>
          <Form.Item name="keyword" rules={[{ required: true, message: '请输入关键词' }]} style={{ flex: 1, minWidth: 240 }}>
            <Input prefix={<SearchOutlined />} placeholder="输入关键词（如 cat toy, yoga mat）" />
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
              分析市场
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>正在分析市场数据...</div>
        </div>
      )}

      {!loading && !report && (
        <Empty description="输入关键词开始市场洞察分析" style={{ padding: 80 }} />
      )}

      {!loading && report && (
        <>
          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="平均售价"
                  value={report.market_analysis.avg_price}
                  prefix="$"
                  precision={2}
                  valueStyle={{ color: '#1976d2' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="平均评分"
                  value={report.market_analysis.avg_rating}
                  prefix={<StarOutlined />}
                  valueStyle={{ color: '#ff9800' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="平均评论数"
                  value={report.market_analysis.avg_reviews}
                  valueStyle={{ color: '#4caf50' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="竞品数量"
                  value={report.market_analysis.competitors.length}
                  prefix={<GlobalOutlined />}
                  valueStyle={{ color: '#9c27b0' }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={14}>
              <Card title={<><LineChartOutlined /> 竞品价格带与月销量分布</>}>
                {priceSalesOption && <ReactECharts option={priceSalesOption} style={{ height: 360 }} />}
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card title={<><RiseOutlined /> 头部竞品 TOP10</>}>
                <Table
                  size="small"
                  columns={competitorColumns}
                  dataSource={report.market_analysis.competitors.slice(0, 10)}
                  rowKey={(r) => r.title + r.brand}
                  pagination={false}
                  scroll={{ y: 320 }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={16}>
              <Card title={<><LineChartOutlined /> 类目趋势与季节性</>}>
                {trendOption && <ReactECharts option={trendOption} style={{ height: 380 }} />}
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card title="市场机会识别">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {report.trending_products.slice(0, 5).map((t: any, i: number) => (
                    <Card key={i} size="small" style={{ borderLeft: `4px solid ${t.opportunity === '高' ? '#1976d2' : '#4caf50'}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Text strong>{t.keyword}</Text>
                        <Tag color={t.opportunity === '高' ? 'blue' : 'green'}>{t.opportunity}机会</Tag>
                      </div>
                      <Text type="secondary">竞争强度：{t.competition}</Text>
                    </Card>
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>

          <Card title="季节与入场节奏">
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <Text strong>旺季高峰：</Text>
                <Tag color="red">{report.trend_analysis.season_narrative.peak_months}</Tag>
                <br />
                <Text strong>建议备货窗口：</Text>
                <Tag color="cyan">{report.trend_analysis.season_narrative.entry_months}</Tag>
              </Col>
              <Col xs={24} md={12}>
                <Text>{report.trend_analysis.season_narrative.season_desc}</Text>
                <br />
                <Text type="secondary">{report.trend_analysis.season_narrative.trend_desc}</Text>
              </Col>
            </Row>
          </Card>
        </>
      )}
    </div>
  )
}
