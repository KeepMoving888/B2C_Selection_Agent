import { ConfigProvider, Drawer, Layout, theme as antTheme } from 'antd';
import { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Outlet, useLocation } from 'react-router-dom';
import { lightTheme } from '../../theme';
import { setMobileMenuOpen } from '../../store/slices/uiSlice';
import { useMobile } from '../../hooks/useMobile';
import type { RootState } from '../../store';
import AppFooter from './AppFooter';
import AppHeader from './AppHeader';
import AppSidebar from './AppSidebar';

const { Content } = Layout;

export default function MainLayout() {
  const dispatch = useDispatch();
  const location = useLocation();
  const { mobileMenuOpen } = useSelector((state: RootState) => state.ui);
  const isMobile = useMobile();
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    dispatch(setMobileMenuOpen(false));
    // 页面切换后滚动到内容区顶部，避免从长页面切过来仍停留在底部
    const el = contentRef.current;
    if (el) {
      el.scrollTo({ top: 0, behavior: 'smooth' });
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [location.pathname, dispatch]);

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
          {!isMobile && <AppSidebar />}
          <Layout style={{ display: 'flex', flexDirection: 'column', minWidth: 0, height: 'calc(100vh - 68px)' }}>
            <Content
              ref={contentRef}
              className="main-layout-content"
              style={{
                padding: isMobile ? 16 : 32,
                background: '#f8fafc',
                flex: 1,
                overflow: 'auto',
                minWidth: 0,
                width: '100%',
                WebkitOverflowScrolling: 'touch',
              }}
            >
              <div style={{ maxWidth: '100%', margin: '0 auto', minWidth: 0 }}>
                <Outlet />
              </div>
            </Content>
            <AppFooter />
          </Layout>
        </Layout>
        <Drawer
          placement="left"
          closable={false}
          onClose={() => dispatch(setMobileMenuOpen(false))}
          open={isMobile && mobileMenuOpen}
          width={isMobile ? '72%' : 260}
          bodyStyle={{ padding: 0 }}
          styles={{ body: { padding: 0 } }}
        >
          <AppSidebar mobile />
        </Drawer>
      </Layout>
    </ConfigProvider>
  );
}
