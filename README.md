# AI文档生成平台

基于LangGraph和DeepSeek API构建的智能文档生成平台，支持自动生成PPT或Word文档。

## 功能特点

- 用户输入主题和页数限制
- AI自动生成大标题和大纲
- 支持用户编辑、增加或删除大纲
- 根据确认后的大纲生成PPT或Word文档
- 离线备用生成功能，确保网络故障时也能工作

## 安装

1. 克隆仓库
```bash
git clone https://github.com/yourusername/ai_doc_platform_langgraph.git
cd ai_doc_platform_langgraph
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
```
然后编辑`.env`文件，添加你的DeepSeek API密钥和其他配置

环境变量说明:
- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `DEEPSEEK_API_URL`: API服务地址，默认为 https://api.deepseek.com
- `DEEPSEEK_MODEL`: 使用的模型名称，默认为 deepseek-chat
- `API_MAX_RETRIES`: API调用失败时的最大重试次数
- `API_RETRY_DELAY`: 重试之间的基础延迟（秒）
- `API_TIMEOUT`: API请求超时时间（秒）

4. 构建前端（提高加载速度）
```bash
cd frontend
npm install
npm run build
cd ..
```

## 运行

```bash
uvicorn app.main:app --reload
```

访问 http://localhost:8000 来使用应用

> **注意**：如果要获得更快的前端加载体验，请确保先完成前端构建步骤。未构建的前端在开发模式下加载速度会较慢。

## 离线使用说明

本系统具有离线备用生成功能，在以下情况下会激活：
- DeepSeek API密钥未配置
- 网络连接问题导致API请求失败
- API服务返回错误

离线模式下，系统将基于提示词自动生成基本内容，确保用户能够获得基础文档，后续可以手动编辑完善。 # AI_Doc_platform_langgraph
