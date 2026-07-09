import {
  ArrowRightOutlined,
  CalculatorOutlined,
  DownloadOutlined,
  HistoryOutlined,
  PercentageOutlined,
  RiseOutlined,
  SaveOutlined,
  WalletOutlined,
} from '@ant-design/icons'
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  InputNumber,
  Row,
  Select,
  Slider,
  Space,
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
import { profitApi } from '../services/api'
import { setPageTitle } from '../store/slices/uiSlice'
import type { ProfitResult } from '../types'

const { Title, Text } = Typography

const COST_COLORS: Record<string, string> = {
  '产品成本': '#1e3a8a',
  '头程物流': '#06b6d4',
  'FBA 费用': '#f97316',
  '平台佣金': '#8b5cf6',
  '广告费用': '#ef4444',
  '退货预留': '#eab308',
  '其他杂费': '#6b7280',
}

const roiColor = (roi: number) => {
  if (roi < 20) return '#dc2626'
  if (roi < 40) return '#f97316'
  if (roi < 60) return '#eab308'
  return '#16a34a'
}

interface CalcRecord {
  id: string
  createdAt: string
  sellingPrice: number
  unitCost: number
  category: string
  market: string
  result: ProfitResult
}

export default function ProfitCalculator() {
  const dispatch = useDispatch()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ProfitResult | null>(null)
  const [history, setHistory] = useState<CalcRecord[]>([])
  const [volume, setVolume] = useState(300)
  const [costReduction, setCostReduction] = useState(0)
  const [adReduction, setAdReduction] = useState(0)
  const [fbaReduction, setFbaReduction] = useState(0)
  const [priceIncrease, setPriceIncrease] = useState(0)

  useEffect(() => {
    dispatch(setPageTitle('利润测算'))
  }, [dispatch])

  useEffect(() => {
    const saved = localStorage.getItem('profit_calc_history')
    if (saved) {
      try {
        setHistory(JSON.parse(saved))
      } catch {
        // ignore
      }
    }
  }, [])

  const onFinish = async (values: { selling_price: number; unit_cost: number; category: string; market: string }) => {
    setLoading(true)
    try {
      const res = await profitApi.calculate(values)
      setResult(res.data)
      const record: CalcRecord = {
        id: Date.now().toString(),
        createdAt: new Date().toISOString(),
        sellingPrice: values.selling_price,
        unitCost: values.unit_cost,
        category: values.category,
        market: values.market,
        result: res.data,
      }
      const next = [record, ...history].slice(0, 20)
      setHistory(next)
      localStorage.setItem('profit_calc_history', JSON.stringify(next))
      // reset sliders
      setCostReduction(0)
      setAdReduction(0)
      setFbaReduction(0)
      setPriceIncrease(0)
    } finally {
      setLoading(false)
    }
  }

  const simulatedResult = useMemo(() => {
    if (!result) return null
    const newPrice = result.selling_price + priceIncrease
    const newTotalCost = Math.max(0, result.total_cost_per_unit - costReduction - adReduction - fbaReduction)
    const newGrossProfit = newPrice - newTotalCost
    const newMargin = newPrice > 0 ? newGrossProfit / newPrice : 0
    return {
      totalCost: newTotalCost,
      grossProfit: newGrossProfit,
      margin: newMargin,
      marginPct: `${(newMargin * 100).toFixed(2)}%`,
    }
  }, [result, costReduction, adReduction, fbaReduction, priceIncrease])

  const costBarOption: EChartsOption | null = useMemo(() => {
    if (!result) return null
    const entries = Object.entries(result.cost_breakdown).sort((a, b) => b[1] - a[1])
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: entries.map(([k]) => k) },
      series: [
        {
          type: 'bar',
          data: entries.map(([k, v]) => ({
            value: v,
            itemStyle: { color: COST_COLORS[k] || '#1976d2' },
          })),
          label: { show: true, formatter: '${c}' },
          barWidth: '60%',
        },
      ],
    }
  }, [result])

  const roiTrendOption: EChartsOption | null = useMemo(() => {
    if (!result) return null
    const investment = result.unit_cost * 500 + 2000
    const grossProfit = result.gross_profit_per_unit
    const volumes = Array.from({ length: 51 }, (_, i) => 100 + i * 10)
    const roiValues = volumes.map((v) => (v * grossProfit / investment) * 100)
    const currentRoi = (volume * grossProfit / investment) * 100
    const scenarios = {
      保守: 100,
      中性: 300,
      乐观: 600,
    }
    const series: any[] = [
      {
        type: 'line',
        name: 'ROI 趋势',
        data: roiValues,
        smooth: true,
        areaStyle: { color: 'rgba(25, 118, 210, 0.1)' },
        lineStyle: { color: '#1976d2', width: 3 },
        showSymbol: false,
      },
      {
        type: 'scatter',
        name: '当前销量',
        data: [[volumes.indexOf(volume), currentRoi]],
        symbolSize: 14,
        itemStyle: { color: roiColor(currentRoi) },
      },
    ]
    Object.entries(scenarios).forEach(([name, vol]) => {
      const idx = volumes.indexOf(vol)
      if (idx >= 0) {
        const roi = roiValues[idx]
        series.push({
          type: 'scatter',
          name: `${name}情景`,
          data: [[idx, roi]],
          symbolSize: 10,
          label: { show: true, formatter: name, position: 'top' },
          itemStyle: { color: roiColor(roi) },
        })
      }
    })
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['ROI 趋势', '当前销量', '保守情景', '中性情景', '乐观情景'], bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
      xAxis: { type: 'category', data: volumes.map((v) => v.toString()) },
      yAxis: { type: 'value', name: 'ROI %', axisLabel: { formatter: '{value}%' } },
      series,
    }
  }, [result, volume])

  const bestScenario = useMemo(() => {
    if (!result) return null
    const entries = Object.entries(result.roi_scenarios)
    return entries.reduce((best, [name, data]: [string, any]) => (data.ROI > best.data.ROI ? { name, data } : best), {
      name: entries[0][0],
      data: entries[0][1] as any,
    })
  }, [result])

  const historyColumns = [
    { title: '时间', dataIndex: 'createdAt', render: (v: string) => new Date(v).toLocaleString() },
    { title: '市场', dataIndex: 'market' },
    { title: '类目', dataIndex: 'category' },
    { title: '售价', dataIndex: 'sellingPrice', render: (v: number) => `$${v.toFixed(2)}` },
    { title: '成本', dataIndex: 'unitCost', render: (v: number) => `$${v.toFixed(2)}` },
    { title: '毛利率', dataIndex: ['result', 'gross_margin_pct'], render: (_: unknown, r: CalcRecord) => r.result.gross_margin_pct },
    {
      title: '操作',
      render: (_: unknown, r: CalcRecord) => (
        <Button type="link" onClick={() => { setResult(r.result); form.setFieldsValue({ selling_price: r.sellingPrice, unit_cost: r.unitCost, category: r.category, market: r.market }); }}>
          载入
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: <Link to="/dashboard">首页</Link> },
          { title: '利润测算' },
        ]}
        style={{ marginBottom: 16 }}
      />
      <Title level={3}>利润测算</Title>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={8}>
          <Card title={<><CalculatorOutlined /> 成本输入</>}>
            <Form
              form={form}
              layout="vertical"
              onFinish={onFinish}
              initialValues={{ selling_price: 25.99, unit_cost: 6.5, category: 'pet_supplies', market: 'US' }}
            >
              <Form.Item name="selling_price" label="售价 (USD)" rules={[{ required: true, type: 'number', min: 0.01 }]}>
                <InputNumber prefix="$" style={{ width: '100%' }} min={0.01} step={0.01} />
              </Form.Item>
              <Form.Item name="unit_cost" label="产品成本 (USD)" rules={[{ required: true, type: 'number', min: 0 }]}>
                <InputNumber prefix="$" style={{ width: '100%' }} min={0} step={0.01} />
              </Form.Item>
              <Form.Item name="category" label="商品类目">
                <Select options={[
                  { value: 'pet_supplies', label: '宠物用品' },
                  { value: 'electronics', label: '电子产品' },
                  { value: 'home_kitchen', label: '家居厨房' },
                  { value: 'beauty', label: '美妆个护' },
                  { value: 'sports', label: '运动户外' },
                  { value: 'general', label: '综合类目' },
                ]} />
              </Form.Item>
              <Form.Item name="market" label="目标市场">
                <Select options={[
                  { value: 'US', label: '美国站' },
                  { value: 'UK', label: '英国站' },
                  { value: 'DE', label: '德国站' },
                  { value: 'JP', label: '日本站' },
                  { value: 'CA', label: '加拿大站' },
                ]} />
              </Form.Item>
              <Button type="primary" htmlType="submit" block loading={loading} icon={<RiseOutlined />}>
                计算利润
              </Button>
            </Form>
          </Card>

          <Card title={<><HistoryOutlined /> 测算历史</>} style={{ marginTop: 24 }}>
            {history.length ? (
              <Table size="small" columns={historyColumns} dataSource={history} rowKey="id" pagination={{ pageSize: 5 }} />
            ) : (
              <Empty description="暂无测算记录" />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          {!result && (
            <Card>
              <Empty description="输入成本参数后点击「计算利润」查看结果" style={{ padding: 60 }} />
            </Card>
          )}

          {result && (
            <>
              {bestScenario && (
                <div
                  style={{
                    background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
                    border: '1px solid #bfdbfe',
                    borderRadius: 16,
                    padding: '18px 22px',
                    marginBottom: 24,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 14,
                  }}
                >
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 800, color: '#64748b', marginBottom: 5 }}>当前最佳 ROI 情景</div>
                    <div style={{ fontSize: 22, fontWeight: 900, color: '#1e40af' }}>
                      {bestScenario.name}情景 · ROI {bestScenario.data.ROI}% · 月毛利 USD {bestScenario.data['月毛利']}
                    </div>
                  </div>
                  <div style={{ background: '#fff', borderRadius: 12, padding: '12px 18px', fontSize: 14, fontWeight: 800, color: '#1e40af' }}>
                    {bestScenario.name === '保守' && '优先降本控风险，验证最小订单模型'}
                    {bestScenario.name === '中性' && '按中性节奏备货，稳步扩大投放'}
                    {bestScenario.name === '乐观' && '积极备货并加大广告，抢占旺季窗口'}
                  </div>
                </div>
              )}

              <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={12} md={6}>
                  <Card>
                    <Statistic title="售价" value={result.selling_price} prefix="$" precision={2} />
                  </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                  <Card>
                    <Statistic title="单件总成本" value={result.total_cost_per_unit} prefix="$" precision={2} />
                  </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                  <Card>
                    <Statistic
                      title="单件毛利"
                      value={result.gross_profit_per_unit}
                      prefix="$"
                      precision={2}
                      valueStyle={{ color: result.gross_profit_per_unit >= 0 ? '#16a34a' : '#dc2626' }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                  <Card>
                    <Statistic
                      title="毛利率"
                      value={result.gross_margin_pct}
                      prefix={<PercentageOutlined />}
                      valueStyle={{ color: result.gross_margin >= 0.2 ? '#16a34a' : '#f97316' }}
                    />
                  </Card>
                </Col>
              </Row>

              <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={12}>
                  <Card title="单件成本明细">
                    <Descriptions column={1} size="small" bordered>
                      {Object.entries(result.cost_breakdown).map(([k, v]) => (
                        <Descriptions.Item
                          key={k}
                          label={
                            <Space>
                              <span style={{ width: 10, height: 10, borderRadius: '50%', background: COST_COLORS[k] || '#1976d2', display: 'inline-block' }} />
                              {k}
                            </Space>
                          }
                        >
                          ${v.toFixed(2)} ({result.cost_breakdown_pct[k]})
                        </Descriptions.Item>
                      ))}
                      <Descriptions.Item label="总成本">
                        <Text strong>${result.total_cost_per_unit.toFixed(2)}</Text>
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card title="成本结构">
                    {costBarOption && <ReactECharts option={costBarOption} style={{ height: 300 }} />}
                  </Card>
                </Col>
              </Row>

              <Card title="ROI 情景分析" style={{ marginBottom: 24 }}>
                <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                  <Col xs={24} sm={8}>
                    <Card size="small" style={{ textAlign: 'center', borderColor: '#dc2626' }}>
                      <Text strong>保守</Text>
                      <div style={{ fontSize: 28, fontWeight: 900, color: roiColor(result.roi_scenarios['保守'].ROI) }}>
                        {result.roi_scenarios['保守'].ROI}%
                      </div>
                      <Text type="secondary">月销量 {result.roi_scenarios['保守']['月销量']}</Text>
                    </Card>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Card size="small" style={{ textAlign: 'center', borderColor: '#f97316' }}>
                      <Text strong>中性</Text>
                      <div style={{ fontSize: 28, fontWeight: 900, color: roiColor(result.roi_scenarios['中性'].ROI) }}>
                        {result.roi_scenarios['中性'].ROI}%
                      </div>
                      <Text type="secondary">月销量 {result.roi_scenarios['中性']['月销量']}</Text>
                    </Card>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Card size="small" style={{ textAlign: 'center', borderColor: '#16a34a' }}>
                      <Text strong>乐观</Text>
                      <div style={{ fontSize: 28, fontWeight: 900, color: roiColor(result.roi_scenarios['乐观'].ROI) }}>
                        {result.roi_scenarios['乐观'].ROI}%
                      </div>
                      <Text type="secondary">月销量 {result.roi_scenarios['乐观']['月销量']}</Text>
                    </Card>
                  </Col>
                </Row>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>当前月销量：{volume} 件</Text>
                  <Slider min={100} max={600} step={10} value={volume} onChange={setVolume} />
                </div>
                {roiTrendOption && <ReactECharts option={roiTrendOption} style={{ height: 360 }} />}
              </Card>

              <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={12}>
                  <Card title={<><WalletOutlined /> 利润优化模拟器</>}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Text>产品成本优化 (-${costReduction.toFixed(2)})</Text>
                        <Slider min={0} max={2} step={0.1} value={costReduction} onChange={setCostReduction} />
                      </div>
                      <div>
                        <Text>广告费用优化 (-${adReduction.toFixed(2)})</Text>
                        <Slider min={0} max={1} step={0.05} value={adReduction} onChange={setAdReduction} />
                      </div>
                      <div>
                        <Text>FBA 费用优化 (-${fbaReduction.toFixed(2)})</Text>
                        <Slider min={0} max={1} step={0.05} value={fbaReduction} onChange={setFbaReduction} />
                      </div>
                      <div>
                        <Text>售价提升 (+${priceIncrease.toFixed(2)})</Text>
                        <Slider min={0} max={5} step={0.1} value={priceIncrease} onChange={setPriceIncrease} />
                      </div>
                    </Space>
                    <div style={{ marginTop: 16, padding: 16, background: '#f8fafc', borderRadius: 12 }}>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Text type="secondary">优化后总成本</Text>
                          <div style={{ fontSize: 18, fontWeight: 700 }}>${simulatedResult?.totalCost.toFixed(2)}</div>
                        </Col>
                        <Col span={8}>
                          <Text type="secondary">优化后毛利</Text>
                          <div style={{ fontSize: 18, fontWeight: 700, color: '#16a34a' }}>${simulatedResult?.grossProfit.toFixed(2)}</div>
                        </Col>
                        <Col span={8}>
                          <Text type="secondary">优化后毛利率</Text>
                          <div style={{ fontSize: 18, fontWeight: 700, color: '#1976d2' }}>{simulatedResult?.marginPct}</div>
                        </Col>
                      </Row>
                    </div>
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card title={<><ArrowRightOutlined /> 优化建议</>}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {result.suggestions.map((s: string, i: number) => (
                        <div key={i} style={{ padding: 12, background: '#f8fafc', borderRadius: 8, borderLeft: '4px solid #1976d2' }}>
                          <Text>{s}</Text>
                        </div>
                      ))}
                    </Space>
                    <div style={{ marginTop: 16 }}>
                      <Tag color="blue">盈亏平衡：{result.breakeven_units ?? '-'} 件</Tag>
                    </div>
                  </Card>
                </Col>
              </Row>

              <Space>
                <Button icon={<DownloadOutlined />} onClick={() => alert('导出功能开发中')}>
                  导出测算表
                </Button>
                <Button icon={<SaveOutlined />} onClick={() => alert('已保存到历史记录')}>
                  保存方案
                </Button>
              </Space>
            </>
          )}
        </Col>
      </Row>
    </div>
  )
}
