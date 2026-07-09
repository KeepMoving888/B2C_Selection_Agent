import {
  BarChartOutlined,
  CommentOutlined,
  DashboardOutlined,
  DollarOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  SettingOutlined,
  ShoppingOutlined,
} from '@ant-design/icons';
import { Layout, Menu, theme as antTheme } from 'antd';
import { useSelector } from 'react-redux';
import { useLocation, useNavigate } from 'react-router-dom';
import type { RootState } from '../../store';

const { Sider } = Layout;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表板' },
  { key: '/product-analysis', icon: <ShoppingOutlined />, label: '商品分析' },
  { key: '/profit-calculator', icon: <DollarOutlined />, label: '利润测算' },
  { key: '/market-insights', icon: <BarChartOutlined />, label: '市场洞察' },
  { key: '/review-analytics', icon: <CommentOutlined />, label: '评论分析' },
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

  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={sidebarCollapsed}
      width={240}
      collapsedWidth={80}
      style={{
        background: token.colorBgContainer,
        boxShadow: '2px 0 8px rgba(0,0,0,0.04)',
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
        style={{ borderRight: 0, paddingTop: 8 }}
      />
      <Menu
        mode="inline"
        selectable={false}
        items={bottomItems}
        style={{ borderRight: 0, borderTop: `1px solid ${token.colorBorderSecondary}` }}
      />
    </Sider>
  );
}
