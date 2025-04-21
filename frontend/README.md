# AI文档生成平台 - Vue前端

这是AI文档生成平台的Vue.js前端实现，提供美观且交互性强的用户界面，与后端API进行通信。

## 技术栈

- Vue 3
- Vue Router
- Pinia (状态管理)
- Element Plus (UI组件库)
- Axios (HTTP客户端)
- Vite (构建工具)

## 开发

### 依赖安装

```bash
cd frontend
npm install
```

### 开发服务器

```bash
npm run dev
```

这将启动一个开发服务器，通常运行在 http://localhost:5173。

### 构建生产版本

```bash
npm run build
```

构建后的文件会生成在 `dist` 目录，可以由后端FastAPI服务直接提供服务。

## 项目结构

- `src/views/`: 页面组件
- `src/components/`: 可复用组件
- `src/store/`: Pinia状态管理
- `src/router/`: Vue Router路由配置
- `src/assets/`: 静态资源
- `public/`: 不需要经过处理的静态资源

## 与后端集成

前端已配置为与后端API通信：

- 开发时通过Vite代理将请求转发到后端
- 生产环境构建后可以直接由FastAPI提供服务

## 功能

- 响应式UI，适配不同设备尺寸
- 步骤化的文档生成流程
- 直观的大纲编辑界面
- 即时反馈和错误处理
- 文档生成和下载

## 部署

1. 在前端目录运行构建:
```bash
npm run build
```

2. 启动后端服务:
```bash
cd ..
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

后端服务会自动检测和提供前端构建的文件。