// ============================================================
// services/mockData.ts — 跨境电商智能选品数据引擎（TypeScript 端口）
//
// 从 api/services/report_engine.py 端口，支持前端独立运行（Vercel 部署）
// ============================================================

import type { AnalysisReport } from '../types';

// ------------------------------------------------------------------
// 品类画像库
// ------------------------------------------------------------------
interface ProductArchetype {
  category: string;
  avg_price: number;
  price_range: [number, number];
  rating: number;
  reviews_level: 'low' | 'medium' | 'high';
  trend: 'rising' | 'stable' | 'falling';
  pain_points: string[];
  praised: string[];
  season_peak: number[];
  certifications: string[];
  supplier_city: string;
  supplier_specialty: string;
  compliance_risks: string[];
  cn_keywords: string[];
}

const ARCHETYPES: Record<string, ProductArchetype> = {
  'cat toy': {
    category: 'pet_supplies',
    avg_price: 12.5,
    price_range: [8.0, 22.0],
    rating: 4.3,
    reviews_level: 'high',
    trend: 'rising',
    pain_points: ['羽毛容易脱落', '电池续航短', '运行时噪音大', '猫咪很快失去兴趣'],
    praised: ['自动互动很方便', 'USB 充电环保', '替换装多，性价比高'],
    season_peak: [11, 12],
    certifications: ['CPSC 儿童产品证书', 'ASTM F963 玩具安全标准'],
    supplier_city: '义乌',
    supplier_specialty: '宠物玩具',
    compliance_risks: [
      '小零件/绳线/羽毛存在窒息与缠绕风险，须符合 ASTM F963 机械物理性能要求',
      '含电池款须做 GCC 通用合格证书及 UL 4200A 纽扣电池安全测试',
      '猫薄荷填充物来源、农药残留及标签标识需符合宠物用品安全规范',
    ],
    cn_keywords: ['猫玩具', '逗猫棒', '猫薄荷玩具', '电动猫玩具'],
  },
  'dog chew toys': {
    category: 'pet_supplies',
    avg_price: 15.0,
    price_range: [9.0, 28.0],
    rating: 4.5,
    reviews_level: 'medium',
    trend: 'rising',
    pain_points: ['不够耐咬', '有异味', '尺寸偏小', '掉色严重'],
    praised: ['耐咬耐磨', '狗狗很喜欢', '材质安全无毒'],
    season_peak: [11, 12, 1],
    certifications: ['FDA 食品接触材料', 'CPSC 儿童产品证书'],
    supplier_city: '东莞',
    supplier_specialty: '宠物咬胶',
    compliance_risks: [
      '咬胶/食品接触材质需通过 FDA 21 CFR 177 食品级检测，避免邻苯二甲酸盐超标',
      '产品耐咬碎片吞咽风险高，需做 CPSC 16 CFR 1501 小零件及锐利边缘测试',
      '色素/香精添加剂需符合宠物用品化学品安全限量，防止过敏与中毒投诉',
    ],
    cn_keywords: ['宠物咬胶', '耐咬磨牙棒', '狗狗玩具', '洁齿磨牙棒'],
  },
  'yoga mat': {
    category: 'sports',
    avg_price: 28.0,
    price_range: [18.0, 55.0],
    rating: 4.4,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['防滑性一般', '有刺鼻气味', '太薄硌得慌', '容易沾灰'],
    praised: ['防滑效果好', '厚度适中', '携带方便'],
    season_peak: [1, 2, 9],
    certifications: ['CE 认证', 'REACH 环保检测', 'SGS 材质检测'],
    supplier_city: '广州',
    supplier_specialty: '运动用品',
    compliance_risks: [
      'TPE/PVC/NBR 材质需通过 REACH SVHC 与邻苯二甲酸盐检测，防止气味投诉与下架',
      '防滑涂层、染料及印刷油墨需符合 OEKO-TEX 或加州 65 号提案化学物质限量',
      '出口欧盟需 CE 标识及技术文件，德国需 EPR 包装法注册',
    ],
    cn_keywords: ['瑜伽垫', 'TPE瑜伽垫', '防滑瑜伽垫', '健身垫'],
  },
  'wireless earbuds': {
    category: 'electronics',
    avg_price: 35.0,
    price_range: [19.0, 79.0],
    rating: 4.2,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['续航不够', '连接不稳定', '佩戴不舒服', '音质一般'],
    praised: ['性价比高', '连接快', '低音饱满'],
    season_peak: [11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'RoHS 环保认证'],
    supplier_city: '深圳',
    supplier_specialty: '蓝牙耳机',
    compliance_risks: [
      '无线射频模块需通过 FCC ID（美国）、CE-RED（欧盟）、TELEC（日本）认证',
      '锂电池需符合 UN38.3、UL 1642/2054 或 IEC 62133 安全测试，防止起火召回',
      'RoHS/REACH 重金属与有害物质限量、WEEE 注册及能效标签要求',
    ],
    cn_keywords: ['蓝牙耳机', 'TWS耳机', '无线耳机', '降噪耳机'],
  },
  'carplay': {
    category: 'electronics',
    avg_price: 45.0,
    price_range: [25.0, 99.0],
    rating: 4.0,
    reviews_level: 'high',
    trend: 'rising',
    pain_points: ['连接不稳定', '兼容性差', '发热严重', '设置复杂'],
    praised: ['即插即用', '兼容车型多', '画面清晰流畅'],
    season_peak: [11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'RoHS 环保认证'],
    supplier_city: '深圳',
    supplier_specialty: '车载电子',
    compliance_risks: [
      'CarPlay/Android Auto 无线适配涉及苹果 MFi 或谷歌 GMS 授权，未授权存在下架风险',
      '车载电子需通过 FCC/CE-RED 射频认证、E-mark（欧洲车载）及电磁兼容 EMC 测试',
      '高温环境下工作需做可靠性测试，防止过热、起火及车辆保险责任纠纷',
    ],
    cn_keywords: ['车载CarPlay', '无线CarPlay盒子', '车载电子', '车机互联'],
  },
  'portable charger': {
    category: 'electronics',
    avg_price: 25.0,
    price_range: [12.0, 59.0],
    rating: 4.3,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['容量虚标', '充电慢', '体积大', '发热明显'],
    praised: ['容量足', '轻薄便携', '支持快充'],
    season_peak: [11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'UL 安全认证'],
    supplier_city: '深圳',
    supplier_specialty: '移动电源',
    compliance_risks: [
      '锂电池移动电源属于危险品，需 UN38.3、MSDS、UL 2056/2743 或 IEC 62133 认证',
      '亚马逊已要求充电宝提供 UL 2056 测试报告，容量虚标易引发消费者集体诉讼',
      '空运/海运需按 UN38.3 与 IATA DGR 包装要求，否则物流拒收',
    ],
    cn_keywords: ['移动电源', '充电宝', '快充充电宝', '大容量充电宝'],
  },
  'kitchen organizer': {
    category: 'home_kitchen',
    avg_price: 22.0,
    price_range: [12.0, 45.0],
    rating: 4.5,
    reviews_level: 'medium',
    trend: 'stable',
    pain_points: ['承重不够', '安装复杂', '尺寸不合适', '容易生锈'],
    praised: ['收纳空间大', '安装简单', '材质厚实'],
    season_peak: [3, 9],
    certifications: ['FDA 食品接触材料', 'SGS 材质检测'],
    supplier_city: '泉州',
    supplier_specialty: '家居收纳',
    compliance_risks: [
      '接触食品的收纳/架类需符合 FDA 21 CFR 食品级及 LFGB（德国）迁移量测试',
      '金属焊接部位需做防锈、镀层重金属（铅、镉、镍）迁移测试',
      '带吸盘/胶贴安装件需评估承重安全与跌落风险，避免人身伤害索赔',
    ],
    cn_keywords: ['厨房收纳', '冰箱收纳盒', '厨房置物架', '抽屉分隔'],
  },
  'makeup brush': {
    category: 'beauty',
    avg_price: 14.0,
    price_range: [8.0, 32.0],
    rating: 4.6,
    reviews_level: 'medium',
    trend: 'rising',
    pain_points: ['掉毛严重', '刷毛扎脸', '异味大', '包装简陋'],
    praised: ['刷毛柔软', '上妆均匀', '性价比高'],
    season_peak: [11, 12],
    certifications: ['FDA 化妆品合规', 'CE 认证'],
    supplier_city: '广州',
    supplier_specialty: '美妆工具',
    compliance_risks: [
      '刷毛材质（动物毛/人造纤维）及粘合剂需符合 FDA 化妆品接触材料与欧盟 REACH 要求',
      '木质手柄涂料、金属口管镀层需检测重金属（铅、镍、铬）与甲醛释放',
      '声称抗菌/环保/ cruelty-free 需有相应检测报告与标签证据，避免虚假宣传投诉',
    ],
    cn_keywords: ['化妆刷', '美妆工具', '散粉刷', '化妆刷套装'],
  },
  'sports water bottle': {
    category: 'sports',
    avg_price: 22.0,
    price_range: [12.0, 45.0],
    rating: 4.4,
    reviews_level: 'high',
    trend: 'rising',
    pain_points: ['漏水密封差', '塑料味重', '容量虚标', '清洗困难'],
    praised: ['防漏设计好', '容量大', '便携提手实用'],
    season_peak: [6, 7, 8],
    certifications: ['FDA 食品接触材料', 'BPA Free 检测', 'SGS 材质检测'],
    supplier_city: '永康',
    supplier_specialty: '运动水杯',
    compliance_risks: [
      '食品接触材质需通过 FDA 21 CFR 177 或 EU 10/2011 迁移量测试，确保 BPA Free',
      '密封圈/吸管等硅胶/橡胶部件需符合 LFGB 与加州 65 号提案化学物质限量',
      '儿童运动水杯需额外符合 CPSIA 铅含量与邻苯二甲酸盐限制',
    ],
    cn_keywords: ['运动水杯', '大容量水壶', 'BPA Free 水瓶', '健身水壶'],
  },
  'water bottle': {
    category: 'home_kitchen',
    avg_price: 18.0,
    price_range: [9.0, 38.0],
    rating: 4.3,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['保温效果差', '杯盖易坏', '瓶身太重', '刻度不清晰'],
    praised: ['保温持久', '外观好看', '容量刚好'],
    season_peak: [6, 7, 8],
    certifications: ['FDA 食品接触材料', 'LFGB 检测', 'BPA Free 检测'],
    supplier_city: '永康',
    supplier_specialty: '保温杯壶',
    compliance_risks: [
      '不锈钢材质需符合 FDA/LFGB 食品接触材料标准，避免重金属迁移超标',
      '保温性能宣称需有真实测试数据支撑，避免虚假宣传',
      '杯盖、密封圈等塑料部件需符合 REACH 与加州 65 号提案',
    ],
    cn_keywords: ['保温杯', '不锈钢水杯', '运动水壶', '随行杯'],
  },
  'running shoes': {
    category: 'sports',
    avg_price: 65.0,
    price_range: [35.0, 120.0],
    rating: 4.2,
    reviews_level: 'high',
    trend: 'rising',
    pain_points: ['尺码偏小', '鞋底不耐磨', '透气性差', '磨脚后跟'],
    praised: ['轻便舒适', '缓震效果好', '性价比高'],
    season_peak: [1, 4, 9],
    certifications: ['CE 认证', 'REACH 环保检测'],
    supplier_city: '泉州',
    supplier_specialty: '运动鞋服',
    compliance_risks: [
      '鞋材需符合 REACH SVHC 与邻苯二甲酸盐限制，避免化学超标',
      '宣称功能（缓震、透气、防水）需有检测报告支持',
      '品牌/外观设计需排查商标与专利侵权风险',
    ],
    cn_keywords: ['跑步鞋', '运动鞋', '缓震跑鞋', '透气跑鞋'],
  },
  'resistance bands': {
    category: 'sports',
    avg_price: 16.0,
    price_range: [9.0, 32.0],
    rating: 4.5,
    reviews_level: 'medium',
    trend: 'rising',
    pain_points: ['弹力不足', '乳胶味大', '容易断裂', '收纳不方便'],
    praised: ['阻力分级清晰', '便携实用', '训练效果好'],
    season_peak: [1, 4, 11],
    certifications: ['CE 认证', 'SGS 材质检测'],
    supplier_city: '东莞',
    supplier_specialty: '健身器材',
    compliance_risks: [
      '乳胶/TPE 材质需检测重金属与致敏物质，避免皮肤接触投诉',
      '阻力磅数宣称需真实，避免虚假宣传',
      '套装产品需确保配件（门扣、手柄）承重安全',
    ],
    cn_keywords: ['阻力带', '弹力带', '健身带', '拉力带'],
  },
  'phone case': {
    category: 'electronics',
    avg_price: 12.0,
    price_range: [6.0, 25.0],
    rating: 4.4,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['按键不灵敏', '保护性一般', '容易发黄', '无线充电受影响'],
    praised: ['手感好', '孔位精准', '防摔耐用'],
    season_peak: [11, 12],
    certifications: ['RoHS 环保认证', 'CE 认证'],
    supplier_city: '深圳',
    supplier_specialty: '手机配件',
    compliance_risks: [
      '塑料/硅胶材质需符合 RoHS/REACH 有害物质限量',
      '外观设计需规避苹果、三星等品牌专利与商标',
      '磁吸/无线充电功能需确保不影响设备正常工作',
    ],
    cn_keywords: ['手机壳', '防摔手机壳', '磁吸手机壳', '透明手机壳'],
  },
  'led strip lights': {
    category: 'electronics',
    avg_price: 24.0,
    price_range: [12.0, 55.0],
    rating: 4.3,
    reviews_level: 'high',
    trend: 'rising',
    pain_points: ['粘贴不牢', '颜色不均匀', '控制器易坏', 'APP 连接不稳定'],
    praised: ['氛围感强', '安装简单', '颜色丰富'],
    season_peak: [11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'RoHS 环保认证'],
    supplier_city: '深圳',
    supplier_specialty: 'LED 照明',
    compliance_risks: [
      'LED 灯带需通过 FCC/CE-RED 电磁兼容与射频认证',
      '电源适配器需符合 UL/CE 安全标准，防止过热起火',
      'RoHS 有害物质限量与能效标签要求需同步满足',
    ],
    cn_keywords: ['LED 灯带', '氛围灯', 'RGB 灯带', '智能灯带'],
  },
  'baby bottles': {
    category: 'baby',
    avg_price: 18.0,
    price_range: [10.0, 40.0],
    rating: 4.6,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['奶嘴流速不稳', '清洗死角多', '漏奶', '材质不放心'],
    praised: ['防胀气效果好', '材质安全', '宝宝接受度高'],
    season_peak: [11, 12],
    certifications: ['FDA 食品接触材料', 'CPC 儿童产品证书', 'BPA Free 检测'],
    supplier_city: '广州',
    supplier_specialty: '母婴用品',
    compliance_risks: [
      '婴幼儿产品需通过 FDA 食品接触与 CPSIA 铅/邻苯二甲酸盐测试',
      '奶嘴/硅胶部件需符合食品级标准与窒息风险提示',
      '标签需清晰标注适用年龄、材质与清洁方式',
    ],
    cn_keywords: ['奶瓶', '防胀气奶瓶', 'PPSU 奶瓶', '新生儿奶瓶'],
  },
  'face serum': {
    category: 'beauty',
    avg_price: 24.0,
    price_range: [14.0, 55.0],
    rating: 4.4,
    reviews_level: 'high',
    trend: 'rising',
    pain_points: ['吸收慢黏腻', '刺激过敏', '效果不明显', '包装易漏'],
    praised: ['肤感清爽', '提亮明显', '成分温和'],
    season_peak: [11, 12, 3],
    certifications: ['FDA 化妆品合规', 'GMPC 认证', ' dermatologically tested'],
    supplier_city: '广州',
    supplier_specialty: '护肤彩妆',
    compliance_risks: [
      '化妆品需符合 FDA 21 CFR 及欧盟 EC 1223/2009 成分与标签要求',
      '功效宣称（美白/抗衰/祛痘）需有测试数据支撑，避免虚假宣传',
      '防腐剂、香精、活性物需符合目标市场限量标准',
    ],
    cn_keywords: ['精华液', '面部精华', '玻尿酸精华', '维C精华'],
  },
  'hair dryer': {
    category: 'beauty',
    avg_price: 42.0,
    price_range: [25.0, 99.0],
    rating: 4.3,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['噪音大', '热风伤发', '线太短', '体积重'],
    praised: ['干发快', '负离子护发', '轻便好握'],
    season_peak: [11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'UL 安全认证'],
    supplier_city: '深圳',
    supplier_specialty: '美发电器',
    compliance_risks: [
      '带电吹风需通过 FCC/CE 电磁兼容与电气安全认证',
      '发热部件需做温升、异常测试，防止过热起火',
      '负离子/护发功效宣称需有检测报告支持',
    ],
    cn_keywords: ['吹风机', '负离子吹风机', '高速吹风机', '电吹风'],
  },
  'camping tent': {
    category: 'sports',
    avg_price: 85.0,
    price_range: [45.0, 180.0],
    rating: 4.4,
    reviews_level: 'medium',
    trend: 'rising',
    pain_points: ['搭建复杂', '防风性差', '闷热不透气', '收纳体积大'],
    praised: ['空间宽敞', '防水性能好', '快速搭建'],
    season_peak: [5, 6, 7],
    certifications: ['CE 认证', 'REACH 环保检测', 'SGS 材质检测'],
    supplier_city: '泉州',
    supplier_specialty: '户外用品',
    compliance_risks: [
      '帐篷面料与涂层需符合 REACH 与加州 65 号提案化学限量',
      '防风、防水性能宣称需有真实测试数据',
      '玻璃纤维杆、地钉等配件需评估强度与安全风险',
    ],
    cn_keywords: ['露营帐篷', '户外帐篷', '自动帐篷', '野营帐篷'],
  },
  'smart watch': {
    category: 'electronics',
    avg_price: 55.0,
    price_range: [29.0, 129.0],
    rating: 4.1,
    reviews_level: 'high',
    trend: 'rising',
    pain_points: ['续航短', '心率不准', 'APP 兼容性差', '屏幕易刮花'],
    praised: ['功能丰富', '性价比高', '运动模式多'],
    season_peak: [11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'RoHS 环保认证'],
    supplier_city: '深圳',
    supplier_specialty: '智能穿戴',
    compliance_risks: [
      '智能手表含无线射频与锂电池，需 FCC/CE-RED/MIC 认证及 UN38.3/UL 测试',
      '健康监测功能（心率/血氧）宣称需避免医疗诊断误导',
      'APP 隐私与数据合规需符合 GDPR/CCPA 等法规',
    ],
    cn_keywords: ['智能手表', '运动手表', '蓝牙手表', '心率手表'],
  },
  'bluetooth speaker': {
    category: 'electronics',
    avg_price: 38.0,
    price_range: [19.0, 89.0],
    rating: 4.3,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['低音不足', '连接断续', '电池虚标', '防水不达标'],
    praised: ['音质清晰', '便携耐用', '续航持久'],
    season_peak: [6, 11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'RoHS 环保认证'],
    supplier_city: '深圳',
    supplier_specialty: '音频电子',
    compliance_risks: [
      '蓝牙音箱需通过 FCC/CE-RED 射频与 EMC 认证',
      '电池需符合 UN38.3、IEC 62133 或 UL 测试',
      '防水等级（IPX）宣称需有真实测试报告',
    ],
    cn_keywords: ['蓝牙音箱', '便携音箱', '户外音箱', '防水音箱'],
  },
  'usb c cable': {
    category: 'electronics',
    avg_price: 11.0,
    price_range: [6.0, 25.0],
    rating: 4.4,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['充电慢', '接头易断', '线材易缠绕', 'MFI 弹窗'],
    praised: ['快充稳定', '编织耐用', '长度合适'],
    season_peak: [11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'RoHS 环保认证'],
    supplier_city: '深圳',
    supplier_specialty: '手机配件',
    compliance_risks: [
      '数据线若含芯片需 MFi 或 USB-IF 认证，否则存在兼容性与下架风险',
      '线材外皮与接头需符合 RoHS/REACH 有害物质限量',
      '快充功率宣称需与线材规格一致，避免安全隐患',
    ],
    cn_keywords: ['Type-C数据线', '快充线', '编织数据线', 'USB-C线'],
  },
  'dog bed': {
    category: 'pet_supplies',
    avg_price: 32.0,
    price_range: [18.0, 65.0],
    rating: 4.5,
    reviews_level: 'medium',
    trend: 'rising',
    pain_points: ['填充物塌陷', '外套难拆洗', '防滑底不够', '有异味'],
    praised: ['柔软支撑好', '可拆洗', '宠物喜欢'],
    season_peak: [11, 12],
    certifications: ['CPSC 儿童产品证书', 'OEKO-TEX 标准'],
    supplier_city: '义乌',
    supplier_specialty: '宠物用品',
    compliance_risks: [
      '宠物窝填充物与面料需符合 REACH 与加州 65 号提案化学限量',
      '可拆洗部件需考虑阻燃、缩水与色牢度要求',
      '产品标签需标注材质、尺寸与清洁方式',
    ],
    cn_keywords: ['狗窝', '宠物床', '猫窝', '可拆洗狗垫'],
  },
  'storage box': {
    category: 'home_kitchen',
    avg_price: 19.0,
    price_range: [10.0, 42.0],
    rating: 4.5,
    reviews_level: 'medium',
    trend: 'stable',
    pain_points: ['盖子不紧', '材质薄易变形', '尺寸不标准', '有塑料味'],
    praised: ['容量大', '叠放稳固', '透明可视'],
    season_peak: [3, 9],
    certifications: ['FDA 食品接触材料', 'SGS 材质检测'],
    supplier_city: '台州',
    supplier_specialty: '家居收纳',
    compliance_risks: [
      '接触食品的收纳盒需符合 FDA/LFGB 食品级迁移量测试',
      '塑料材质需符合 REACH 与加州 65 号提案',
      '叠放承重与跌落测试需满足日常使用安全',
    ],
    cn_keywords: ['收纳箱', '透明收纳盒', '塑料储物箱', '整理箱'],
  },
  'robot vacuum': {
    category: 'home_kitchen',
    avg_price: 220.0,
    price_range: [120.0, 450.0],
    rating: 4.2,
    reviews_level: 'high',
    trend: 'rising',
    pain_points: ['避障不灵敏', '噪音大', '续航短', '拖地效果差'],
    praised: ['解放双手', '吸力强劲', 'APP 智能控制'],
    season_peak: [11, 12],
    certifications: ['FCC 认证', 'CE 认证', 'RoHS 环保认证'],
    supplier_city: '深圳',
    supplier_specialty: '智能家电',
    compliance_risks: [
      '扫地机器人含锂电池与无线模块，需 FCC/CE-RED/UL 等认证',
      '激光雷达/摄像头需关注隐私合规与出口管制',
      '跌落、碰撞、电池安全测试需符合目标市场强制标准',
    ],
    cn_keywords: ['扫地机器人', '智能吸尘器', '扫拖一体机', '扫地机'],
  },
  'plant pot': {
    category: 'home_kitchen',
    avg_price: 16.0,
    price_range: [8.0, 35.0],
    rating: 4.6,
    reviews_level: 'medium',
    trend: 'rising',
    pain_points: ['排水孔堵塞', '盆底漏水', '易碎', '颜色老气'],
    praised: ['设计简约', '排水合理', '性价比高'],
    season_peak: [3, 4],
    certifications: ['REACH 环保检测', 'SGS 材质检测'],
    supplier_city: '泉州',
    supplier_specialty: '园艺用品',
    compliance_risks: [
      '塑料/陶瓷/水泥材质需符合 REACH 与加州 65 号提案化学限量',
      '产品承重与稳定性需评估，避免倾倒伤人',
      '外观专利与园艺设计侵权风险需提前排查',
    ],
    cn_keywords: ['花盆', '塑料花盆', '陶瓷花盆', '多肉花盆'],
  },
  'baby stroller': {
    category: 'baby',
    avg_price: 160.0,
    price_range: [90.0, 350.0],
    rating: 4.3,
    reviews_level: 'high',
    trend: 'stable',
    pain_points: ['收车不便', '轮子不灵活', '重量沉', '避震差'],
    praised: ['一键收车', '推行顺滑', '可登机'],
    season_peak: [11, 12],
    certifications: ['ASTM F833 婴儿推车标准', 'CPC 儿童产品证书', 'EN 1888 认证'],
    supplier_city: '东莞',
    supplier_specialty: '母婴童车',
    compliance_risks: [
      '婴儿推车需符合 ASTM F833 / EN 1888 机械安全、刹车与稳定性测试',
      '面料与把手材质需符合 CPSIA 铅/邻苯二甲酸盐限量',
      '折叠锁定、安全带、车轮等关键部件需做可靠性测试',
    ],
    cn_keywords: ['婴儿推车', '轻便伞车', '可登机婴儿车', '高景观推车'],
  },
};

