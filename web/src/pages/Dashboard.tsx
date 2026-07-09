import {
  BarChartOutlined,
  FileTextOutlined,
  PlusOutlined,
  RiseOutlined,
  ShoppingOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { Button, Card, Col, Empty, Row, Statistic, Table, Typography } from 'antd'
import type { EChartsOption } from 'echarts'
import ReactECharts from 'echarts-for-react'
import { useEffect, useMemo, useState } from 'react'
import { useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { analysisApi } from '../services/api'
import { setPageTitle } from '../store/slices/uiSlice'
import type { AnalysisHistoryItem } from '../types'

const { Title, Text } = Typography

interface TrendPoint {
  date: string
  analyses: number
  recommendationRate: number
}

export default function Dashboard() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    dispatch(setPageTitle('仪表板'))
  }, [dispatch])

  useEffect(() => {
    setLoading(true)
    analysisApi
      .history()
      .then((res) => setHistory(res.data.items || []))
      .finally(() => setLoading(false))
  }, [])

  const stats = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10)
    const todayItems = history.filter((h) => h.created_at.startsWith(today))
    const avgScore = history.length
      ? history.reduce((sum, h) => sum + h.overall_score, 0) / history.length
      : 0
    const recommended = history.filter((h) => h.overall_score >= 70).length
    const risky = history.filter((h) => h.overall_score < 50).length
    return {
      todayCount: todayItems.length,
      avgScore: avgScore.toFixed(1),
      recommended,
      risky,
    }
  }, [history])

  const trendData: TrendPoint[] = useMemo(() => {
    const map: Record<string, { count: number; recommended: number }> = {}
    for (let i = 6; i >= 0; i--) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      map[key] = { count: 0, recommended: 0 }
    }
    history.forEach((h) => {
      const key = h.created_at.slice(0, 10)
      if (map[key]) {
        map[key].count += 1
        if (h.overall_score >= 70) map[key].recommended += 1
      }
    })
    return Object.entries(map).map(([date, val]) => ({
      date: date.slice(5),
      analyses: val.count,
      recommendationRate: val.count ? Math.round((val.recommended / val.count) * 100) : 0,
    }))
  }, [history])

  const chartOption: EChartsOption = useMemo(
    () => ({
      tooltip: { trigger: 'axis' },
      legend: { data: ['分析量', '推荐率'], bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
      xAxis: { type: 'category', data: trendData.map((d) => d.date) },
      yAxis: [
        { type: 'value', name: '分析量', minInterval: 1 },
        { type: 'value', name: '推荐率 %', max: 100 },
      ],
      series: [
        {
          name: '分析量',
          type: 'bar',
          data: trendData.map((d) => d.analyses),
          itemStyle: { color: '#1976d2', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '推荐率',
          type: 'line',
          yAxisIndex: 1,
          data: trendData.map((d) => d.recommendationRate),
          itemStyle: { color: '#4caf50' },
          smooth: true,
        },
      ],
    }),
    [trendData]
  )

  const columns = [
    { title: '关键词', dataIndex: 'keyword', key: 'keyword' },
    { title: '市场', dataIndex: 'market', key: 'market' },
    {
      title: '评分',
      dataIndex: 'overall_score',
      key: 'overall_score',
      render: (score: number) => (
        <Text strong style={{ color: score >= 70 ? '#4caf50' : score >= 50 ? '#ff9800' : '#f44336' }}>
          {score}
        </Text>
      ),
    },
    { title: '等级', dataIndex: 'grade', key: 'grade' },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: AnalysisHistoryItem) => (
        <Button type="link" onClick={() => navigate(`/product-analysis?id=${record.id}`)}>
          查看
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>仪表板</Title>
      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日分析商品数"
              value={stats.todayCount}
              prefix={<ShoppingOutlined />}
              valueStyle={{ color: '#1976d2' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均评分"
              value={stats.avgScore}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#1976d2' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="推荐商品数"
              value={stats.recommended}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#4caf50' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="高风险商品数"
              value={stats.risky}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#f44336' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card title="近7天分析量与推荐率趋势" style={{ height: '100%' }}>
            {trendData.some((d) => d.analyses > 0) ? (
              <ReactECharts option={chartOption} style={{ height: 320 }} />
            ) : (
              <Empty description="暂无趋势数据" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="快捷操作" style={{ height: '100%' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Button type="primary" icon={<PlusOutlined />} block onClick={() => navigate('/product-analysis')}>
                新建分析
              </Button>
              <Button icon={<ShoppingOutlined />} block disabled>
                批量导入
              </Button>
              <Button icon={<FileTextOutlined />} block onClick={() => navigate('/report-center')}>
                查看报告
              </Button>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="最近分析记录">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={history.slice(0, 5)}
          loading={loading}
          pagination={false}
        />
      </Card>
    </div>
  )
}
