import { Breadcrumb, Card, Switch, Typography } from 'antd'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import { toggleTheme } from '../store/slices/uiSlice'
import type { RootState } from '../store'

const { Title } = Typography

export default function Settings() {
  const dispatch = useDispatch()
  const { theme } = useSelector((state: RootState) => state.ui)

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
      <Card title="外观">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>深色模式</span>
          <Switch checked={theme === 'dark'} onChange={() => dispatch(toggleTheme())} />
        </div>
      </Card>
    </div>
  )
}
