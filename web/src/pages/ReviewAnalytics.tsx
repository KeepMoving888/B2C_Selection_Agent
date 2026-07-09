import { Breadcrumb, Card, Typography } from 'antd'
import { Link } from 'react-router-dom'

const { Title } = Typography

export default function ReviewAnalytics() {
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
      <Card>评论情感分析与关键词提取页面开发中，后续将支持词云、痛点识别与改进建议。</Card>
    </div>
  )
}