// ------------------------------------------------------------------
// 市场配置
// ------------------------------------------------------------------
interface MarketProfile {
  name: string;
  currency: string;
  price_mult: number;
  review_mult: number;
  shipping_premium: number;
  fba_premium: number;
  referral_adj: number;
}

const MARKET_PROFILES: Record<string, MarketProfile> = {
  US: { name: '美国站', currency: 'USD', price_mult: 1.0, review_mult: 1.0, shipping_premium: 0.0, fba_premium: 0.0, referral_adj: 0.0 },
  UK: { name: '英国站', currency: 'GBP', price_mult: 0.95, review_mult: 0.75, shipping_premium: 0.3, fba_premium: 0.2, referral_adj: 0.0 },
  DE: { name: '德国站', currency: 'EUR', price_mult: 0.92, review_mult: 0.7, shipping_premium: 0.4, fba_premium: 0.25, referral_adj: 0.01 },
  JP: { name: '日本站', currency: 'JPY', price_mult: 1.05, review_mult: 0.55, shipping_premium: 0.25, fba_premium: 0.15, referral_adj: 0.0 },
  CA: { name: '加拿大站', currency: 'CAD', price_mult: 1.0, review_mult: 0.6, shipping_premium: 0.35, fba_premium: 0.2, referral_adj: 0.0 },
};

