import { Layout, theme as antTheme, Typography } from 'antd';

const { Footer } = Layout;
const { Text } = Typography;

export default function AppFooter() {
  const { token } = antTheme.useToken();

  return (
    <Footer
      style={{
        textAlign: 'center',
        background: token.colorBgContainer,
        borderTop: `1px solid ${token.colorBorderSecondary}`,
        padding: '12px 24px',
      }}
    >
      <Text type="secondary" style={{ fontSize: 12 }}>
        © 2026 选品决策系统 Product Selection Decision System · v1.0.0
      </Text>
    </Footer>
  );
}
