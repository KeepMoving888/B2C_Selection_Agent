import { SearchOutlined } from '@ant-design/icons';
import { Button, Empty, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

export default function EmptyReport({ pageName }: { pageName: string }) {
  const navigate = useNavigate();

  return (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <div>
          <Text strong>暂无分析报告</Text>
          <br />
          <Text type="secondary">请先在「首页雷达」输入关键词进行分析，再查看{pageName}。</Text>
        </div>
      }
      style={{ padding: 80 }}
    >
      <Button type="primary" icon={<SearchOutlined />} onClick={() => navigate('/dashboard')}>
        去首页分析
      </Button>
    </Empty>
  );
}
