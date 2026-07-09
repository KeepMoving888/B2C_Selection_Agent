import { Breadcrumb, Card, Typography } from 'antd'
import { Link } from 'react-router-dom'

const { Title } = Typography

export default function ReportCenter() {
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
      <Card>报告管理与导出页面开发中，后续将支持报告列表、详情查看、批量导出与分享。</Card>
    </div>
  )
}
