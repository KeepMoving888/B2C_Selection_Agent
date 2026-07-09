import { ConfigProvider, Grid, Layout, theme as antTheme } from 'antd';
import { useSelector } from 'react-redux';
import { Outlet } from 'react-router-dom';
import { darkTheme, lightTheme } from '../../theme';
import AppFooter from './AppFooter';
import AppHeader from './AppHeader';
import AppSidebar from './AppSidebar';
import type { RootState } from '../../store';

const { Content } = Layout;
const { useBreakpoint } = Grid;

export default function MainLayout() {
  const { theme } = useSelector((state: RootState) => state.ui);
  const isDark = theme === 'dark';
  const screens = useBreakpoint();

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
        ...(isDark ? darkTheme.token : lightTheme.token),
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <AppHeader />
        <Layout>
          <AppSidebar />
          <Layout style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <Content
              style={{
                padding: screens.xl ? 32 : screens.lg ? 24 : screens.md ? 20 : 16,
                background: isDark ? '#0f172a' : '#f1f5f9',
                flex: 1,
                overflow: 'auto',
                minWidth: 0,
                width: '100%',
              }}
            >
              <div style={{ maxWidth: '100%', margin: '0 auto' }}>
                <Outlet />
              </div>
            </Content>
            <AppFooter />
          </Layout>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
