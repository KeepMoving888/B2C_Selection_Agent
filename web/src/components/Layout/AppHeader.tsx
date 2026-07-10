import {
  BellOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Avatar, Badge, Dropdown, Input, Layout, Space, theme as antTheme, Typography } from 'antd';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { toggleSidebar } from '../../store/slices/uiSlice';
import type { RootState } from '../../store';

const { Header } = Layout;
const { Text } = Typography;

export default function AppHeader() {
  const dispatch = useDispatch();
  const { sidebarCollapsed } = useSelector((state: RootState) => state.ui);
  const { token } = antTheme.useToken();

  const isDark = false;

  const userMenuItems = [
    { key: 'profile', label: <Link to="/settings">个人设置</Link> },
    { key: 'help', label: '帮助中心' },
    { type: 'divider' as const },
    { key: 'logout', label: '退出登录', danger: true },
  ];

  return (
    <Header
      style={{
        padding: '0 28px',
        background: isDark ? 'rgba(15, 23, 42, 0.85)' : 'rgba(255, 255, 255, 0.85)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: `1px solid ${isDark ? 'rgba(51, 65, 85, 0.6)' : 'rgba(226, 232, 240, 0.8)'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 1px 3px rgba(15, 23, 42, 0.04)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: 64,
      }}
    >
      <Space size={18}>
        <span
          onClick={() => dispatch(toggleSidebar())}
          style={{
            cursor: 'pointer',
            fontSize: 18,
            color: token.colorText,
            width: 36,
            height: 36,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 10,
            background: isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(241, 245, 249, 0.8)',
            transition: 'background 0.2s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = isDark ? 'rgba(51, 65, 85, 0.7)' : '#e2e8f0')}
          onMouseLeave={(e) => (e.currentTarget.style.background = isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(241, 245, 249, 0.8)')}
        >
          {sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </span>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 900,
              fontSize: 14,
              boxShadow: '0 4px 12px rgba(29, 78, 216, 0.25)',
            }}
          >
            PS
          </div>
          <div>
            <Text strong style={{ fontSize: 18, color: token.colorText, letterSpacing: '-0.02em', display: 'block', lineHeight: 1.2 }}>
              选品决策系统
            </Text>
            <Text style={{ fontSize: 11, color: token.colorTextTertiary, fontWeight: 600, letterSpacing: '0.02em' }}>
              Product Selection
            </Text>
          </div>
        </Link>
      </Space>

      <Space size={20}>
        <Input
          prefix={<SearchOutlined style={{ color: token.colorTextTertiary }} />}
          placeholder="搜索商品、报告..."
          style={{
            width: 300,
            borderRadius: 24,
            background: isDark ? 'rgba(30, 41, 59, 0.6)' : 'rgba(241, 245, 249, 0.8)',
            border: 'none',
            boxShadow: 'none',
          }}
          className="global-search"
        />
        <Badge count={3} size="small" style={{ cursor: 'pointer' }}>
          <span
            style={{
              fontSize: 18,
              color: token.colorText,
              width: 36,
              height: 36,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 10,
              background: isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(241, 245, 249, 0.8)',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = isDark ? 'rgba(51, 65, 85, 0.7)' : '#e2e8f0')}
            onMouseLeave={(e) => (e.currentTarget.style.background = isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(241, 245, 249, 0.8)')}
          >
            <BellOutlined />
          </span>
        </Badge>
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer', padding: '4px 12px 4px 4px', borderRadius: 24, background: isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(241, 245, 249, 0.8)' }}>
            <Avatar icon={<UserOutlined />} size="small" style={{ background: 'linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%)' }} />
            <Text style={{ fontSize: 13, fontWeight: 700, color: token.colorText }} className="header-username">
              Admin
            </Text>
          </Space>
        </Dropdown>
      </Space>
    </Header>
  );
}
