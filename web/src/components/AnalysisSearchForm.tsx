import { SearchOutlined } from '@ant-design/icons';
import { Button, Form, Input, Select } from 'antd';
import type { SearchParams } from '../store/slices/uiSlice';

interface Props {
  initialValues?: SearchParams;
  onSubmit: (values: SearchParams) => void;
  loading?: boolean;
}

const markets = [
  { value: 'US', label: '美国站' },
  { value: 'UK', label: '英国站' },
  { value: 'DE', label: '德国站' },
  { value: 'JP', label: '日本站' },
  { value: 'CA', label: '加拿大站' },
];

const budgets = [
  { value: '5000-10000', label: '$5,000 - $10,000' },
  { value: '10000-30000', label: '$10,000 - $30,000' },
  { value: '30000-50000', label: '$30,000 - $50,000' },
  { value: '50000+', label: '$50,000+' },
];

export default function AnalysisSearchForm({ initialValues, onSubmit, loading }: Props) {
  return (
    <Form
      layout="inline"
      initialValues={initialValues || { keyword: '', market: 'US', budget: '5000-10000' }}
      onFinish={onSubmit}
      style={{ flexWrap: 'wrap', gap: '0 8px' }}
    >
      <Form.Item name="keyword" rules={[{ required: true, message: '请输入关键词' }]} style={{ flex: '1 1 280px', minWidth: 200 }}>
        <Input placeholder="输入关键词，如 dog chew toys" allowClear />
      </Form.Item>
      <Form.Item name="market" style={{ width: 140 }}>
        <Select options={markets} />
      </Form.Item>
      <Form.Item name="budget" style={{ width: 180 }}>
        <Select options={budgets} />
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
          开始分析
        </Button>
      </Form.Item>
    </Form>
  );
}
