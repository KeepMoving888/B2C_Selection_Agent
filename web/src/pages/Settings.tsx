import {
  BellOutlined,
  CopyOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  GlobalOutlined,
  KeyOutlined,
  PlusOutlined,
  UserOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useDispatch } from 'react-redux'
import { setPageTitle } from '../store/slices/uiSlice'

const { Text, Title, Paragraph } = Typography

interface ApiKey {
  id: string
  name: string
  key: string
  scopes: string[]
  createdAt: string
  lastUsedAt?: string
  enabled: boolean
}

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
  apiKeys: ApiKey[]
  exportFormat: 'json' | 'csv' | 'excel'
}

const defaultSettings: AppSettings = {
  weights: { profit: 30, trend: 25, competition: 25, review: 20 },
  thresholds: { recommend: 70, risky: 50 },
  notifications: { email: true, browser: true, weekly: true, riskAlert: true },
  apiKeys: [],
  exportFormat: 'json',
}

const API_SCOPES = [
  { value: 'analysis:read', label: '读取分析报告', desc: 'GET /api/v1/analysis' },
  { value: 'profit:read', label: '读取利润测算', desc: 'GET /api/v1/profit/calculate' },
  { value: 'market:read', label: '读取市场数据', desc: 'GET /api/v1/market/competitors' },
  { value: 'report:write', label: '提交分析任务', desc: 'POST /api/v1/analysis' },
  { value: 'admin', label: '全部权限', desc: '访问所有接口' },
]

