import { ConfigProvider, Layout, theme as antTheme } from 'antd';
import { useSelector } from 'react-redux';
import { Outlet } from 'react-router-dom';
import { darkTheme, lightTheme } from '../../theme';
import AppFooter from './AppFooter';
import AppHeader from './AppHeader';
import AppSidebar from './AppSidebar';
import type { RootState } from '../../store';

const { Content } = Layout;

export default function MainLayout() {
  const { theme } = useSelector((state: RootState) => state.ui);
  const isDark = theme === 'dark';

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
        ...lightTheme.token,
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <AppHeader />
        <Layout>
          <AppSidebar />
          <Layout style={{ display: 'flex', flexDirection: 'column' }}>
            <Content
              style={{
                margin: 24,
                padding: 24,
                background: isDark ? '#141414' : '#f5f5f5',
                borderRadius: 8,
                flex: 1,
                overflow: 'auto',
              }}
            >
              <Outlet />
            </Content>
            <AppFooter />
          </Layout>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
