import {
  BellOutlined,
  DatabaseOutlined,
  GlobalOutlined,
  KeyOutlined,
  SunOutlined,
  UserOutlined,
} from '@ant-design/icons'
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import { setPageTitle } from '../store/slices/uiSlice'
import { toggleTheme } from '../store/slices/uiSlice'
import type { RootState } from '../store'

const { Title, Text } = Typography

interface AppSettings {
  weights: {
    profit: number
    trend: number
    competition: number
    review: number
  }
  thresholds: {
    recommend: number
    risky: number
  }
  notifications: {
    email: boolean
    browser: boolean
    weekly: boolean
    riskAlert: boolean
  }
  apiKey: string
  exportFormat: 'json' | 'csv' | 'excel'
}

const defaultSettings: AppSettings = {
  weights: { profit: 50, trend: 25, competition: 20, review: 15 },
  thresholds: { recommend: 70, risky: 50 },
  notifications: { email: true, browser: true, weekly: true, riskAlert: true },
  apiKey: '',
  exportFormat: 'json',
}

export default function Settings() {
  const dispatch = useDispatch()
  const { theme } = useSelector((state: RootState) => state.ui)
  const [settings, setSettings] = useState<AppSettings>(defaultSettings)

  useEffect(() => {
    dispatch(setPageTitle('设置'))
    const saved = localStorage.getItem('app_settings')
    if (saved) {
      try {
        setSettings({ ...defaultSettings, ...JSON.parse(saved) })
      } catch {
        // ignore
      }
    }
  }, [dispatch])

  const saveSettings = (next: AppSettings) => {
    setSettings(next)
    localStorage.setItem('app_settings', JSON.stringify(next))
    message.success('设置已保存')
  }

  const regenerateApiKey = () => {
    const key = 'ps_' + Math.random().toString(36).slice(2) + Date.now().toString(36)
    saveSettings({ ...settings, apiKey: key })
  }

  const tabItems = useMemo(() => [
    {
      key: 'account',
      label: (
        <span>
          <UserOutlined /> 账户管理
        </span>
      ),
      children: (
        <Card title="用户账户">
          <Form layout="vertical">
            <Form.Item label="用户名">
              <Input defaultValue="admin" disabled />
            </Form.Item>
            <Form.Item label="邮箱">
              <Input defaultValue="admin@example.com" />
            </Form.Item>
            <Form.Item label="角色">
              <Input defaultValue="管理员" disabled />
            </Form.Item>
            <Form.Item>
              <Button type="primary">保存账户信息</Button>
            </Form.Item>
          </Form>
          <Divider />
          <Text strong>密码修改</Text>
          <Form layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item label="当前密码">
              <Input.Password />
            </Form.Item>
            <Form.Item label="新密码">
              <Input.Password />
            </Form.Item>
            <Form.Item label="确认新密码">
              <Input.Password />
            </Form.Item>
            <Form.Item>
              <Button type="primary">修改密码</Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'analysis',
      label: (
        <span>
          <DatabaseOutlined /> 分析参数
        </span>
      ),
      children: (
        <Card title="评分权重配置">
          <Text type="secondary" style={{ marginBottom: 24, display: 'block' }}>
            调整各维度在综合评分中的权重，权重总和建议为 100。
          </Text>
          <Row gutter={[24, 24]}>
            <Col xs={24} sm={12}>
              <Form.Item label="利润空间权重">
                <InputNumber
                  min={0}
                  max={100}
                  value={settings.weights.profit}
                  onChange={(v) => saveSettings({ ...settings, weights: { ...settings.weights, profit: v || 0 } })}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="趋势热度权重">
                <InputNumber
                  min={0}
                  max={100}
                  value={settings.weights.trend}
                  onChange={(v) => saveSettings({ ...settings, weights: { ...settings.weights, trend: v || 0 } })}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="竞争强度权重">
                <InputNumber
                  min={0}
                  max={100}
                  value={settings.weights.competition}
                  onChange={(v) => saveSettings({ ...settings, weights: { ...settings.weights, competition: v || 0 } })}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="评论洞察权重">
                <InputNumber
                  min={0}
                  max={100}
                  value={settings.weights.review}
                  onChange={(v) => saveSettings({ ...settings, weights: { ...settings.weights, review: v || 0 } })}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>
          <Divider />
          <Text strong>阈值设置</Text>
          <Row gutter={[24, 24]} style={{ marginTop: 16 }}>
            <Col xs={24} sm={12}>
              <Form.Item label="推荐商品分数线">
                <InputNumber
                  min={0}
                  max={100}
                  value={settings.thresholds.recommend}
                  onChange={(v) => saveSettings({ ...settings, thresholds: { ...settings.thresholds, recommend: v || 0 } })}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="高风险商品分数线">
                <InputNumber
                  min={0}
                  max={100}
                  value={settings.thresholds.risky}
                  onChange={(v) => saveSettings({ ...settings, thresholds: { ...settings.thresholds, risky: v || 0 } })}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>
      ),
    },
    {
      key: 'notifications',
      label: (
        <span>
          <BellOutlined /> 通知设置
        </span>
      ),
      children: (
        <Card title="通知偏好">
          <Space direction="vertical" style={{ width: '100%' }}>
            {[
              { key: 'email', title: '邮件通知', desc: '分析完成后发送邮件提醒' },
              { key: 'browser', title: '浏览器通知', desc: '启用桌面推送' },
              { key: 'weekly', title: '周报', desc: '每周一发送分析周报' },
              { key: 'riskAlert', title: '风险预警', desc: '高风险商品自动告警' },
            ].map((item) => (
              <div key={item.key} style={{ display: 'flex', justifyContent: 'space-between', padding: 12, background: '#f8fafc', borderRadius: 8 }}>
                <div>
                  <Text strong>{item.title}</Text>
                  <div><Text type="secondary">{item.desc}</Text></div>
                </div>
                <Switch
                  checked={settings.notifications[item.key as keyof AppSettings['notifications']]}
                  onChange={(v) => saveSettings({ ...settings, notifications: { ...settings.notifications, [item.key]: v } })}
                />
              </div>
            ))}
          </Space>
        </Card>
      ),
    },
    {
      key: 'data',
      label: (
        <span>
          <GlobalOutlined /> 数据导入/导出
        </span>
      ),
      children: (
        <Card title="数据管理">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Card size="small" title="导出数据">
              <Text type="secondary">导出所有分析报告和测算记录到本地文件</Text>
              <div style={{ marginTop: 12 }}>
                <Select
                  value={settings.exportFormat}
                  onChange={(v) => saveSettings({ ...settings, exportFormat: v })}
                  style={{ width: 160, marginRight: 12 }}
                >
                  <Select.Option value="json">JSON</Select.Option>
                  <Select.Option value="csv">CSV</Select.Option>
                  <Select.Option value="excel">Excel</Select.Option>
                </Select>
                <Button type="primary">导出数据</Button>
              </div>
            </Card>
            <Card size="small" title="导入数据">
              <Text type="secondary">从历史备份文件恢复报告数据</Text>
              <div style={{ marginTop: 12 }}>
                <Input type="file" style={{ width: 300, marginRight: 12 }} />
                <Button>导入数据</Button>
              </div>
            </Card>
            <Card size="small" title="清空本地缓存">
              <Text type="secondary">清除浏览器本地保存的测算历史和设置</Text>
              <div style={{ marginTop: 12 }}>
                <Button danger onClick={() => { localStorage.clear(); message.success('本地缓存已清空'); }}>
                  清空缓存
                </Button>
              </div>
            </Card>
          </Space>
        </Card>
      ),
    },
    {
      key: 'api',
      label: (
        <span>
          <KeyOutlined /> API 密钥
        </span>
      ),
      children: (
        <Card title="API 密钥管理">
          <Text type="secondary">用于第三方系统接入选品决策 API</Text>
          <Form layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item label="当前密钥">
              <Space.Compact style={{ width: '100%' }}>
                <Input.Password value={settings.apiKey} readOnly placeholder="点击生成密钥" />
                <Button onClick={regenerateApiKey}>重新生成</Button>
              </Space.Compact>
            </Form.Item>
            <Form.Item label="API 文档">
              <Tag color="blue">POST /api/v1/analysis</Tag>
              <Tag color="blue">POST /api/v1/profit/calculate</Tag>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'theme',
      label: (
        <span>
          <SunOutlined /> 主题切换
        </span>
      ),
      children: (
        <Card title="外观主题">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, background: '#f8fafc', borderRadius: 8 }}>
            <div>
              <Text strong>深色模式</Text>
              <div><Text type="secondary">切换系统浅色/深色主题</Text></div>
            </div>
            <Switch checked={theme === 'dark'} onChange={() => dispatch(toggleTheme())} checkedChildren="深色" unCheckedChildren="浅色" />
          </div>
        </Card>
      ),
    },
  ], [settings, theme])

  return (
    <div>
      <Breadcrumb
        items={[
          { title: <Link to="/dashboard">首页</Link> },
          { title: '设置' },
        ]}
        style={{ marginBottom: 16 }}
      />
      <Title level={3}>系统设置</Title>

      <Tabs
        defaultActiveKey="account"
        items={tabItems}
      />
    </div>
  )
}
