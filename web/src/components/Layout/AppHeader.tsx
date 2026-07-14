import {
  BellOutlined,
  MenuFoldOutlined,
  MenuOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Avatar, Badge, Dropdown, Input, Layout, Space, theme as antTheme, Typography } from 'antd';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { useMobile } from '../../hooks/useMobile';
import { toggleMobileMenu, toggleSidebar } from '../../store/slices/uiSlice';
import type { RootState } from '../../store';

const { Header } = Layout;
const { Text } = Typography;

export default function AppHeader() {
  const dispatch = useDispatch();
  const { sidebarCollapsed } = useSelector((state: RootState) => state.ui);
  const { token } = antTheme.useToken();
  const isMobile = useMobile();

  const isDark = false;

  const handleLogoClick = () => {
    // 重置搜索与报告状态，回到带向导的初始首页
    localStorage.removeItem('current_report');
    localStorage.setItem('last_search', JSON.stringify({ keyword: '', market: 'US', budget: '5000-10000' }));
    window.location.href = `${window.location.origin}${window.location.pathname}#/dashboard`;
  };

  const userMenuItems = [
    { key: 'profile', label: <Link to="/settings">个人设置</Link> },
    { key: 'help', label: '帮助中心' },
    { type: 'divider' as const },
    { key: 'logout', label: '退出登录', danger: true },
  ];

  return (
    <Header
      style={{
        padding: isMobile ? '0 16px' : '0 28px',
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
        height: 68,
        lineHeight: 'normal',
        overflow: 'visible',
      }}
    >
      <Space size={18}>
        <span
          onClick={() => dispatch(isMobile ? toggleMobileMenu() : toggleSidebar())}
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
          {isMobile ? <MenuOutlined /> : sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </span>
        <div onClick={handleLogoClick} style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}>
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
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <span style={{ fontSize: 17, fontWeight: 800, color: token.colorText, letterSpacing: '-0.02em', lineHeight: 1.25, display: 'block' }}>
              选品决策系统
            </span>
            <span style={{ fontSize: 11, color: token.colorTextTertiary, fontWeight: 600, letterSpacing: '0.04em', lineHeight: 1.2, display: 'block', marginTop: 1 }}>
              Product Selection
            </span>
          </div>
        </div>
      </Space>

      <Space size={isMobile ? 12 : 20}>
        {!isMobile && (
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
        )}
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
            {!isMobile && (
              <Text style={{ fontSize: 13, fontWeight: 700, color: token.colorText }} className="header-username">
                Admin
              </Text>
            )}
          </Space>
        </Dropdown>
      </Space>
    </Header>
  );
}