function generateApiKey(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let rand = ''
  for (let i = 0; i < 32; i++) {
    rand += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return `ps_${rand}`
}

function maskKey(key: string): string {
  if (key.length <= 12) return key
  return `${key.slice(0, 8)}...${key.slice(-4)}`
}

export default function Settings() {
  const dispatch = useDispatch()
  const [settings, setSettings] = useState<AppSettings>(defaultSettings)
  const [apiKeyModalOpen, setApiKeyModalOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyScopes, setNewKeyScopes] = useState<string[]>(['analysis:read', 'profit:read'])
  const [createdKey, setCreatedKey] = useState<ApiKey | null>(null)
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({})

  useEffect(() => {
    dispatch(setPageTitle('设置'))
    const saved = localStorage.getItem('app_settings')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // 迁移旧版单个 apiKey 到多密钥列表
        if (parsed.apiKey && !parsed.apiKeys) {
          parsed.apiKeys = [{
            id: `key_${Date.now()}`,
            name: '默认密钥',
            key: parsed.apiKey,
            scopes: ['analysis:read', 'profit:read', 'market:read', 'report:write', 'admin'],
            createdAt: new Date().toISOString(),
            enabled: true,
          }]
          delete parsed.apiKey
        }
        setSettings({ ...defaultSettings, ...parsed })
      } catch {
        // ignore
      }
    }
  }, [dispatch])

  const saveSettings = (next: AppSettings) => {
    setSettings(next)
    localStorage.setItem('app_settings', JSON.stringify(next))
  }

  const createApiKey = useCallback(() => {
    if (!newKeyName.trim()) {
      message.error('请输入密钥名称')
      return
    }
    if (newKeyScopes.length === 0) {
      message.error('请选择至少一个权限')
      return
    }
    const key: ApiKey = {
      id: `key_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      name: newKeyName.trim(),
      key: generateApiKey(),
      scopes: newKeyScopes,
      createdAt: new Date().toISOString(),
      enabled: true,
    }
    const next = { ...settings, apiKeys: [key, ...settings.apiKeys] }
    saveSettings(next)
    setCreatedKey(key)
    setNewKeyName('')
    setNewKeyScopes(['analysis:read', 'profit:read'])
  }, [newKeyName, newKeyScopes, settings])

  const deleteApiKey = useCallback((id: string) => {
    const next = { ...settings, apiKeys: settings.apiKeys.filter((k) => k.id !== id) }
    saveSettings(next)
    message.success('密钥已删除')
  }, [settings])

  const toggleApiKey = useCallback((id: string) => {
    const next = {
      ...settings,
      apiKeys: settings.apiKeys.map((k) => k.id === id ? { ...k, enabled: !k.enabled } : k),
    }
    saveSettings(next)
    message.success('状态已更新')
  }, [settings])

  const copyToClipboard = useCallback((text: string) => {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => message.success('已复制到剪贴板'))
    } else {
      message.info(text)
    }
  }, [])

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
          <Alert
            message="第三方系统接入"
            description="创建 API 密钥后，其他软件可通过 HTTP 请求调用选品决策接口。请妥善保管密钥，避免泄露。"
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => { setCreatedKey(null); setApiKeyModalOpen(true) }}>
              创建 API 密钥
            </Button>
          </Space>
          <Table
            rowKey="id"
            dataSource={settings.apiKeys}
            pagination={false}
            columns={[
              { title: '名称', dataIndex: 'name', key: 'name' },
              {
                title: '密钥',
                dataIndex: 'key',
                key: 'key',
                render: (_: string, record: ApiKey) => (
                  <Space>
                    <Text code copyable={{ text: record.key, onCopy: () => message.success('已复制') }}>
                      {visibleKeys[record.id] ? record.key : maskKey(record.key)}
                    </Text>
                    <Button
                      type="text"
                      size="small"
                      icon={visibleKeys[record.id] ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                      onClick={() => setVisibleKeys((prev) => ({ ...prev, [record.id]: !prev[record.id] }))}
                    />
                  </Space>
                ),
              },
              {
                title: '权限范围',
                dataIndex: 'scopes',
                key: 'scopes',
                render: (scopes: string[]) => (
                  <Space wrap>
                    {scopes.map((s) => {
                      const scope = API_SCOPES.find((item) => item.value === s)
                      return <Tag key={s} color={s === 'admin' ? 'red' : 'blue'}>{scope?.label || s}</Tag>
                    })}
                  </Space>
                ),
              },
              { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', render: (v: string) => new Date(v).toLocaleString() },
              {
                title: '状态',
                dataIndex: 'enabled',
                key: 'enabled',
                render: (enabled: boolean) => <Badge status={enabled ? 'success' : 'default'} text={enabled ? '启用中' : '已禁用'} />,
              },
              {
                title: '操作',
                key: 'action',
                render: (_: unknown, record: ApiKey) => (
                  <Space size="small">
                    <Tooltip title="复制密钥">
                      <Button type="text" icon={<CopyOutlined />} onClick={() => copyToClipboard(record.key)} />
                    </Tooltip>
                    <Button type="text" onClick={() => toggleApiKey(record.id)}>
                      {record.enabled ? '禁用' : '启用'}
                    </Button>
                    <Button type="text" danger icon={<DeleteOutlined />} onClick={() => deleteApiKey(record.id)}>
                      删除
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
          <Divider />
          <Title level={5}>API 接入文档</Title>
          <Paragraph type="secondary">Base URL: <Text code>https://api.xuanpin.example.com</Text></Paragraph>
          <Descriptions bordered size="small" column={1} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="认证方式">请求头携带 <Text code>Authorization: Bearer &lt;your_api_key&gt;</Text></Descriptions.Item>
            <Descriptions.Item label="Content-Type"><Text code>application/json</Text></Descriptions.Item>
            <Descriptions.Item label="Rate Limit">100 次 / 分钟</Descriptions.Item>
          </Descriptions>
          <Card size="small" title="示例：提交选品分析任务" style={{ background: '#f8fafc' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 12 }}>
{`curl -X POST https://api.xuanpin.example.com/api/v1/analysis \\
  -H "Authorization: Bearer ${settings.apiKeys[0]?.key || 'your_api_key'}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "keyword": "cat toy",
    "market": "US",
    "budget": "$5,000 - $10,000"
  }'`}
            </pre>
          </Card>

          <Modal
            title="创建 API 密钥"
            open={apiKeyModalOpen}
            onOk={() => { createApiKey(); setApiKeyModalOpen(false) }}
            onCancel={() => setApiKeyModalOpen(false)}
            okText="创建"
            cancelText="取消"
          >
            <Form layout="vertical">
              <Form.Item label="密钥名称" required>
                <Input placeholder="例如：ERP 系统接入" value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} maxLength={50} />
              </Form.Item>
              <Form.Item label="权限范围" required>
                <Select
                  mode="multiple"
                  placeholder="选择权限"
                  value={newKeyScopes}
                  onChange={setNewKeyScopes}
                  options={API_SCOPES.map((s) => ({ value: s.value, label: `${s.label} · ${s.desc}` }))}
                />
              </Form.Item>
            </Form>
          </Modal>

          <Modal
            title="密钥创建成功"
            open={!!createdKey}
            onOk={() => setCreatedKey(null)}
            onCancel={() => setCreatedKey(null)}
            okText="知道了"
            cancelButtonProps={{ style: { display: 'none' } }}
          >
            <Alert
              message="请立即复制以下密钥，关闭弹窗后将无法再次查看完整密钥"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            {createdKey && (
              <Input.Password
                value={createdKey.key}
                readOnly
                addonAfter={<Button type="text" icon={<CopyOutlined />} onClick={() => copyToClipboard(createdKey.key)}>复制</Button>}
              />
            )}
          </Modal>
        </Card>
      ),
    },
  ], [settings, visibleKeys, apiKeyModalOpen, newKeyName, newKeyScopes, createdKey, createApiKey, deleteApiKey, toggleApiKey, copyToClipboard])

  return (
    <div className="page-container">
      <div className="page-header">系统设置</div>
      <div className="page-subtitle">管理账户、分析参数、通知偏好与数据导出</div>

      <Tabs
        defaultActiveKey="account"
        items={tabItems}
      />
    </div>
  )
}
