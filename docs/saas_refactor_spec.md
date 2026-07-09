# 选品决策系统 SaaS 重构方案

## 1. 项目背景与目标

将当前基于 Streamlit 的单页应用重构为完整的企业级 SaaS 系统，保留并扩展现有选品分析能力，提供多页面导航、统一视觉规范、状态管理和可扩展的 API 架构。

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    选品决策系统 (SaaS)                    │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│   左侧导航栏  │              顶部 Header                  │
│  (240px/折叠) ├──────────────────────────────────────────┤
│              │                                          │
│              │           内容展示区 (Router)             │
│              │                                          │
│              │  Dashboard / 商品分析 / 利润测算 / ...     │
│              │                                          │
│              ├──────────────────────────────────────────┤
│              │              Footer 版权信息               │
└──────────────┴──────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │   FastAPI 后端服务       │
              │  (分析引擎 / 报告 / 用户) │
              └─────────────────────────┘
```

## 3. 技术栈选型

| 层级 | 选型 | 说明 |
|------|------|------|
| 前端框架 | React 18 + TypeScript + Vite | 类型安全、构建快、生态成熟 |
| UI 组件库 | Ant Design 5 | 企业级组件、主题定制方便 |
| 图表库 | ECharts (echarts-for-react) | 与 Ant Design 配合、功能丰富 |
| 状态管理 | Redux Toolkit + RTK Query | 全局状态 + 数据缓存/同步 |
| 路由 | React Router v6 | 声明式路由、嵌套路由支持 |
| 后端框架 | FastAPI | 异步高性能、自动文档、Python 生态 |
| 数据验证 | Pydantic v2 | 前后端数据契约 |
| 认证 | JWT (python-jose) | 无状态、易扩展 |
| 数据库 | SQLite / PostgreSQL | 阶段一用 SQLite，生产切 PostgreSQL |
| ORM | SQLModel | 与 FastAPI/Pydantic 原生集成 |

## 4. 目录结构

```
cross-border-agent/
├── frontend/                    # 现有 Streamlit 前端（保留为 legacy/demo）
│   └── app.py
├── web/                         # 新增 React SaaS 前端
│   ├── src/
│   │   ├── app/                 # 路由与布局
│   │   ├── components/          # 公共组件 (Header, Sidebar, Footer)
│   │   ├── features/            # 按业务域拆分
│   │   │   ├── dashboard/
│   │   │   ├── productAnalysis/
│   │   │   ├── profitCalculator/
│   │   │   ├── marketInsights/
│   │   │   ├── reviewAnalytics/
│   │   │   ├── reportCenter/
│   │   │   └── settings/
│   │   ├── store/               # Redux store + slices
│   │   ├── services/            # API client (RTK Query / axios)
│   │   ├── hooks/               # 自定义 Hooks
│   │   ├── types/               # TypeScript 类型定义
│   │   ├── utils/               # 工具函数
│   │   ├── theme/               # 主题配置
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── api/                         # 新增 FastAPI 后端
│   ├── main.py                  # 应用入口
│   ├── deps.py                  # 依赖注入 (DB, 认证)
│   ├── core/                    # 配置、安全、日志
│   ├── routers/                 # API 路由
│   │   ├── auth.py
│   │   ├── analysis.py
│   │   ├── profit.py
│   │   ├── market.py
│   │   ├── reviews.py
│   │   ├── reports.py
│   │   └── settings.py
│   ├── services/                # 业务逻辑 (从 frontend/app.py 抽取)
│   │   ├── report_engine.py
│   │   ├── profit_engine.py
│   │   ├── market_engine.py
│   │   └── review_engine.py
│   ├── models/                  # SQLModel 数据库模型
│   └── schemas/                 # Pydantic 请求/响应模型
└── docs/saas_refactor_spec.md   # 本方案
```

## 5. 页面设计

### 5.1 通用布局

- **Header (64px)**：左侧 Logo + 系统名，中部全局搜索，右侧通知/用户/主题切换
- **Sidebar (240px，可折叠至 80px)**：7 个主导航 + 底部帮助/反馈
- **Content**：面包屑 + 页面标题 + 操作区 + 卡片内容
- **Footer (48px)**：版权信息、版本号

### 5.2 页面清单

| 页面 | 路由 | 核心内容 |
|------|------|----------|
| 仪表板 | `/dashboard` | 关键指标卡片、最近分析、快捷入口、7 天趋势图 |
| 商品分析 | `/product-analysis` | 搜索框、商品信息卡、雷达图、五维评分、利润测算、历史对比 |
| 利润测算 | `/profit-calculator` | 成本表单、实时利润、ROI 情景、优化建议、历史记录 |
| 市场洞察 | `/market-insights` | 类目趋势、竞品监控、机会识别、季节性预测 |
| 评论分析 | `/review-analytics` | 情感分析、词云、痛点识别、改进建议、时间线 |
| 报告中心 | `/report-center` | 报告列表、详情、批量导出、分享、模板 |
| 设置 | `/settings` | 账户、参数、通知、数据导入导出、API 密钥、主题 |

## 6. API 设计（RESTful）

### 6.1 认证

- `POST /api/v1/auth/login`：登录，返回 JWT
- `POST /api/v1/auth/register`：注册
- `GET /api/v1/auth/me`：当前用户信息

### 6.2 分析

- `POST /api/v1/analysis`：创建分析任务
  - Payload: `{ keyword, market, budget }`
  - Response: `{ task_id, status, report }`
- `GET /api/v1/analysis/{id}`：获取分析结果
- `GET /api/v1/analysis/history`：历史记录列表（分页）
- `POST /api/v1/analysis/{id}/compare`：与另一条记录对比

### 6.3 利润测算

- `POST /api/v1/profit/calculate`：独立利润计算
  - Payload: `{ selling_price, unit_cost, category, market, ... }`
  - Response: `{ total_cost, gross_margin, roi_scenarios, suggestions }`
- `GET /api/v1/profit/history`：历史测算记录

### 6.4 市场洞察

- `GET /api/v1/market/trends`：类目趋势
- `GET /api/v1/market/competitors`：竞品列表
- `GET /api/v1/market/opportunities`：市场机会
- `GET /api/v1/market/seasonality`：季节性预测

### 6.5 评论分析

- `POST /api/v1/reviews/analyze`：评论分析
- `GET /api/v1/reviews/{product_id}/sentiment`：情感分布
- `GET /api/v1/reviews/{product_id}/keywords`：关键词/词云
- `GET /api/v1/reviews/{product_id}/timeline`：趋势时间线

### 6.6 报告中心

- `GET /api/v1/reports`：报告列表（筛选、分页）
- `GET /api/v1/reports/{id}`：报告详情
- `POST /api/v1/reports/{id}/export`：导出 PDF/Excel
- `POST /api/v1/reports/{id}/share`：生成分享链接

### 6.7 设置

- `GET /api/v1/settings`：用户设置
- `PUT /api/v1/settings`：更新设置
- `POST /api/v1/settings/api-key`：生成/刷新 API 密钥

## 7. 状态管理（Redux Toolkit）

```
store/
├── index.ts
├── slices/
│   ├── authSlice.ts         # 用户、token、主题
│   ├── analysisSlice.ts     # 当前分析、历史记录
│   ├── profitSlice.ts       # 利润测算输入/结果
│   ├── marketSlice.ts       # 市场数据
│   ├── reviewSlice.ts       # 评论分析
│   ├── reportSlice.ts       # 报告列表
│   └── uiSlice.ts           # 侧边栏折叠、加载态、通知
```

## 8. 视觉设计规范

- **主色**：`#1976d2`（深蓝）
- **辅助色**：成功 `#4caf50`、警告 `#ff9800`、危险 `#f44336`
- **背景**：`#f5f5f5`
- **卡片背景**：`#ffffff`
- **字体**：标题 18-24px 加粗，正文 14-16px，辅助 12-13px
- **间距**：卡片间距 24px，卡片内边距 20px，元素间距 12-16px
- **圆角**：卡片 8px，按钮 6px
- **阴影**：卡片 `0 2px 8px rgba(0,0,0,0.08)`

