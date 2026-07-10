import {
  AuditOutlined,
  BarChartOutlined,
  CarryOutOutlined,
  CommentOutlined,
  DashboardOutlined,
  DollarOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  SettingOutlined,
  ShopOutlined,
  StockOutlined,
} from '@ant-design/icons';
import { Layout, Menu, theme as antTheme } from 'antd';
import { useSelector } from 'react-redux';
import { useLocation, useNavigate } from 'react-router-dom';
import type { RootState } from '../../store';

const { Sider } = Layout;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '首页雷达' },
  { key: '/market-analysis', icon: <BarChartOutlined />, label: '市场分析' },
  { key: '/review-insights', icon: <CommentOutlined />, label: '评论洞察' },
  { key: '/profit-analysis', icon: <DollarOutlined />, label: '利润测算' },
  { key: '/trend-seasonal', icon: <StockOutlined />, label: '趋势季节' },
  { key: '/suppliers', icon: <ShopOutlined />, label: '供应商' },
  { key: '/compliance', icon: <AuditOutlined />, label: '合规检查' },
  { key: '/action-plan', icon: <CarryOutOutlined />, label: '行动计划' },
  { key: '/report-center', icon: <FileTextOutlined />, label: '报告中心' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
];

const bottomItems = [
  { key: '/help', icon: <QuestionCircleOutlined />, label: '帮助' },
];

export default function AppSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed } = useSelector((state: RootState) => state.ui);
  const { token } = antTheme.useToken();
  const isDark = false;

  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={sidebarCollapsed}
      width={250}
      collapsedWidth={80}
      style={{
        background: isDark ? '#0f172a' : '#ffffff',
        borderRight: `1px solid ${isDark ? 'rgba(51, 65, 85, 0.6)' : 'rgba(226, 232, 240, 0.8)'}`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: 'calc(100vh - 64px)',
      }}
    >
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        inlineIndent={16}
        style={{
          borderRight: 0,
          padding: '12px 14px',
          background: 'transparent',
          fontWeight: 700,
        }}
        theme={isDark ? 'dark' : 'light'}
      />
      <Menu
        mode="inline"
        selectable={false}
        items={bottomItems}
        onClick={({ key }) => navigate(key)}
        style={{
          borderRight: 0,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          padding: '12px 14px',
          background: 'transparent',
          fontWeight: 700,
        }}
        theme={isDark ? 'dark' : 'light'}
      />
    </Sider>
  );
}
