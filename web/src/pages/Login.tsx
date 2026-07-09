import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Card, Checkbox, Form, Input, Typography } from 'antd'
import { useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { setToken } from '../store/slices/authSlice'

const { Title, Text } = Typography

export default function Login() {
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const onFinish = (values: { username: string; password: string; remember: boolean }) => {
    // 演示登录：直接写入 token，实际应调用 authApi.login
    dispatch(setToken(`demo-token-${values.username}`))
    navigate('/dashboard')
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
      }}
    >
      <Card style={{ width: 420, borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.15)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 8,
              background: '#1976d2',
              color: '#fff',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
              fontWeight: 800,
              marginBottom: 16,
            }}
          >
            PS
          </div>
          <Title level={3} style={{ margin: 0 }}>
            选品决策系统
          </Title>
          <Text type="secondary">Product Selection Decision System</Text>
        </div>
        <Form name="login" initialValues={{ remember: true }} onFinish={onFinish} size="large">
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Form.Item name="remember" valuePropName="checked" noStyle>
              <Checkbox>记住我</Checkbox>
            </Form.Item>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
