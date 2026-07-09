import { Breadcrumb, Card, Typography } from 'antd'
import { Link } from 'react-router-dom'

const { Title } = Typography

export default function ProfitCalculator() {
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
      <Card>利润测算工具页面开发中，后续将支持成本输入、ROI 情景分析与优化建议。</Card>
    </div>
  )
}