## 9. 响应式断点

- **桌面**：≥1200px，完整左侧导航
- **平板**：768px-1199px，导航可折叠，内容区自适应
- **移动**：<768px，底部导航栏，内容全宽

## 10. 实施阶段

### 阶段一：后端 API 与数据层（2-3 天）

1. 初始化 `api/` 目录，搭建 FastAPI 项目结构
2. 抽取 `frontend/app.py` 中的分析逻辑到 `api/services/`
3. 实现核心接口：`/analysis`、`/profit/calculate`、`/market/trends`
4. 添加 SQLite 数据库模型（用户、分析记录、报告、设置）
5. 添加 JWT 认证桩和 CORS 配置
6. 编写 API 单元测试

### 阶段二：前端基础架构（2 天）

1. 初始化 `web/` React + Vite + TypeScript 项目
2. 安装 Ant Design、ECharts、Redux Toolkit、React Router
3. 实现 Layout（Header、Sidebar、Footer）和主题切换
4. 配置路由与权限守卫
5. 实现 API client 和 RTK Query 基础服务

### 阶段三：核心页面开发（4-5 天）

1. 仪表板：指标卡、最近记录、趋势图
2. 商品分析：搜索、雷达图、五维评分、利润测算嵌入
3. 利润测算：表单、实时计算、ROI 图、优化建议、历史记录
4. 市场洞察 / 评论分析 / 报告中心 / 设置：按 MVP 实现核心功能

### 阶段四：集成、优化与测试（2-3 天）

1. 前后端联调
2. 加载态、错误处理、骨架屏
3. 响应式适配
4. E2E 测试（Playwright）和单元测试
5. 构建、Docker 化、部署脚本

## 11. 风险与决策点

| 决策点 | 建议 | 备注 |
|--------|------|------|
| 是否保留 Streamlit 版本？ | 保留为 `frontend/legacy` | 作为快速演示和回归对比 |
| 认证是否必须真实？ | 阶段一用 JWT + 内存/SQLite 用户 | 后续可对接 OAuth/LDAP |
| 数据库选型 | SQLite → PostgreSQL | 降低初期复杂度 |
| 是否 SSR？ | 否，纯 CSR SPA | 满足 SaaS 后台场景 |
| 文件上传/导出 | 后端生成，前端下载 | PDF 可用 Playwright/WeasyPrint |

## 12. 验收标准

- [ ] 7 个页面均可通过左侧导航访问
- [ ] 商品分析页保留原有全部分析能力
- [ ] 利润测算页支持独立输入和实时计算
- [ ] 所有页面符合视觉规范
- [ ] 桌面/平板/移动端布局正常
- [ ] 页面切换动画流畅（<300ms）
- [ ] 首屏加载 < 2 秒（生产构建）
- [ ] API 单元测试 + 前端组件测试通过
- [ ] `pytest` 全量测试通过
