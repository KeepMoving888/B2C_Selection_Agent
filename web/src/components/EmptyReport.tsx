import { BarChartOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, Typography } from 'antd';

const { Text, Title } = Typography;

export default function EmptyReport({ pageName }: { pageName: string }) {
  return (
    <div className="empty-report">
      <div className="empty-report-icon">
        <BarChartOutlined />
      </div>
      <Title level={4} className="empty-report-title">暂无{pageName}数据</Title>
      <Text className="empty-report-desc">
        在上方搜索框输入关键词并点击「开始分析」，即可查看 {pageName} 的完整分析结果。
      </Text>
      <Button type="primary" icon={<SearchOutlined />} size="large" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} style={{ marginTop: 24 }}>
        去搜索分析
      </Button>
    </div>
  );
}