// 相对市场规模指数，用于生成各国走势时区分量级（非真实销量，仅反映相对热度）
const MARKET_SIZE_INDEX: Record<string, number> = {
  US: 100,
  UK: 60,
  DE: 55,
  JP: 50,
  CA: 42,
};

// ------------------------------------------------------------------
// 工具函数
// ------------------------------------------------------------------
function seededRng(...args: (string | number)[]): {
  random: () => number;
  uniform: (a: number, b: number) => number;
  randint: (a: number, b: number) => number;
  choice: <T>(arr: T[]) => T;
  shuffle: <T>(arr: T[]) => T[];
  sample: <T>(arr: T[], k: number) => T[];
} {
  const text = args.join('|');
  let seed = 0;
  for (let i = 0; i < text.length; i++) {
    seed = ((seed << 5) - seed + text.charCodeAt(i)) | 0;
  }
  seed = Math.abs(seed);
  if (seed === 0) seed = 1;

  const next = () => {
    seed = (seed * 16807 + 0) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  return {
    random: next,
    uniform: (a: number, b: number) => a + next() * (b - a),
    randint: (a: number, b: number) => Math.floor(a + next() * (b - a + 1)),
    choice: <T>(arr: T[]) => arr[Math.floor(next() * arr.length)],
    shuffle: <T>(arr: T[]) => {
      const result = [...arr];
      for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(next() * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
      }
      return result;
    },
    sample: <T>(arr: T[], k: number) => {
      const shuffled = [...arr].sort(() => next() - 0.5);
      return shuffled.slice(0, Math.min(k, arr.length));
    },
  };
}

function resolveArchetype(keyword: string): ProductArchetype {
  const key = keyword.toLowerCase().trim();
  for (const k of Object.keys(ARCHETYPES)) {
    if (key.includes(k)) return ARCHETYPES[k];
  }
  const categoryMap: Record<string, ProductArchetype> = {
    pet: ARCHETYPES['dog chew toys'],
    dog: ARCHETYPES['dog chew toys'],
    cat: ARCHETYPES['cat toy'],
    yoga: ARCHETYPES['yoga mat'],
    fitness: ARCHETYPES['resistance bands'],
    'resistance band': ARCHETYPES['resistance bands'],
    'workout band': ARCHETYPES['resistance bands'],
    earbud: ARCHETYPES['wireless earbuds'],
    headphone: ARCHETYPES['wireless earbuds'],
    carplay: ARCHETYPES['carplay'],
    car: ARCHETYPES['carplay'],
    charger: ARCHETYPES['portable charger'],
    'power bank': ARCHETYPES['portable charger'],
    kitchen: ARCHETYPES['kitchen organizer'],
    organizer: ARCHETYPES['kitchen organizer'],
    makeup: ARCHETYPES['makeup brush'],
    brush: ARCHETYPES['makeup brush'],
    beauty: ARCHETYPES['face serum'],
    serum: ARCHETYPES['face serum'],
    skincare: ARCHETYPES['face serum'],
    'hair dryer': ARCHETYPES['hair dryer'],
    'water bottle': ARCHETYPES['water bottle'],
    'sports bottle': ARCHETYPES['sports water bottle'],
    bottle: ARCHETYPES['sports water bottle'],
    'running shoes': ARCHETYPES['running shoes'],
    shoes: ARCHETYPES['running shoes'],
    sneaker: ARCHETYPES['running shoes'],
    'phone case': ARCHETYPES['phone case'],
    'led strip': ARCHETYPES['led strip lights'],
    'led light': ARCHETYPES['led strip lights'],
    'baby bottle': ARCHETYPES['baby bottles'],
    baby: ARCHETYPES['baby bottles'],
    tent: ARCHETYPES['camping tent'],
    camping: ARCHETYPES['camping tent'],
    'smart watch': ARCHETYPES['smart watch'],
    'bluetooth speaker': ARCHETYPES['bluetooth speaker'],
    speaker: ARCHETYPES['bluetooth speaker'],
    'usb c cable': ARCHETYPES['usb c cable'],
    cable: ARCHETYPES['usb c cable'],
    'dog bed': ARCHETYPES['dog bed'],
    bed: ARCHETYPES['dog bed'],
    'storage box': ARCHETYPES['storage box'],
    'robot vacuum': ARCHETYPES['robot vacuum'],
    vacuum: ARCHETYPES['robot vacuum'],
    'plant pot': ARCHETYPES['plant pot'],
    'baby stroller': ARCHETYPES['baby stroller'],
    stroller: ARCHETYPES['baby stroller'],
  };
  for (const catKey of Object.keys(categoryMap)) {
    if (key.includes(catKey)) return categoryMap[catKey];
  }
  // 默认：基于关键词语义与长度生成稳定且符合商业逻辑的数据
  const rng = seededRng(key);
  const isElectronics = /(charger|cable|speaker|earbud|headphone|watch|robot|vacuum|strip|led|carplay|power)/.test(key);
  const isBeauty = /(serum|skincare|makeup|brush|hair|cream|lotion|cosmetic)/.test(key);
  const isBaby = /(baby|stroller|bottle|diaper|nipple|newborn|toddler)/.test(key);
  const isPet = /(dog|cat|pet|puppy|kitten|chew|bed)/.test(key);
  const isSports = /(yoga|fitness|running|gym|sports|tent|camping|bottle|shoes|band)/.test(key);

  let priceLow = 18.0, priceHigh = 55.0;
  if (isElectronics) { priceLow = 22.0; priceHigh = 89.0; }
  else if (isBaby) { priceLow = 25.0; priceHigh = 120.0; }
  else if (isSports) { priceLow = 16.0; priceHigh = 75.0; }
  else if (isBeauty) { priceLow = 12.0; priceHigh = 45.0; }
  else if (isPet) { priceLow = 12.0; priceHigh = 42.0; }

  const avgPrice = Math.round(rng.uniform(priceLow, priceHigh) * 100) / 100;
  const category = isElectronics ? 'electronics' : isBeauty ? 'beauty' : isBaby ? 'baby' : isPet ? 'pet_supplies' : isSports ? 'sports' : 'general';
  const supplierCity = isElectronics ? '深圳' : isBeauty ? '广州' : isBaby ? '东莞' : isPet ? '义乌' : isSports ? '泉州' : rng.choice(['深圳', '义乌', '广州', '东莞', '泉州']);
  const specialty = isElectronics ? '消费电子' : isBeauty ? '美妆护肤' : isBaby ? '母婴用品' : isPet ? '宠物用品' : isSports ? '运动户外' : '综合类目';

  return {
    category,
    avg_price: avgPrice,
    price_range: [
      Math.round(rng.uniform(priceLow * 0.55, priceLow * 0.85) * 100) / 100,
      Math.round(rng.uniform(avgPrice * 1.15, avgPrice * 1.55) * 100) / 100,
    ],
    rating: Math.round(rng.uniform(4.0, 4.7) * 10) / 10,
    reviews_level: rng.choice(['low', 'medium', 'high'] as const),
    trend: rng.choice(['rising', 'stable', 'falling'] as const),
    pain_points: ['质量参差不齐', '物流时效不稳定', '售后响应慢'],
    praised: ['功能实用', '性价比高'],
    season_peak: [11, 12],
    certifications: ['CE 认证', 'FDA 认证（如适用）'],
    supplier_city: supplierCity,
    supplier_specialty: specialty,
    compliance_risks: [
      '通用类目需确认目标市场强制认证（CE/FCC/UKCA 等）与标签语言要求',
      '产品外观与功能需排查目标市场专利、商标与版权风险',
      '建议根据具体材质与使用场景补充化学、机械及电气安全测试',
    ],
    cn_keywords: ['外贸爆款', '跨境电商货源', '工厂直销'],
  };
}

function getMarketProfile(market: string): MarketProfile {
  return MARKET_PROFILES[market.toUpperCase()] || MARKET_PROFILES.US;
}

// ------------------------------------------------------------------
// 竞品生成
// ------------------------------------------------------------------
function generateCompetitors(
  rng: ReturnType<typeof seededRng>,
  archetype: ProductArchetype,
  keyword: string,
  market: string
): any[] {
  const profile = getMarketProfile(market);
  const baseStores = [
    { brand: 'AmaBest', store: 'AmaBest Direct', color: '#2563eb' },
    { brand: 'PetPro', store: 'PetPro Home', color: '#0891b2' },
    { brand: 'HomePlus', store: 'HomePlus Living', color: '#7c3aed' },
    { brand: 'TechZone', store: 'TechZone Official', color: '#db2777' },
    { brand: 'EcoLife', store: 'EcoLife Shop', color: '#16a34a' },
    { brand: 'PrimePick', store: 'PrimePick Store', color: '#ea580c' },
    { brand: 'NovaGear', store: 'NovaGear Mall', color: '#0f766e' },
    { brand: 'Zenith', store: 'Zenith Select', color: '#4338ca' },
    { brand: 'BlueWave', store: 'BlueWave Mart', color: '#b91c1c' },
    { brand: 'OptiMax', store: 'OptiMax Outlet', color: '#0369a1' },
  ];
  const extraBrands = [
    'Swift', 'TrueLine', 'EverCore', 'MaxVibe', 'PureNest', 'AlphaGear', 'VitalPeak', 'SmartHome',
    'UrbanLeaf', 'CloudNine', 'BrightFox', 'IronClad', 'SoftWave', 'PowerBolt', 'CrystalMark',
    'EcoNest', 'ProLine', 'ReliaGoods', 'FusionX', 'NatureBeat', 'UrbanFit', 'ZenMode',
    'HyperCore', 'SoftTouch', 'EverBright', 'PrimeNest', 'SolidBase', 'FlexiPro', 'DailyJoy',
    'NextWave', 'TrueFit', 'SafeHaven', 'HappyNest', 'SmartChoice', 'ComfortZone', 'ActiveLife',
    'CleanSlate', 'DreamGear', 'ReadySet', 'SteadyPro',
  ];
  const extraColors = [
    '#0ea5e9', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#06b6d4', '#84cc16',
    '#6366f1', '#14b8a6', '#f97316', '#d946ef', '#22c55e', '#3b82f6', '#eab308', '#a855f7',
    '#64748b', '#b91c1c', '#0d9488', '#7c3aed', '#be123c', '#047857', '#4338ca', '#9f1239',
    '#15803d', '#1d4ed8', '#c2410c', '#7e22ce', '#a16207', '#115e59', '#1e40af', '#9a3412',
    '#6b21a8', '#3f6212', '#92400e', '#701a75', '#14532d', '#1e3a8a', '#713f12', '#4c0519',
  ];
  const stores = [
    ...baseStores,
    ...extraBrands.map((b, i) => ({ brand: b, store: `${b} Store`, color: extraColors[i % extraColors.length] })),
  ];
  const shuffledStores = rng.shuffle(stores);
  const suffixes = ['Premium', 'Pro', 'Elite', 'Ultra', 'Classic', 'Lite', 'Plus', 'Max', 'Essential', 'Signature'];
  const searchLink = `https://www.amazon.com/s?k=${encodeURIComponent(keyword)}`;

  const keywordSeed = keyword.toLowerCase().split('').reduce((acc, c) => ((acc << 5) - acc + c.charCodeAt(0)) | 0, 0);
  const keywordRng = seededRng(String(Math.abs(keywordSeed)));
  const marketSizeFactor = keywordRng.uniform(0.5, 2.5);
  const saturation = keywordRng.uniform(0.6, 1.4);

  const products = [];
  for (let i = 0; i < 50; i++) {
    const storeInfo = shuffledStores[i % shuffledStores.length];
    const priceNoise = rng.uniform(0.92, 1.12);
    const price = Math.round(rng.uniform(archetype.price_range[0], archetype.price_range[1]) * profile.price_mult * priceNoise * 100) / 100;
    const rating = Math.round(Math.max(3.5, Math.min(5.0, archetype.rating + rng.uniform(-0.4, 0.3))) * 10) / 10;
    const reviewBase = archetype.reviews_level === 'high' ? 800 : 200;
    const reviewTop = archetype.reviews_level === 'high' ? 38000 : 8000;
    const reviewCount = Math.round(rng.randint(reviewBase, reviewTop) * profile.review_mult);

    let bsr: number;
    if (i === 0) bsr = rng.randint(300, 2500);
    else if (i <= 10) bsr = rng.randint(1500, 8000);
    else if (i <= 25) bsr = rng.randint(6000, 25000);
    else bsr = rng.randint(20000, 90000);
    bsr = Math.max(200, Math.round(bsr * rng.uniform(0.85, 1.15)));

    const logRank = Math.max(1, Math.log(bsr));
    const baseSales = Math.round(25000 / logRank * marketSizeFactor);
    const monthlySales = Math.max(10, Math.round(baseSales * rng.uniform(0.85, 1.25) / saturation));

    products.push({
      asin: '',
      title: `${storeInfo.brand} ${keyword.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')} ${rng.choice(suffixes)}`,
      subtitle: `${storeInfo.store} · ${archetype.category.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}`,
      brand: storeInfo.brand,
      store: storeInfo.store,
      price,
      rating,
      review_count: reviewCount,
      bsr,
      estimated_monthly_sales: monthlySales,
      image: `https://placehold.co/80x80/${storeInfo.color.replace('#', '')}/ffffff?text=${encodeURIComponent(storeInfo.brand[0])}`,
      link: searchLink,
      color: storeInfo.color,
    });
  }
  products.sort((a, b) => a.bsr - b.bsr);
  return products;
}

// ------------------------------------------------------------------
// 趋势数据
// ------------------------------------------------------------------
function generateTrendSeries(rng: ReturnType<typeof seededRng>, archetype: ProductArchetype) {
  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1; // 1-12

  // 生成全年 12 个月基础季节性曲线
  const baseValues: number[] = [];
  for (let i = 0; i < 12; i++) {
    const monthIdx = i + 1;
    let val = 45 + rng.randint(-10, 12);
    if (archetype.season_peak.includes(monthIdx)) val += rng.randint(35, 50);
    if (archetype.trend === 'rising') val += Math.round(i * 0.9);
    else if (archetype.trend === 'falling') val -= Math.round(i * 0.7);
    baseValues.push(Math.max(15, Math.min(100, val)));
  }

  // 为每一年生成略有差异的月度数据
  const yearlyData: Record<number, { months: string[]; values: number[] }> = {};
  for (let year = currentYear - 2; year <= currentYear; year++) {
    const isCurrentYear = year === currentYear;
    const availableMonths = isCurrentYear ? currentMonth - 1 : 12;
    const yearRngOffset = (year - currentYear) * 7;
    const yearValues = baseValues.map((v, i) => {
      if (i >= availableMonths) return null as unknown as number;
      return Math.max(15, Math.min(100, v + yearRngOffset + rng.randint(-12, 10)));
    }).slice(0, availableMonths);
    yearlyData[year] = {
      months: months.slice(0, availableMonths),
      values: yearValues,
    };
  }

  // 本年度 1-12 月：已有月份用真实数据，未发生月份用去年同期推算
  const currentYearValues = baseValues.map((_, i) => {
    if (i < currentMonth - 1) {
      return yearlyData[currentYear].values[i];
    }
    return Math.max(15, Math.min(100, yearlyData[currentYear - 1].values[i] + rng.randint(-8, 8)));
  });

  // 去年同期（完整 12 个月）
  const lastYear = yearlyData[currentYear - 1].values.map(v => Math.max(15, Math.min(100, v + rng.randint(-5, 5))));

  // 近 12 个月：从去年当前月份到本年度上个月
  const trailingLabels: string[] = [];
  const trailingValues: number[] = [];
  const trailingLastYear: number[] = [];
  for (let i = 0; i < 12; i++) {
    let year: number;
    let month: number;
    if (i < currentMonth - 1) {
      year = currentYear;
      month = currentMonth - 1 - i;
    } else {
      year = currentYear - 1;
      month = 12 - (i - (currentMonth - 1));
    }
    const label = `${year}年${month}月`;
    trailingLabels.push(label);
    const prevYear = year - 1;
    const val = yearlyData[year]?.values[month - 1] ?? baseValues[month - 1];
    const lyVal = yearlyData[prevYear]?.values[month - 1] ?? baseValues[month - 1];
    trailingValues.push(val);
    trailingLastYear.push(Math.max(15, Math.min(100, lyVal + rng.randint(-5, 5))));
  }
  trailingLabels.reverse();
  trailingValues.reverse();
  trailingLastYear.reverse();

  // 预测：结合最近 3 个月动量 + 去年同期同月季节性，避免平直/失真
  const forecast: number[] = [];
  const actualSoFar = currentYearValues.slice(0, currentMonth - 1).filter((v): v is number => v != null);
  const lastVal = actualSoFar[actualSoFar.length - 1] ?? 50;
  const last3 = actualSoFar.slice(-3);
  const slope = last3.length >= 2 ? (last3[last3.length - 1] - last3[0]) / (last3.length - 1) : 0;
  for (let i = 1; i <= 3; i++) {
    const futureMonthIdx = (currentMonth - 1 + i - 1) % 12; // 预测目标月在去年的同月索引
    const seasonalBase = lastYear[futureMonthIdx] ?? lastVal;
    const momentum = lastVal + slope * i * 0.7;
    const blended = momentum * 0.6 + seasonalBase * 0.4;
    forecast.push(Math.max(15, Math.min(100, Math.round(blended + rng.randint(-5, 5)))));
  }

  return {
    months,
    values: currentYearValues,
    last_year_values: lastYear,
    forecast_values: forecast,
    forecast_months: ['+1月', '+2月', '+3月'],
    yearly_data: yearlyData,
    trailing_12_months: { labels: trailingLabels, values: trailingValues, last_year_values: trailingLastYear },
  };
}

function detectPeakMonths(values: number[], topN = 2): number[] {
  const indexed = values.map((v, i) => ({ month: i + 1, value: v }));
  indexed.sort((a, b) => b.value - a.value);
  return indexed.slice(0, topN).map(x => x.month).sort((a, b) => a - b);
}

function detectEntryWindows(values: number[], peakMonths: number[], windowSize = 2): number[] {
  const candidates = new Set<number>();
  for (const peak of peakMonths) {
    for (let offset = 2; offset < 7; offset++) {
      let m = peak - offset;
      if (m <= 0) m += 12;
      candidates.add(m);
    }
  }
  for (const peak of peakMonths) candidates.delete(peak);

  const indexed = Array.from(candidates).map(m => ({ month: m, value: values[m - 1] }));
  indexed.sort((a, b) => a.value - b.value);
  return indexed.slice(0, windowSize).map(x => x.month).sort((a, b) => a - b);
}

function buildSeasonNarrative(peakMonths: number[], entryMonths: number[], trendDirection: string) {
  const peakStr = peakMonths.map(m => `${m}月`).join('、');
  const entryStr = entryMonths.map(m => `${m}月`).join('、');

  const narrativeMap: Record<string, string> = {
    '11,12': '年末礼品季 + 黑五网一（BFCM）大促驱动，Q4 是全年需求顶点。',
    '12,1': '跨年 + 新年消费/健身/整理类需求高峰，圣诞后返场与 New Year Resolution 叠加。',
    '6,7': '夏季户外/度假/宠物出行旺季，高温场景带动相关产品需求。',
    '7,8': '返校季（Back to School）与夏末户外尾峰叠加。',
    '3,4': '春季换季 + 复活节/家居焕新需求上升。',
    '9,10': 'Prime Day 返场 / 早鸟假日购物启动，需求开始爬坡。',
  };
  const key = peakMonths.sort((a, b) => a - b).join(',');
  const seasonDesc = narrativeMap[key] || `需求高峰集中在 ${peakStr}，建议围绕该时段前置备货与广告投放。`;
  const trendDesc = {
    rising: '整体搜索热度呈上升态势，类目处于成长期。',
    stable: '全年热度相对平稳，无明显爆发性增长。',
    falling: '整体搜索热度呈下滑态势，需警惕类目衰退风险。',
  }[trendDirection] || '';

  return {
    peak_months: peakStr,
    entry_months: entryStr,
    season_desc: seasonDesc,
    trend_desc: trendDesc,
  };
}

// ------------------------------------------------------------------
// 全球市场走势（多国家对比）
// ------------------------------------------------------------------
function buildGlobalTrends(keyword: string, archetype: ProductArchetype) {
  return Object.entries(MARKET_PROFILES).map(([code, profile]) => {
    const rng = seededRng(keyword, code);
    const series = generateTrendSeries(rng, archetype);
    const size = MARKET_SIZE_INDEX[code] || 60;
    const scale = size / 100;
    const scaleValues = (vals: number[]) => vals.map((v) => Math.round(v * scale));
    const yearlyData: Record<number, { months: string[]; values: number[] }> = {};
    if (series.yearly_data) {
      for (const [year, data] of Object.entries(series.yearly_data)) {
        yearlyData[Number(year)] = {
          months: data.months,
          values: scaleValues(data.values),
        };
      }
    }
    const trailing = series.trailing_12_months
      ? {
          labels: series.trailing_12_months.labels,
          values: scaleValues(series.trailing_12_months.values),
        }
      : undefined;
    return {
      code,
      name: profile.name,
      months: series.months,
      values: series.values.map((v) => Math.round(v * scale)),
      market_size_index: size,
      yearly_data: yearlyData,
      trailing_12_months: trailing,
    };
  });
}

// ------------------------------------------------------------------
// 供应商生成
// ------------------------------------------------------------------
function generateSuppliers(
  rng: ReturnType<typeof seededRng>,
  keyword: string,
  archetype: ProductArchetype,
  market: string
): any[] {
  const city = archetype.supplier_city;
  const specialty = archetype.supplier_specialty;
  const profile = getMarketProfile(market);

  const districtMap: Record<string, string[]> = {
    '深圳': ['龙华区', '宝安区', '龙岗区', '南山区', '光明区'],
    '东莞': ['长安镇', '虎门镇', '塘厦镇', '厚街镇', '大朗镇'],
    '广州': ['白云区', '番禺区', '花都区', '天河区', '海珠区'],
    '义乌': ['稠江街道', '江东街道', '北苑街道', '福田街道', '廿三里街道'],
    '泉州': ['晋江市', '南安市', '石狮市', '惠安县', '安溪县'],
  };
  const districts = rng.shuffle(districtMap[city] || ['市区', '高新区', '经开区']);

  const namePrefixes = rng.shuffle([
    '领航', '盛达', '众诚', '创联', '宏图', '亿帆', '拓海', '锦程', '博远', '锐捷',
    '恒信', '腾飞', '鑫源', '天成', '东方', '华宇', '金辉', '星辰', '远航', '卓越',
    '伟业', '聚丰', '昌隆', '凯瑞', '明德', '正泰', '兴达', '永泰', '汇丰', '瑞祥',
    '龙翔', '凤舞', '国泰', '民安', '富邦', '荣耀', '智汇', '云程', '海川', '光辉',
    '鹏程', '天佑', '祥瑞', '安顺', '康泰', '益民', '立信', '精诚', '弘毅', '德润',
  ]);

  const hotProducts = [
    '热门爆款 A', '热销单品 B', '市场潜力款 C', '季节主推款 D', '长尾稳定款 E',
    '经典款 F', '新品 G', '升级款 H', '限量款 I', '定制款 J',
    '旗舰款 K', '入门款 L', '专业款 M', '轻便款 N', '豪华款 O',
    '环保款 P', '智能款 Q', '便携款 R', '多功能款 S', '高性价比款 T',
  ];
  const shuffledHot = rng.shuffle(hotProducts);

  const supplierPool: Array<{
    name: string;
    moq: string;
    lead_time: string;
    rating: number;
    capacity: string;
    sample_days: number;
    response_rate: number;
  }> = [];

  for (let i = 0; i < 50; i++) {
    const district = districts[i % districts.length];
    const prefix = namePrefixes[i % namePrefixes.length];
    let name: string;
    if (i % 3 === 0) name = `${city}${district}${prefix}${specialty}厂`;
    else if (i % 3 === 1) name = `${prefix}${specialty}（${city}${district}）`;
    else name = `${city}${prefix}${specialty}供应链`;

    supplierPool.push({
      name,
      moq: rng.choice(['MOQ 100', 'MOQ 200', 'MOQ 300', 'MOQ 500', 'MOQ 800', 'MOQ 1000']),
      lead_time: rng.choice(['5-8 天', '7-12 天', '10-15 天', '12-18 天', '15-20 天']),
      rating: Math.round(rng.uniform(4.1, 4.9) * 10) / 10,
      capacity: rng.choice(['日产 2K', '日产 5K', '日产 8K', '日产 12K', '日产 20K']),
      sample_days: rng.randint(3, 10),
      response_rate: rng.randint(85, 99),
    });
  }
  supplierPool.sort((a, b) => b.rating - a.rating);

  return supplierPool.map((s, rank) => {
    const unitCost = Math.round(rng.uniform(archetype.price_range[0], archetype.price_range[1]) * rng.uniform(0.18, 0.34) * profile.price_mult * 100) / 100;
    const hotName = shuffledHot[rank % shuffledHot.length];

    return {
      rank: rank + 1,
      name: s.name,
      moq: s.moq,
      lead_time: s.lead_time,
      rating: s.rating,
      capacity: s.capacity,
      sample_days: s.sample_days,
      response_rate: s.response_rate,
      unit_cost: unitCost,
      sample_cost: Math.round(unitCost * 3 * 100) / 100,
      years: rng.randint(5, 18),
      transactions: rng.randint(120, 1800),
      hot_categories: [hotName, shuffledHot[(rank + 1) % shuffledHot.length]],
      hot_product_image: `https://placehold.co/100x100/334155/ffffff?text=${encodeURIComponent(hotName[0])}`,
      hot_product_name: hotName,
      // 使用原始关键词（多为英文）生成 1688 搜索链接，避免中文编码乱码；空格统一用 + 更符合搜索引擎表单习惯
      link_1688: `https://s.1688.com/selloffer/offer_search.htm?keywords=${encodeURIComponent(keyword).replace(/%20/g, '+')}`,
    };
  });
}

// ------------------------------------------------------------------
// 利润计算
// ------------------------------------------------------------------
function calculateProfit(
  sellingPrice: number,
  unitCost: number,
  category: string,
  market: string
) {
  const profile = getMarketProfile(market);
  const referralRates: Record<string, number> = {
    pet_supplies: 0.15,
    electronics: 0.08,
    sports: 0.15,
    home_kitchen: 0.15,
    beauty: 0.15,
    baby: 0.15,
    general: 0.15,
  };
  const rate = Math.min(0.20, (referralRates[category] || 0.15) + profile.referral_adj);
  const fbaFee = (['pet_supplies', 'baby', 'beauty'].includes(category) ? 3.22 : ['sports'].includes(category) ? 4.20 : 4.80) + profile.fba_premium;
  const shipping = 2.0 + profile.shipping_premium;
  const advertising = sellingPrice * 0.08;
  const returnAllowance = sellingPrice * 0.03;
  const misc = 0.50;

  // 基准单位经济
  const totalCost = unitCost + shipping + fbaFee + sellingPrice * rate + advertising + returnAllowance + misc;
  const baseGrossProfit = sellingPrice - totalCost;
  const baseGrossMargin = sellingPrice > 0 ? baseGrossProfit / sellingPrice : 0;

  // ROI 动态模型：投资随销量增加而增加（按销量备货 + 固定运营费用）
  const inventoryMonths = 2; // 安全库存月数
  const monthlyFixed = 2000; // 月度固定运营成本
  const scenarios: Record<string, any> = {};

  // 不同情景不仅销量不同，也对应不同的成本/售价假设，因此毛利率会不同
  const scenarioAssumptions: Record<string, { sales: number; costFactor: number; adFactor: number; priceFactor: number }> = {
    保守: { sales: 100, costFactor: 1.12, adFactor: 1.25, priceFactor: 0.95 },
    中性: { sales: 300, costFactor: 1.0, adFactor: 1.0, priceFactor: 1.0 },
    乐观: { sales: 600, costFactor: 0.90, adFactor: 0.80, priceFactor: 1.08 },
  };

  for (const [name, { sales, costFactor, adFactor, priceFactor }] of Object.entries(scenarioAssumptions)) {
    const scenarioUnitCost = unitCost * costFactor;
    const scenarioAd = advertising * adFactor;
    const scenarioPrice = sellingPrice * priceFactor;
    const scenarioCommission = scenarioPrice * rate;
    const scenarioReturn = scenarioPrice * 0.03;
    const scenarioTotalCost = scenarioUnitCost + shipping + fbaFee + scenarioCommission + scenarioAd + scenarioReturn + misc;
    const scenarioGrossProfit = scenarioPrice - scenarioTotalCost;
    const scenarioGrossMargin = scenarioPrice > 0 ? scenarioGrossProfit / scenarioPrice : 0;
    const scenarioLandingCost = scenarioUnitCost + shipping;

    const monthlyNetProfit = sales * scenarioGrossProfit - monthlyFixed;
    const inventoryUnits = Math.round(sales * inventoryMonths);
    const investment = inventoryUnits * scenarioLandingCost + monthlyFixed;
    const roi = investment > 0 ? (monthlyNetProfit / investment) * 100 : 0;
    const payback = monthlyNetProfit > 0 ? investment / monthlyNetProfit : null;
    scenarios[name] = {
      '月销量': sales,
      '月毛利': Math.round(monthlyNetProfit * 100) / 100,
      '毛利率': `${(scenarioGrossMargin * 100).toFixed(1)}%`,
      'ROI': Math.round(roi * 10) / 10,
      '回本周期': payback ? Math.round(payback * 10) / 10 : null,
    };
  }

  const costBreakdown: Record<string, number> = {
    '产品成本': unitCost,
    '头程物流': shipping,
    'FBA 费用': fbaFee,
    '平台佣金': sellingPrice * rate,
    '广告费用': advertising,
    '退货预留': returnAllowance,
    '其他杂费': misc,
  };

  return {
    selling_price: sellingPrice,
    unit_cost: unitCost,
    total_cost_per_unit: Math.round(totalCost * 100) / 100,
    gross_profit_per_unit: Math.round(baseGrossProfit * 100) / 100,
    gross_margin: baseGrossMargin,
    gross_margin_pct: `${(baseGrossMargin * 100).toFixed(1)}%`,
    cost_breakdown: costBreakdown,
    cost_breakdown_pct: Object.fromEntries(
      Object.entries(costBreakdown).map(([k, v]) => [k, `${((v / totalCost) * 100).toFixed(1)}%`])
    ),
    roi_scenarios: scenarios,
    breakeven_units: baseGrossProfit > 0 ? Math.round(monthlyFixed / baseGrossProfit) : null,
  };
}

// ------------------------------------------------------------------
// 合规信息
// ------------------------------------------------------------------
function buildCompliance(
  rng: ReturnType<typeof seededRng>,
  archetype: ProductArchetype,
  market: string
) {
  const profile = getMarketProfile(market);
  const certifications = [...archetype.certifications];

  const marketCertAdditions: Record<string, string[]> = {
    US: ['FCC 认证（如含电子）', 'CPSC/CPC（如儿童/宠物相关）'],
    UK: ['UKCA 标识', '英国授权代表'],
    DE: ['CE 标识 + 欧代', '德国包装法 EPR/VerpackG 注册'],
    JP: ['PSE 标志（如电子）', 'TELEC/MIC（如无线）', '日语标签/说明书'],
    CA: ['IC 认证（如含电子）', '英法双语标签'],
  };
  for (const cert of marketCertAdditions[market.toUpperCase()] || []) {
    if (!certifications.includes(cert)) certifications.push(cert);
  }

  const dbNames: Record<string, string> = {
    US: 'USPTO / Google Patents',
    UK: 'UK IPO / EUIPO',
    DE: 'EUIPO / DPMA',
    JP: 'J-PlatPat / JPO',
    CA: 'CIPO / USPTO',
  };
  const dbName = dbNames[market.toUpperCase()] || '当地专利局';

  const designPatentRisks = [
    `${profile.name} 常见外观设计专利覆盖本产品主流造型，建议上架前通过 ${dbName} 做专利检索。`,
    '产品外观若与头部竞品高度相似，存在被投诉下架或 TRO（临时限制令）风险。',
    `请确认上市设计不落入他人 ${profile.name} 外观专利保护范围。`,
  ];

  const tmDbs: Record<string, string> = {
    US: 'USPTO TESS',
    UK: 'UK IPO 商标检索',
    DE: 'EUIPO eSearch',
    JP: 'J-PlatPat 商标库',
    CA: 'CIPO 商标库',
  };
  const brandRisks = [
    `避免使用 ${profile.name} 已注册商标的通用词或近似 Logo，建议通过 ${tmDbs[market.toUpperCase()] || '当地商标局'} 做筛查。`,
    'Listing 文案、图片、包装中勿出现影视/动漫/游戏角色、球队、品牌联名等未授权元素。',
    `${profile.name} 对品牌侵权处罚严格，可能导致账户资金冻结或链接下架。`,
  ];

  const industryPatentRisks = [
    `${archetype.category.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')} 类目存在若干功能型专利，需排查核心结构/材料在 ${profile.name} 是否侵权。`,
    '若产品含电子、机械或特殊材料组件，建议做 Freedom-to-Operate（FTO）分析。',
    '供应链端需确认工厂拥有相关设计授权，避免 OEM 侵权连带责任。',
  ];

  const marketRules: Record<string, string[]> = {
    US: [
      '儿童/宠物用品需关注 CPSC 安全标准与 CPC 证书要求。',
      '含电子部件需 FCC 认证；食品接触材料需 FDA 合规。',
      `针对「${archetype.category.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}」类目，确认是否需要第三方实验室检测报告。`,
    ],
    UK: [
      '需 UKCA 标识及英国授权代表。',
      '产品安全与 GPSR 相关义务需同步满足。',
      `针对「${archetype.category.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}」类目，确认是否需要英国本土合规文件。`,
    ],
    DE: [
      '需 CE 标识 + 欧代信息，部分产品需 ROHS/REACH 化学检测。',
      '包装需符合 EPR 法规（德国包装法、法国 Triman 标识等）。',
      `针对「${archetype.category.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}」类目，确认是否需要符合 GPSR 通用产品安全法规。`,
    ],
    JP: [
      '无线电/电子类产品需 TELEC/MIC 认证；食品接触类需食品卫生法。',
      '日语标签、说明书及 PSE 标志（如适用）需提前准备。',
      `针对「${archetype.category.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}」类目，确认是否需要日本进口商/代理商信息。`,
    ],
    CA: [
      '需符合加拿大消费品安全法（CCPSA）及双语标签要求。',
      '含电子部件需 IC 认证；食品接触材料需 Health Canada 合规。',
      `针对「${archetype.category.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}」类目，确认是否需要加拿大本地安全标准测试。`,
    ],
  };
  const marketSpecific = marketRules[market.toUpperCase()] || marketRules.US;

  return {
    certifications,
    risk_level: rng.choice(['低', '中', '高']),
    estimated_cert_cost: Math.round(rng.uniform(500, 3500) * profile.price_mult * 100) / 100,
    estimated_cert_time: rng.choice(['2-4 周', '4-6 周', '6-8 周', '8-12 周']),
    category_risks: rng.sample(archetype.compliance_risks, Math.min(3, archetype.compliance_risks.length)),
    design_patent_risks: rng.sample(designPatentRisks, Math.min(2, designPatentRisks.length)),
    brand_risks: rng.sample(brandRisks, Math.min(2, brandRisks.length)),
    industry_patent_risks: rng.sample(industryPatentRisks, Math.min(2, industryPatentRisks.length)),
    market_specific: marketSpecific,
    market: profile.name,
  };
}

// ------------------------------------------------------------------
// 行动计划
// ------------------------------------------------------------------
function buildNextSteps(report: any): any[] {
  const keyword = report.keyword;
  const market = report.market;
  const archetype = resolveArchetype(keyword);
  const pain1 = archetype.pain_points[0];
  const pain2 = archetype.pain_points[1] || archetype.pain_points[0];
  const cert1 = archetype.certifications[0];
  const cert2 = archetype.certifications[1] || cert1;
  const peak = report.trend_analysis.peak_months.map((m: number) => `${m}月`).join('、');
  const entry = report.trend_analysis.entry_windows.map((m: number) => `${m}月`).join('、');

  return [
    {
      phase: 'Week 1-2',
      title: '供应商开发与样品验证',
      owner: '供应链专员 / 采购',
      tasks: [
        `针对「${pain1}」「${pain2}」筛选 3-5 家可定向改良的工厂`,
        '索取样品、核验材质/工艺、对比报价与交期',
        '确认工厂资质（ISO、BSCI、相关认证）与产能匹配度',
      ],
      value: '锁定具备差异化改良能力的供应商，降低质量与交付风险。',
    },
    {
      phase: 'Week 3-4',
      title: '合规与知识产权风控',
      owner: '合规专员 / 法务',
      tasks: [
        `完成 ${cert1}、${cert2} 认证方案与预算评估`,
        `在 ${market} 市场进行商标/外观专利/功能专利检索`,
        '设计独立包装与 Listing 素材，规避侵权风险',
      ],
      value: '避免上架后因合规或 TRO 导致链接下架、资金冻结。',
    },
    {
      phase: `${entry} 前`,
      title: '备货与物流布局',
      owner: '运营 / 物流',
      tasks: [
        `在 ${entry} 完成首批 300-500 件备货并发出`,
        '选择海运/空运组合，确保旺季前 4-6 周到仓',
        '建立安全库存预警：按日销 30-50 件设置补货点',
      ],
      value: `抢占 ${peak} 旺季搜索排名，避免断货错失销售高峰。`,
    },
    {
      phase: `${peak} 旺季`,
      title: 'Listing 优化与广告投放',
      owner: '亚马逊运营',
      tasks: [
        '围绕用户好评卖点优化标题、五点、A+ 与主图视频',
        '启动自动+手动广告，预算按 ROI 分阶段释放',
        '监控 BSR、广告 ACoS、Review 增长率与退货原因',
      ],
      value: '提升转化率与广告效率，实现盈亏平衡后的利润放大。',
    },
    {
      phase: '持续迭代',
      title: '数据复盘与产品迭代',
      owner: '产品 / 运营',
      tasks: [
        '每周复盘退货率、Review 差评点与竞品动态',
        '基于真实用户反馈启动 V2.0 改良（材质/功能/包装）',
        '建立供应商绩效评分表，季度优化供应链结构',
      ],
      value: '形成数据驱动的选品-备货-销售-迭代闭环。',
    },
  ];
}

// ------------------------------------------------------------------
// 趋势产品
// ------------------------------------------------------------------
function generateTrendingProducts(rng: ReturnType<typeof seededRng>, keyword: string): any[] {
  const seeds = rng.shuffle([
    'automatic', 'interactive', 'organic', 'silicone', 'foldable',
    'wireless', 'rechargeable', 'portable', 'smart', 'eco-friendly',
  ]);
  return seeds.slice(0, 4).map(seed => ({
    keyword: `${seed} ${keyword}`,
    growth_pct: rng.randint(15, 85),
    competition: rng.choice(['低', '中', '高']),
    opportunity: rng.randint(15, 85) > 50 && rng.random() > 0.5 ? '高' : '中',
  }));
}

// ------------------------------------------------------------------
// 细分关键词机会
// ------------------------------------------------------------------
const KEYWORD_MODIFIERS: Record<string, string[]> = {
  default: ['best', 'top rated', 'premium', 'affordable', 'with', 'for', 'set of', 'bundle', 'heavy duty', 'adjustable', 'professional', 'compact'],
  pet_supplies: ['interactive', 'automatic', 'durable', 'chew resistant', 'catnip', 'squeaky', 'plush', 'treat dispensing', 'feather', 'mouse', 'ball', 'scratch'],
  sports: ['insulated', 'leak proof', 'BPA free', 'large capacity', 'collapsible', 'with straw', 'gym', 'cycling', '32 oz', 'running', 'fitness', 'lightweight'],
  electronics: ['wireless', 'bluetooth', 'noise cancelling', 'gaming', 'sport', 'waterproof', 'magnetic', 'fast charging', 'long battery', 'tws', 'mini', 'open ear'],
  home_kitchen: ['stackable', 'space saving', 'rust proof', 'magnetic', 'adjustable', 'expandable', 'with lid', 'organizer', 'over sink', 'cabinet', 'drawer', 'wall mount'],
  beauty: ['organic', 'vegan', 'travel size', 'professional', 'salon grade', 'with brush', 'set', 'natural', 'cruelty free', 'hypoallergenic', 'premium', 'soft'],
  baby: ['non toxic', 'BPA free', 'soft', 'washable', 'portable', 'travel', 'newborn', 'toddler', 'anti colic', 'silicone', 'gentle', 'easy clean'],
};

function buildKeywordOpportunities(
  rng: ReturnType<typeof seededRng>,
  keyword: string,
  category: string,
  competitors: any[]
): AnalysisReport['market_analysis']['keyword_opportunities'] {
  const modifiers = KEYWORD_MODIFIERS[category] || KEYWORD_MODIFIERS.default;
  const shuffled = rng.shuffle([...modifiers]);
  const count = Math.min(12, Math.max(10, modifiers.length));
  const trends: Array<'rising' | 'stable' | 'falling'> = ['rising', 'rising', 'stable', 'stable', 'falling'];
  const competitions: Array<'low' | 'medium' | 'high'> = ['low', 'low', 'medium', 'medium', 'medium', 'high'];

  return shuffled.slice(0, count).map((modifier) => {
    const kw = `${modifier} ${keyword}`;
    const searchVolume = rng.randint(1200, 18500);
    const trend = rng.choice(trends);
    const competition = rng.choice(competitions);
    const cpc = Math.round(rng.uniform(0.45, 3.2) * 100) / 100;
    const trendBoost = trend === 'rising' ? 1.2 : trend === 'stable' ? 1.0 : 0.8;
    const compBoost = competition === 'low' ? 1.3 : competition === 'medium' ? 1.0 : 0.7;
    const opportunityScore = Math.round(Math.min(100, (searchVolume / 200) * trendBoost * compBoost));
    const productCount = rng.randint(2, 3);
    const products = rng.shuffle(competitors).slice(0, productCount).map((p) => {
      const bg = p.color && p.color.startsWith('#') ? p.color.replace('#', '') : '2563eb';
      const initial = p.brand ? p.brand[0] : 'P';
      return {
        ...p,
        title: `${p.brand} ${kw.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}`,
        image: `https://placehold.co/80x80/${bg}/ffffff?text=${encodeURIComponent(initial)}`,
        link: `https://www.amazon.com/s?k=${encodeURIComponent(kw)}`,
      };
    });

    return {
      keyword: kw,
      search_volume: searchVolume,
      trend,
      competition,
      opportunity_score: opportunityScore,
      cpc,
      products,
    };
  }).sort((a, b) => b.opportunity_score - a.opportunity_score);
}

// ------------------------------------------------------------------
// 关键词关系网络与拓品建议
// ------------------------------------------------------------------
const SEGMENT_RULES = [
  { key: 'quality', label: '品质升级型', words: ['best', 'top rated', 'premium', 'professional', 'salon grade', 'heavy duty', 'durable', 'top'] },
  { key: 'price', label: '性价比/组合型', words: ['affordable', 'cheap', 'budget', 'bundle', 'set of', 'value', 'pack', 'deal'] },
  { key: 'feature', label: '功能创新型', words: ['wireless', 'bluetooth', 'noise cancelling', 'fast charging', 'magnetic', 'adjustable', 'foldable', 'compact', 'automatic', 'interactive', 'smart', 'portable', 'rechargeable', 'waterproof', 'leak proof', 'insulated', 'collapsible', 'with'] },
  { key: 'use_case', label: '场景细分型', words: ['for', 'gym', 'running', 'cycling', 'travel', 'kitchen', 'baby', 'cat', 'dog', 'toddler', 'newborn', 'camping', 'sports', 'fitness', 'outdoor', 'home', 'office'] },
  { key: 'material', label: '材质安全型', words: ['organic', 'vegan', 'bpa free', 'bpa-free', 'non toxic', 'non-toxic', 'silicone', 'cruelty free', 'cruelty-free', 'hypoallergenic', 'natural', 'stainless steel', 'glass'] },
  { key: 'size', label: '规格尺寸型', words: ['large', 'small', '32 oz', 'large capacity', 'mini', 'compact'] },
];

function inferSegment(keyword: string, rootKeyword: string): string {
  const modifier = keyword.toLowerCase().replace(rootKeyword.toLowerCase(), '').trim();
  const first = modifier.split(' ')[0];
  for (const rule of SEGMENT_RULES) {
    if (rule.words.some((w) => modifier.includes(w) || first === w)) return rule.label;
  }
  return '其他细分型';
}

// 跨行业/相关品类映射：以核心类目为中心，向外穿透关联行业
const RELATED_CATEGORIES: Record<string, { category: string; relation: number; keywords: string[] }[]> = {
  pet_supplies: [
    { category: '宠物零食', relation: 0.92, keywords: ['dog treats', 'natural dog treats', 'training treats', 'dental chews'] },
    { category: '宠物窝垫', relation: 0.78, keywords: ['dog bed', 'calming bed', 'orthopedic dog bed', 'washable dog bed'] },
    { category: '宠物牵引', relation: 0.65, keywords: ['dog leash', 'retractable leash', 'hands free leash', 'leather dog leash'] },
    { category: '猫玩具', relation: 0.58, keywords: ['cat toy', 'interactive cat toy', 'catnip toy', 'automatic cat toy'] },
  ],
  electronics: [
    { category: '手机配件', relation: 0.88, keywords: ['phone case', 'screen protector', 'magnetic charger', 'phone stand'] },
    { category: '充电储能', relation: 0.82, keywords: ['portable charger', 'fast charger', 'wireless charger', 'power bank'] },
    { category: '音频设备', relation: 0.75, keywords: ['bluetooth speaker', 'wireless earbuds', 'noise cancelling headphones', 'open ear headphones'] },
    { category: '车载电子', relation: 0.60, keywords: ['carplay adapter', 'wireless carplay', 'car phone mount', 'dash cam'] },
  ],
  sports: [
    { category: '健身器材', relation: 0.85, keywords: ['resistance bands', 'yoga mat', 'dumbbells', 'foam roller'] },
    { category: '户外装备', relation: 0.72, keywords: ['camping tent', 'sleeping bag', 'hiking backpack', 'camping chair'] },
    { category: '运动水壶', relation: 0.68, keywords: ['sports water bottle', 'insulated bottle', 'shaker bottle', 'collapsible bottle'] },
    { category: '运动鞋服', relation: 0.55, keywords: ['running shoes', 'compression socks', 'gym shorts', 'yoga pants'] },
  ],
  home_kitchen: [
    { category: '厨房收纳', relation: 0.86, keywords: ['kitchen organizer', 'spice rack', 'drawer organizer', 'pan organizer'] },
    { category: '冰箱收纳', relation: 0.74, keywords: ['storage box', 'fridge organizer', 'food container', 'egg holder'] },
    { category: '清洁工具', relation: 0.62, keywords: ['robot vacuum', 'vacuum cleaner', 'mop', 'cleaning gloves'] },
    { category: '家居装饰', relation: 0.50, keywords: ['plant pot', 'wall shelf', 'decorative tray', 'candle holder'] },
  ],
  beauty: [
    { category: '护肤精华', relation: 0.88, keywords: ['face serum', 'vitamin c serum', 'hyaluronic acid', 'retinol serum'] },
    { category: '美妆工具', relation: 0.76, keywords: ['makeup brush', 'makeup sponge', 'brush set', 'eyelash curler'] },
    { category: '美发电器', relation: 0.68, keywords: ['hair dryer', 'hair straightener', 'curling iron', 'hair clipper'] },
    { category: '身体护理', relation: 0.55, keywords: ['body lotion', 'body scrub', 'shower gel', 'hand cream'] },
  ],
  baby: [
    { category: '喂养用品', relation: 0.86, keywords: ['baby bottles', 'sippy cup', 'breast pump', 'bottle warmer'] },
    { category: '出行推车', relation: 0.72, keywords: ['baby stroller', 'car seat', 'baby carrier', 'diaper bag'] },
    { category: '婴童玩具', relation: 0.65, keywords: ['baby toy', 'teething toy', 'activity gym', 'soft book'] },
    { category: '婴童寝居', relation: 0.58, keywords: ['crib sheets', 'baby blanket', 'swaddle', 'nursery organizer'] },
  ],
  general: [
    { category: '关联品类 A', relation: 0.70, keywords: ['premium version', 'professional kit', 'travel set', 'bundle pack'] },
    { category: '关联品类 B', relation: 0.55, keywords: ['replacement parts', 'accessories kit', 'cleaning kit', 'carrying case'] },
  ],
};

type KeywordRelationships = NonNullable<AnalysisReport['market_analysis']['keyword_relationships']>;

function buildKeywordRelationships(
  keyword: string,
  opportunities: AnalysisReport['market_analysis']['keyword_opportunities'],
  summary: AnalysisReport['market_analysis']['keyword_summary'],
  archetype: ProductArchetype
): KeywordRelationships {
  if (!opportunities || opportunities.length === 0) {
    return { nodes: [], links: [], expansion_suggestions: [] };
  }
  const rootVolume = summary?.search_volume || 50000;
  const nodes: KeywordRelationships['nodes'] = [
    { id: 'root', name: keyword, value: rootVolume, type: 'root' },
  ];
  const links: KeywordRelationships['links'] = [];

  // 1) 本类目细分关键词节点（按 segment 聚类）
  for (const opp of opportunities) {
    const segment = inferSegment(opp.keyword, keyword);
    nodes.push({
      id: opp.keyword,
      name: opp.keyword,
      value: opp.search_volume,
      type: 'niche',
      trend: opp.trend,
      competition: opp.competition,
      opportunity_score: opp.opportunity_score,
      segment,
    });
    links.push({ source: 'root', target: opp.keyword, value: opp.opportunity_score });
  }

  const segmentGroups: Record<string, NonNullable<AnalysisReport['market_analysis']['keyword_opportunities']>> = {};
  for (const opp of opportunities) {
    const seg = inferSegment(opp.keyword, keyword);
    if (!segmentGroups[seg]) segmentGroups[seg] = [];
    segmentGroups[seg].push(opp);
  }

  // 2) 跨行业相关品类节点（拓品穿透）
  const relatedCategories = RELATED_CATEGORIES[archetype.category] || RELATED_CATEGORIES.general;
  const rng = seededRng(keyword, archetype.category, 'related-categories');
  for (const rc of relatedCategories) {
    const categoryId = `category::${rc.category}`;
    const categoryVolume = Math.round(rootVolume * rc.relation * rng.uniform(0.55, 0.95));
    nodes.push({
      id: categoryId,
      name: rc.category,
      value: categoryVolume,
      type: 'category',
      segment: '相关行业',
      opportunity_score: Math.round(rc.relation * 100),
    });
    // 关系越近，连线越粗
    links.push({ source: 'root', target: categoryId, value: Math.round(rc.relation * 100) });

    // 为每个相关行业挂载 2-3 个代表性关键词
    const sampleKeywords = rng.sample(rc.keywords, rng.randint(2, 3));
    for (const kw of sampleKeywords) {
      const nicheId = `niche::${kw}`;
      const nicheVolume = Math.round(categoryVolume * rng.uniform(0.25, 0.55));
      nodes.push({
        id: nicheId,
        name: kw,
        value: nicheVolume,
        type: 'niche',
        segment: '相关行业',
        trend: rng.choice(['rising', 'stable', 'falling']),
        competition: rng.choice(['low', 'medium', 'high']),
        opportunity_score: Math.round(rc.relation * rng.uniform(40, 90)),
      });
      links.push({ source: categoryId, target: nicheId, value: Math.round(rc.relation * 60) });
    }
  }

  const expansion_suggestions = Object.entries(segmentGroups)
    .map(([segment, list]) => {
      const avg = Math.round(list.reduce((s, o) => s + o.opportunity_score, 0) / list.length);
      const rising = list.filter((o) => o.trend === 'rising').length;
      const lowComp = list.filter((o) => o.competition === 'low').length;
      return {
        segment,
        keywords: list.sort((a, b) => b.opportunity_score - a.opportunity_score).slice(0, 5).map((o) => o.keyword),
        avg_score: avg,
        rationale: `该细分方向包含 ${list.length} 个关键词，平均机会分 ${avg}；其中 ${rising} 个呈上升趋势、${lowComp} 个竞争较低，${avg >= 60 ? '具备较好的拓品与广告测试价值' : '可作为长尾补充观察'}。`,
      };
    })
    .sort((a, b) => b.avg_score - a.avg_score)
    .slice(0, 4);

  return { nodes, links, expansion_suggestions };
}

// ------------------------------------------------------------------
// 主函数：生成报告
// ------------------------------------------------------------------

interface ScoringWeights {
  profit: number
  trend: number
  competition: number
  review: number
  supply: number
}

function getScoringWeights(): ScoringWeights {
  try {
    const raw = localStorage.getItem('app_settings')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed.weights) {
        return {
          profit: Number(parsed.weights.profit) || 30,
          trend: Number(parsed.weights.trend) || 25,
          competition: Number(parsed.weights.competition) || 20,
          review: Number(parsed.weights.review) || 15,
          supply: Number(parsed.weights.supply) || 10,
        }
      }
    }
  } catch {
    // ignore
  }
  return { profit: 30, trend: 25, competition: 20, review: 15, supply: 10 }
}

