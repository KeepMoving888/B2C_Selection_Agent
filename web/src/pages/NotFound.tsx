import { Button, Empty, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'

const { Title } = Typography

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div style={{ textAlign: 'center', padding: '80px 0' }}>
      <Empty description={false} />
      <Title level={2} style={{ marginTop: 24 }}>
        404
      </Title>
      <Title level={4} type="secondary">
        页面不存在
      </Title>
      <Button type="primary" onClick={() => navigate('/dashboard')}>
        返回仪表板
      </Button>
    </div>
  )
}
