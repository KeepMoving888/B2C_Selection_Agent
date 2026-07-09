import {
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  FilterOutlined,
  ShareAltOutlined,
} from '@ant-design/icons'
import {
  Breadcrumb,
  Button,
  Card,
  Empty,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useDispatch } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import { analysisApi } from '../services/api'
import { setPageTitle } from '../store/slices/uiSlice'
import type { AnalysisHistoryItem } from '../types'

const { Title, Text } = Typography

export default function ReportCenter() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([])
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [filterGrade, setFilterGrade] = useState<string>('')
  const [filterKeyword, setFilterKeyword] = useState('')
  const [detailId, setDetailId] = useState<string | null>(null)
  const [detail, setDetail] = useState<any>(null)

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
      .then((res) => setHistory(res.data.items || []))
      .finally(() => setLoading(false))
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
    analysisApi.get(id).then((res) => setDetail(res.data.report))
  }

  const exportCSV = (items: AnalysisHistoryItem[]) => {
    const rows = [
      ['报告ID', '关键词', '市场', '综合评分', '等级', '创建时间'],
      ...items.map((h) => [h.id, h.keyword, h.market, h.overall_score, h.grade, new Date(h.created_at).toLocaleString()]),
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

  const exportJSON = (items: AnalysisHistoryItem[]) => {
    const blob = new Blob([JSON.stringify(items, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `reports_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    message.success(`已导出 ${items.length} 条报告`)
  }

  const shareReport = (id: string) => {
    const url = `${window.location.origin}/product-analysis?id=${id}`
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

  const columns = [
    { title: '关键词', dataIndex: 'keyword', key: 'keyword' },
    { title: '市场', dataIndex: 'market', key: 'market' },
    {
      title: '等级',
      dataIndex: 'grade',
      key: 'grade',
      render: (v: string) => (
        <Tag color={v === 'A' ? '#4caf50' : v === 'B' ? '#1976d2' : v === 'C' ? '#ff9800' : '#f44336'}>{v}</Tag>
      ),
    },
    {
      title: '评分',
      dataIndex: 'overall_score',
      key: 'overall_score',
      render: (v: number) => (
        <Text strong style={{ color: v >= 70 ? '#4caf50' : v >= 50 ? '#ff9800' : '#f44336' }}>
          {v}
        </Text>
      ),
    },
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
        <Space>
          <Button type="link" icon={<EyeOutlined />} onClick={() => showDetail(record.id)}>
            详情
          </Button>
          <Button type="link" icon={<ShareAltOutlined />} onClick={() => shareReport(record.id)}>
            分享
          </Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => deleteReport(record.id)}>
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: <Link to="/dashboard">首页</Link> },
          { title: '报告中心' },
        ]}
        style={{ marginBottom: 16 }}
      />
      <Title level={3}>报告中心</Title>

      <Card style={{ marginBottom: 24 }} title={<><FilterOutlined /> 筛选</>}>
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
            <Button icon={<FileTextOutlined />} onClick={() => navigate('/product-analysis')}>
              新建分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title={`报告列表（共 ${filteredHistory.length} 条）`}
        extra={
          <Space>
            <Button icon={<FileExcelOutlined />} onClick={() => exportCSV(filteredHistory)}>
              导出 Excel
            </Button>
            <Button icon={<DownloadOutlined />} onClick={() => exportJSON(filteredHistory)}>
              导出 JSON
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={filteredHistory}
          loading={loading}
          pagination={{ pageSize: 10 }}
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
        />
        {filteredHistory.length === 0 && !loading && <Empty description="暂无报告" />}
      </Card>

      <Modal
        title="报告详情"
        open={!!detailId}
        onCancel={() => { setDetailId(null); setDetail(null) }}
        width={800}
        footer={[
          <Button key="close" onClick={() => { setDetailId(null); setDetail(null) }}>关闭</Button>,
          <Button key="view" type="primary" onClick={() => { navigate(`/product-analysis?id=${detailId}`); setDetailId(null) }}>查看完整报告</Button>,
        ]}
      >
        {detail ? (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong style={{ fontSize: 18 }}>{detail.keyword}</Text>
              <Tag color={detail.verdict_color} style={{ marginLeft: 12 }}>{detail.verdict}</Tag>
            </div>
            <Text>市场：{detail.market_analysis.market_profile.name} · 预算：{detail.budget}</Text>
            <Text>综合评分：{detail.overall_score}/{detail.max_score} · 等级：{detail.grade}</Text>
            <Text>毛利率：{detail.profit_analysis.gross_margin_pct}</Text>
            <div>
              <Text strong>用户痛点</Text>
              <ul>
                {detail.review_insights.pain_points.slice(0, 3).map((p: string, i: number) => <li key={i}>{p}</li>)}
              </ul>
            </div>
            <div>
              <Text strong>优化建议</Text>
              <ul>
                {detail.profit_analysis.suggestions?.slice(0, 3).map((s: string, i: number) => <li key={i}>{s}</li>) || <li>暂无</li>}
              </ul>
            </div>
          </Space>
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        )}
      </Modal>
    </div>
  )
}
