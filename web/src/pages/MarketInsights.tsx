import { Breadcrumb, Card, Typography } from 'antd'
import { Link } from 'react-router-dom'

const { Title } = Typography

export default function MarketInsights() {
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
      <Card>市场趋势与竞品分析页面开发中，后续将支持类目趋势、竞品监控与机会识别。</Card>
    </div>
  )
}
