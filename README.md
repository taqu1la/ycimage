# AI创作工坊

一个现代化的AI图像和视频生成平台，支持GPT-Image-2、VEO3等多种顶级AI模型。

## ✨ 功能特点

- 🎨 **多种创作模式**
  - 文字转图像生成
  - 图像参考编辑
  - 文字转视频
  - 图像转视频动画

- ⚡ **极速生成**
  - GPU集群加速处理
  - 实时进度追踪
  - 批量处理支持

- 🎯 **专业级效果**
  - 4K超清画质输出
  - 多种比例可选
  - 无水印下载
  - 商业授权可用

## 🚀 快速开始

### 安装依赖

```bash
# 无需安装，直接在浏览器中打开index.html即可
```

### 使用方式

1. 直接在浏览器中打开 `index.html` 文件
2. 或使用本地服务器：
```bash
# Python
python -m http.server 8080

# Node.js
npx serve .
```

## 📁 项目结构

```
├── index.html      # 主页面
├── styles.css      # 样式文件
├── script.js       # JavaScript逻辑
├── admin.html      # 后台管理页面
└── README.md       # 项目文档
```

## 🔧 配置API

在 `script.js` 中配置您的API密钥：

```javascript
const API_CONFIG = {
    baseURL: 'https://api.apimart.ai/v1',
    apiKey: 'YOUR_API_KEY'
};
```

## 💳 支付集成

平台支持微信支付和支付宝支付（需对接商户接口）

## 📝 后台管理

访问 `admin.html` 进行模板管理和系统设置

## 🎨 技术栈

- HTML5 + CSS3
- Vanilla JavaScript
- APIMart API

## 📄 License

MIT License
