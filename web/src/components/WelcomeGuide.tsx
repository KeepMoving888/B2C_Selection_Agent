import {
  BarChartOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  CommentOutlined,
  DollarOutlined,
  RiseOutlined,
  SearchOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import { Button, Typography } from 'antd';

const { Text, Title } = Typography;

interface Props {
  onExample: (keyword: string) => void;
}

const examples = [
  { keyword: 'dog chew toys', label: '宠物咬胶玩具', icon: <ShopOutlined /> },
  { keyword: 'carplay adapter', label: '车载 CarPlay', icon: <RiseOutlined /> },
  { keyword: 'portable blender', label: '便携榨汁机', icon: <DollarOutlined /> },
  { keyword: 'yoga mat', label: '瑜伽垫', icon: <BarChartOutlined /> },
  { keyword: 'kids water bottle', label: '儿童水壶', icon: <CommentOutlined /> },
];

const steps = [
  { icon: <SearchOutlined />, title: '输入关键词', desc: '在搜索框填写目标商品或品类，支持英文多词与多关键词分隔。' },
  { icon: <BarChartOutlined />, title: '多维分析', desc: '系统自动输出市场、评论、利润、趋势、供应商、合规等维度结论。' },
  { icon: <BulbOutlined />, title: '决策落地', desc: '基于综合评分与行动计划，快速判断选品可行性并制定执行节奏。' },
];

export default function WelcomeGuide({ onExample }: Props) {
  return (
    <div className="welcome-guide">
      <div className="welcome-guide-inner">
        <div className="welcome-guide-main">
          <div className="welcome-guide-badge">
            <CheckCircleOutlined /> 智能选品决策系统
          </div>
          <Title level={3} className="welcome-guide-title">
            从关键词到决策建议，只需一次搜索
          </Title>
          <Text className="welcome-guide-desc">
            输入任意跨境电商品类关键词，系统将自动聚合市场、评论、利润、趋势、供应商与合规风险数据，生成可落地的选品决策报告。
          </Text>

          <div className="welcome-guide-steps">
            {steps.map((s, i) => (
              <div key={i} className="welcome-guide-step">
                <div className="welcome-guide-step-icon">{s.icon}</div>
                <div className="welcome-guide-step-num">0{i + 1}</div>
                <div className="welcome-guide-step-title">{s.title}</div>
                <div className="welcome-guide-step-desc">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="welcome-guide-examples">
          <div className="welcome-guide-examples-title">
            <BulbOutlined style={{ marginRight: 8 }} />
            热门示例
          </div>
          <Text className="welcome-guide-examples-desc">
            点击下方任一示例，即可立即体验完整分析流程。
          </Text>
          <div className="welcome-guide-example-list">
            {examples.map((ex) => (
              <button
                key={ex.keyword}
                className="welcome-guide-example-btn"
                onClick={() => onExample(ex.keyword)}
              >
                <span className="welcome-guide-example-icon">{ex.icon}</span>
                <span className="welcome-guide-example-label">{ex.label}</span>
                <span className="welcome-guide-example-keyword">{ex.keyword}</span>
              </button>
            ))}
          </div>
          <Button
            type="primary"
            size="large"
            icon={<SearchOutlined />}
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="welcome-guide-cta"
            block
          >
            前往搜索框开始分析
          </Button>
        </div>
      </div>
    </div>
  );
}
