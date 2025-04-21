<template>
  <el-config-provider>
    <div class="app-container">
      <el-container>
        <el-header height="60px">
          <div class="header-content">
            <h1 class="app-title">AI文档生成平台</h1>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
        <el-footer height="40px">
          <div class="footer-content">
            <p>© 2025 AI文档生成平台 - 基于LangGraph和DeepSeek API</p>
          </div>
        </el-footer>
      </el-container>
    </div>
  </el-config-provider>
</template>

<style>
body {
  margin: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}

.el-header {
  background-color: #409eff;
  color: white;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.12);
  position: relative;
  z-index: 10;
}

.header-content {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
}

.app-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.el-main {
  padding: 20px;
}

.el-footer {
  background-color: #f5f7fa;
  color: #666;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
}

.footer-content {
  width: 100%;
  max-width: 1200px;
}
</style> 