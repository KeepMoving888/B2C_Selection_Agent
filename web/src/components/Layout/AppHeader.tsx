import {
  BellOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MoonOutlined,
  SearchOutlined,
  SunOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Avatar, Badge, Dropdown, Input, Layout, Space, theme as antTheme, Typography } from 'antd';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { toggleSidebar, toggleTheme } from '../../store/slices/uiSlice';
import type { RootState } from '../../store';

const { Header } = Layout;
const { Text } = Typography;

export default function AppHeader() {
  const dispatch = useDispatch();
  const { sidebarCollapsed, theme } = useSelector((state: RootState) => state.ui);
  const { token } = antTheme.useToken();

  const isDark = theme === 'dark';

  const userMenuItems = [
    { key: 'profile', label: <Link to="/settings">个人设置</Link> },
    { key: 'help', label: '帮助中心' },
    { type: 'divider' as const },
    { key: 'logout', label: '退出登录', danger: true },
  ];

  return (
    <Header
      style={{
        padding: '0 24px',
        background: token.colorBgContainer,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <Space size={16}>
        <span
          onClick={() => dispatch(toggleSidebar())}
          style={{ cursor: 'pointer', fontSize: 18, color: token.colorText }}
        >
          {sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </span>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              background: token.colorPrimary,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 800,
            }}
          >
            PS
          </div>
          <Text strong style={{ fontSize: 18, color: token.colorText }}>
            选品决策系统
          </Text>
        </Link>
      </Space>

      <Space size={24}>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索商品、报告..."
          style={{ width: 320, borderRadius: 20, display: 'none' }}
          className="global-search"
        />
        <span
          onClick={() => dispatch(toggleTheme())}
          style={{ cursor: 'pointer', fontSize: 18, color: token.colorText }}
        >
          {isDark ? <SunOutlined /> : <MoonOutlined />}
        </span>
        <Badge count={3} size="small">
          <BellOutlined style={{ fontSize: 18, color: token.colorText, cursor: 'pointer' }} />
        </Badge>
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer' }}>
            <Avatar icon={<UserOutlined />} size="small" />
            <Text style={{ display: 'none' }} className="header-username">
              Admin
            </Text>
          </Space>
        </Dropdown>
      </Space>
    </Header>
  );
}