export function generateMockReport(
  keyword: string,
  market: string,
  budget: string,
  sellingPrice?: number,
  unitCost?: number
): AnalysisReport {
  const rng = seededRng(keyword, market, budget);
  const archetype = resolveArchetype(keyword);
  const profile = getMarketProfile(market);

  if (sellingPrice === undefined) {
    sellingPrice = Math.round((archetype.avg_price * profile.price_mult + rng.uniform(-2, 3)) * 100) / 100;
  }
  if (unitCost === undefined) {
    unitCost = Math.round(sellingPrice * rng.uniform(0.18, 0.30) * 100) / 100;
  }

  const competitors = generateCompetitors(rng, archetype, keyword, market);
  const avgPrice = Math.round((competitors.reduce((sum, p) => sum + p.price, 0) / competitors.length) * 100) / 100;
  const avgRating = Math.round((competitors.reduce((sum, p) => sum + p.rating, 0) / competitors.length) * 10) / 10;
  const avgReviews = Math.round(competitors.reduce((sum, p) => sum + p.review_count, 0) / competitors.length);

  const profit = calculateProfit(sellingPrice, unitCost, archetype.category, market);
  const trend = generateTrendSeries(rng, archetype);
  const detectedPeaks = detectPeakMonths(trend.values);
  const entryWindows = detectEntryWindows(trend.values, detectedPeaks);
  const seasonNarrative = buildSeasonNarrative(detectedPeaks, entryWindows, archetype.trend);
  const suppliers = generateSuppliers(rng, keyword, archetype, market);
  const trending = generateTrendingProducts(rng, keyword);
  const keywordOpportunities = buildKeywordOpportunities(rng, keyword, archetype.category, competitors);

  // 综合评分（五维加权：利润/趋势/竞争/评论/供应链）
  const grossMargin = profit.gross_margin;
  const marginScore = Math.min(40, Math.max(-20, grossMargin * 120));
  const trendScore = archetype.trend === 'rising' ? 25 : archetype.trend === 'stable' ? 18 : 8;
  const keywordSummary = {
    search_volume: rng.randint(8500, 95000),
    trend: archetype.trend,
    competition: (avgReviews > 8000 ? 'high' : avgReviews > 2000 ? 'medium' : 'low') as 'low' | 'medium' | 'high',
    cpc: Math.round(rng.uniform(0.65, 3.8) * 100) / 100,
    opportunity_score: Math.round(Math.min(100, (marginScore / 40) * 60 + (archetype.trend === 'rising' ? 25 : 15))),
    top_niche_keywords: (keywordOpportunities || []).slice(0, 5).map((o) => o.keyword),
  };
  const globalTrends = buildGlobalTrends(keyword, archetype);
  const keywordRelationships = buildKeywordRelationships(keyword, keywordOpportunities, keywordSummary, archetype);
  const competitionScore = avgReviews < 1500 ? 20 : avgReviews < 8000 ? 12 : 5;
  const insightScore = archetype.pain_points.length > 0 ? 15 : 8;
  // 供应链稳定性：基于供应商平均评分、响应率与交期综合评估
  const avgSupplierRating = suppliers.reduce((sum, s) => sum + s.rating, 0) / suppliers.length;
  const avgResponseRate = suppliers.reduce((sum, s) => sum + s.response_rate, 0) / suppliers.length;
  const supplyScore = Math.round(
    Math.min(15, Math.max(5, (avgSupplierRating * 2.2) + (avgResponseRate / 20) - 2)) * 10
  ) / 10;

  // 读取后台权重配置并做加权归一化（总分 100）
  const weights = getScoringWeights();
  const totalScore = Math.round(
    ((marginScore / 40) * weights.profit +
      (trendScore / 25) * weights.trend +
      (competitionScore / 20) * weights.competition +
      (insightScore / 15) * weights.review +
      (supplyScore / 15) * weights.supply) *
      10
  ) / 10;

  // 综合判定：基于五维加权总分
  let verdict: string;
  let verdictColor: string;
  let grade: string;
  if (totalScore >= 75) {
    verdict = '推荐进入';
    verdictColor = '#16a34a';
    grade = 'A';
  } else if (totalScore >= 60) {
    verdict = '谨慎进入';
    verdictColor = '#d97706';
    grade = 'B';
  } else if (totalScore >= 40) {
    verdict = '观察';
    verdictColor = '#0891b2';
    grade = 'C';
  } else {
    verdict = '不建议';
    verdictColor = '#dc2626';
    grade = 'D';
  }

  // 差异化机会：根据痛点生成具体可执行的差异化方向，便于标签提取
  function buildOpportunity(pain: string): string {
    const keywords = [
      { kw: ['漏', '渗', '密封'], action: '优化密封结构与防漏设计' },
      { kw: ['味', '异', '臭'], action: '改用食品级无异味材质' },
      { kw: ['容量', '标'], action: '推出大容量/多规格组合' },
      { kw: ['清洗', '清洁'], action: '采用可拆卸宽口设计便于清洗' },
      { kw: ['耐', '咬', '磨', '断', '裂'], action: '提升材质耐用性与抗磨损能力' },
      { kw: ['小', '尺寸', '偏大', '偏小'], action: '优化尺寸规格覆盖更多人群' },
      { kw: ['连接', '稳定', '信号', '兼容'], action: '升级芯片与连接稳定性' },
      { kw: ['续航', '电池', '充电'], action: '提升电池续航与快充体验' },
      { kw: ['安装', '设置', '复杂'], action: '简化安装步骤与使用说明' },
      { kw: ['重', '沉', '便携'], action: '轻量化便携设计' },
      { kw: ['散热', '发热'], action: '优化散热结构与温控' },
      { kw: ['掉毛', '扎', '刺激'], action: '选用更柔软亲肤材质' },
      { kw: ['色差', '掉色', '发黄'], action: '改进染色工艺与抗黄变处理' },
      { kw: ['物流', '时效'], action: '优化物流履约与时效保障' },
      { kw: ['售后', '响应'], action: '建立快速响应售后服务机制' },
      { kw: ['价格', '贵'], action: '优化成本结构实现价格优势' },
    ];
    const matched = keywords.find((k) => k.kw.some((w) => pain.includes(w)));
    const action = matched ? matched.action : '做产品升级与功能优化';
    return `针对「${pain}」${action}，形成核心差异化卖点`;
  }

  const praisedFeature = archetype.praised[0] || '核心卖点';
  const opportunities = [
    ...archetype.pain_points.slice(0, 3).map((pain) => buildOpportunity(pain)),
    `强化「${praisedFeature}」核心卖点，在 Listing 与广告中重点展示`,
  ];

  const reportCore: any = {
    keyword,
    market,
    budget,
    version: 3,
    selling_price: sellingPrice,
    unit_cost: unitCost,
    verdict,
    verdict_color: verdictColor,
    grade,
    overall_score: totalScore,
    max_score: 100,
    score_breakdown: {
      '利润空间': Math.round(marginScore * 10) / 10,
      '趋势热度': trendScore,
      '竞争强度': competitionScore,
      '评论洞察': insightScore,
      '供应链稳定性': supplyScore,
    },
    market_analysis: {
      avg_price: avgPrice,
      avg_rating: avgRating,
      avg_reviews: avgReviews,
      competitors,
      keyword_summary: keywordSummary,
      keyword_opportunities: keywordOpportunities,
      global_trends: globalTrends,
      keyword_relationships: keywordRelationships,
      data_quality: '智能分析引擎',
      market_profile: profile,
    },
    trend_analysis: {
      trend_direction: archetype.trend,
      series: trend,
      peak_months: detectedPeaks,
      entry_windows: entryWindows,
      season_narrative: seasonNarrative,
      data_quality: '智能分析引擎',
    },
    review_insights: {
      pain_points: archetype.pain_points,
      praised_features: archetype.praised,
      opportunities,
      data_quality: '智能分析引擎',
    },
    profit_analysis: profit,
    suppliers,
    compliance: buildCompliance(rng, archetype, market),
    trending_products: trending,
  };
  reportCore.next_steps = buildNextSteps(reportCore);

  return reportCore as AnalysisReport;
}
