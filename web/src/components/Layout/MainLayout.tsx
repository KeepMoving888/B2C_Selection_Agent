import { ConfigProvider, Layout, theme as antTheme } from 'antd';
import { Outlet } from 'react-router-dom';
import { lightTheme } from '../../theme';
import AppFooter from './AppFooter';
import AppHeader from './AppHeader';
import AppSidebar from './AppSidebar';

const { Content } = Layout;

export default function MainLayout() {
  // 参赛版本强制浅色主题：保证自定义 CSS 全部生效，视觉统一
  return (
    <ConfigProvider
      theme={{
        algorithm: antTheme.defaultAlgorithm,
        ...lightTheme.token,
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <AppHeader />
        <Layout style={{ height: 'calc(100vh - 68px)', overflow: 'hidden' }}>
          <AppSidebar />
          <Layout style={{ display: 'flex', flexDirection: 'column', minWidth: 0, height: 'calc(100vh - 68px)' }}>
            <Content
              style={{
                padding: 32,
                background: '#f8fafc',
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
