<template>
  <div class="home-container">
    <el-card class="main-card">
      <!-- 步骤条 -->
      <el-steps :active="documentStore.currentStep" finish-status="success" class="steps-container">
        <el-step title="输入信息" />
        <el-step title="编辑大纲" />
        <el-step title="生成内容" />
        <el-step title="生成文档" />
      </el-steps>

      <!-- 步骤1: 输入信息 -->
      <div v-if="documentStore.currentStep === 1" class="step-content">
        <h2>输入文档信息</h2>
        <el-form :model="formData" label-width="120px" @submit.prevent="handleGenerateOutline">
          <el-form-item label="文档主题" required>
            <el-input v-model="formData.topic" placeholder="请输入文档主题" />
          </el-form-item>
          <el-form-item label="页数限制">
            <el-input-number v-model="formData.pageLimit" :min="1" :max="50" />
          </el-form-item>
          <el-form-item label="文档类型">
            <el-radio-group v-model="formData.documentType">
              <el-radio label="ppt">PPT演示文稿</el-radio>
              <el-radio label="word">Word文档</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleGenerateOutline" :loading="documentStore.loading">
              生成大纲
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤2: 编辑大纲 -->
      <div v-if="documentStore.currentStep === 2" class="step-content">
        <h2 class="title-editable">
          <el-input 
            v-model="editableTitle" 
            placeholder="文档标题" 
            class="title-input" 
            @blur="handleTitleEdit"
            :modelValue="editableTitle || documentStore.title"
          />
        </h2>
        <el-alert v-if="documentStore.error" type="error" :title="documentStore.error" :closable="false" />

        <div class="outline-editor">
          <div v-for="(section, sectionIndex) in editableOutline" :key="sectionIndex" class="outline-section">
            <div class="section-header">
              <el-input v-model="section.title" placeholder="章节标题" />
              <el-button type="danger" size="small" @click="removeSection(sectionIndex)" icon="Delete" circle />
            </div>
            <div class="section-content">
              <div v-for="(point, pointIndex) in section.content" :key="pointIndex" class="content-item">
                <el-input v-model="section.content[pointIndex]" placeholder="要点内容" />
                <el-button type="danger" size="small" @click="removePoint(sectionIndex, pointIndex)" icon="Delete" circle />
              </div>
              <el-button type="primary" size="small" @click="addPoint(sectionIndex)" plain>添加要点</el-button>
            </div>
          </div>

          <div class="outline-actions">
            <el-button @click="addSection" type="success">添加章节</el-button>
            <el-button type="primary" @click="handleConfirmOutline" :loading="documentStore.loading">确认大纲</el-button>
            <el-button @click="documentStore.setCurrentStep(1)">返回</el-button>
          </div>
        </div>
      </div>

      <!-- 步骤3: 生成内容 -->
      <div v-if="documentStore.currentStep === 3" class="step-content">
        <h2>{{ documentStore.title }} - 内容生成</h2>
        <el-alert v-if="documentStore.error" type="error" :title="documentStore.error" :closable="false" />
        
        <div v-if="documentStore.loading" class="loading-container">
          <div class="progress-status">
            <el-progress 
              type="circle" 
              :percentage="generationProgress" 
              :status="generationProgress >= 100 ? 'success' : 'in-progress'"
            />
            <p class="mt-3">{{ generationStatusText }}</p>
            <div class="generation-details">
              <div v-for="(section, index) in documentStore.outline" :key="index" 
                   class="section-progress" 
                   :class="{ 'completed': completedSections.includes(section.title) }">
                <span class="section-icon">
                  <el-icon v-if="completedSections.includes(section.title)"><Check /></el-icon>
                  <el-icon v-else-if="currentSection === section.title"><Loading /></el-icon>
                  <el-icon v-else><Timer /></el-icon>
                </span>
                <span class="section-title">{{ section.title }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="content-preview">
          <el-collapse>
            <el-collapse-item v-for="(section, index) in documentStore.outline" :key="index" :title="section.title">
              <div v-if="documentStore.content && documentStore.content[section.title]" class="content-section">
                <h4>内容预览:</h4>
                <div class="content-text">
                  {{ documentStore.content[section.title].substring(0, 200) }}...
                </div>
              </div>
              <div v-else class="no-content">
                <el-empty description="内容尚未生成" />
              </div>
            </el-collapse-item>
          </el-collapse>
          
          <div class="content-actions mt-4">
            <el-button type="primary" @click="handleGenerateContent" :loading="documentStore.loading">生成内容</el-button>
            <el-button type="success" @click="handleProceedToDocument" :disabled="!hasGeneratedContent">生成文档</el-button>
            <el-button @click="documentStore.setCurrentStep(2)">返回编辑大纲</el-button>
          </div>
        </div>
      </div>

      <!-- 步骤4: 生成文档 -->
      <div v-if="documentStore.currentStep === 4" class="step-content">
        <div v-if="documentStore.loading" class="loading-container">
          <el-icon class="loading-icon"><Loading /></el-icon>
          <p>正在生成文档，请稍候...</p>
        </div>
        <div v-else-if="documentStore.error" class="error-container">
          <el-alert type="error" :title="documentStore.error" :closable="false" />
          <el-button class="mt-3" @click="documentStore.setCurrentStep(3)">返回修改</el-button>
        </div>
        <div v-else-if="documentStore.documentUrl" class="success-container">
          <el-result icon="success" title="文档生成成功!" sub-title="您可以点击下方按钮下载文档">
            <template #extra>
              <el-button type="primary" @click="downloadDocument">下载文档</el-button>
              <el-button @click="resetAll">创建新文档</el-button>
            </template>
          </el-result>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, onUnmounted } from 'vue'
import { useDocumentStore } from '../store/document'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Check, Timer } from '@element-plus/icons-vue'

const documentStore = useDocumentStore()

// 表单数据
const formData = ref({
  topic: '',
  pageLimit: 10,
  documentType: 'ppt'
})

// 可编辑的大纲数据
const editableOutline = ref([])

// 可编辑的标题
const editableTitle = ref('')

// 内容生成进度状态
const generationProgress = ref(0)
const currentSection = ref('')
const completedSections = ref([])
const generationStatusText = ref('正在准备生成详细内容...')

// 生成进度轮询逻辑
const progressPolling = ref(null)

// 定义生成阶段
const GENERATION_STAGES = {
  PREPARING: { text: '正在准备生成详细内容...', progress: 5 },
  ANALYZING: { text: '正在分析大纲内容...', progress: 15 },
  RESEARCHING: { text: '正在收集相关信息...', progress: 30 },
  GENERATING: { text: '正在生成章节内容...', progress: 50 },
  REVIEWING: { text: '正在优化内容质量...', progress: 80 },
  FINALIZING: { text: '正在完成最终内容...', progress: 95 },
  COMPLETED: { text: '内容生成完成！', progress: 100 }
}

// 在组件挂载时初始化可编辑大纲和标题
onMounted(() => {
  // 立即初始化标题
  if (documentStore.title) {
    editableTitle.value = documentStore.title
  }
  
  if (documentStore.outline.length > 0) {
    editableOutline.value = JSON.parse(JSON.stringify(documentStore.outline))
  }
})

// 使用计算属性监听变化并确保标题总是展示
watch(() => documentStore.title, (newTitle) => {
  if (newTitle && (!editableTitle.value || editableTitle.value === '')) {
    editableTitle.value = newTitle
  }
}, { immediate: true })

// 监听大纲变化
watch(() => documentStore.outline, (newOutline) => {
  if (newOutline.length > 0 && editableOutline.value.length === 0) {
    editableOutline.value = JSON.parse(JSON.stringify(newOutline))
  }
}, { immediate: true })

// 生成大纲
const handleGenerateOutline = async () => {
  if (!formData.value.topic) {
    ElMessage.warning('请输入文档主题')
    return
  }

  try {
    await documentStore.generateOutline(formData.value)
    editableOutline.value = JSON.parse(JSON.stringify(documentStore.outline))
    
    // 确保标题立即更新到可编辑变量中
    if (documentStore.title) {
      editableTitle.value = documentStore.title
    }
  } catch (error) {
    ElMessage.error(error.message || '生成大纲失败')
  }
}

// 添加章节
const addSection = () => {
  editableOutline.value.push({
    title: '新章节',
    content: ['新要点']
  })
}

// 删除章节
const removeSection = (index) => {
  editableOutline.value.splice(index, 1)
}

// 添加要点
const addPoint = (sectionIndex) => {
  editableOutline.value[sectionIndex].content.push('')
}

// 删除要点
const removePoint = (sectionIndex, pointIndex) => {
  editableOutline.value[sectionIndex].content.splice(pointIndex, 1)
}

// 确认大纲并生成文档
const handleConfirmOutline = async () => {
  // 过滤无效内容
  const validOutline = editableOutline.value.map(section => {
    return {
      title: section.title.trim() || '未命名章节',
      content: section.content.filter(point => point.trim() !== '')
    }
  }).filter(section => section.content.length > 0)

  if (validOutline.length === 0) {
    ElMessage.warning('大纲至少需要一个有效章节')
    return
  }

  try {
    await documentStore.updateOutline(validOutline)
    documentStore.setCurrentStep(3)
    
    // 自动开始生成内容
    setTimeout(async () => {
      await handleGenerateContent()
    }, 500)
  } catch (error) {
    ElMessage.error(error.message || '处理失败')
  }
}

// 生成内容
const handleGenerateContent = async () => {
  try {
    // 重置进度状态
    generationProgress.value = 0
    generationStatusText.value = '正在准备生成详细内容...'
    currentSection.value = ''
    completedSections.value = []
    
    // 开始生成内容并获取请求ID
    const contentPromise = documentStore.generateContent()
    
    // 开始轮询真实进度
    startProgressPolling(documentStore.requestId)
    
    // 等待真实内容生成完成
    await contentPromise
    
    // 停止轮询进度
    stopProgressPolling()
    
    if (hasGeneratedContent.value) {
      ElMessage.success('内容生成成功')
    } else {
      ElMessage.warning('内容生成部分成功或为空，可能导致文档质量降低')
    }
  } catch (error) {
    // 出错时也更新UI状态
    stopProgressPolling()
    generationStatusText.value = '生成过程中出现错误'
    ElMessage.error(error.message || '生成内容失败')
  }
}

// 检查是否有生成的内容
const hasGeneratedContent = computed(() => {
  return documentStore.content && Object.keys(documentStore.content).length > 0 &&
         Object.values(documentStore.content).some(content => content && content.trim().length > 0)
})

// 进入生成文档步骤
const handleProceedToDocument = async () => {
  if (!hasGeneratedContent.value) {
    ElMessage.warning('请先生成内容，没有内容数据将无法生成文档')
    return
  }
  
  // 已有内容，直接生成文档
  documentStore.setCurrentStep(4)
  try {
    const result = await documentStore.generateDocument()
    if (result.success) {
      ElMessage.success('文档生成成功，请点击下载按钮获取文档')
    } else {
      // 服务器返回了失败但有消息，显示具体消息
      documentStore.error = result.message
      ElMessage.warning(result.message || '文档生成完成，但可能存在问题')
    }
  } catch (error) {
    // 网络或其他错误
    ElMessage.error(error.message || '生成文档失败')
  }
}

// 下载文档
const downloadDocument = () => {
  if (!documentStore.documentUrl) {
    ElMessage.error('文档下载链接不可用')
    return
  }
  
  const downloadUrl = documentStore.documentUrl.startsWith('/download/') ? 
    documentStore.documentUrl : 
    `/download/${documentStore.documentUrl}`
  
  ElMessage.success('开始下载文档')
  window.open(downloadUrl, '_blank')
}

// 重置所有
const resetAll = () => {
  formData.value = {
    topic: '',
    pageLimit: 10,
    documentType: 'ppt'
  }
  editableOutline.value = []
  documentStore.resetState()
}

// 处理标题编辑
const handleTitleEdit = async () => {
  if (editableTitle.value.trim() === '') {
    editableTitle.value = documentStore.title
    return
  }
  
  if (editableTitle.value.trim() !== documentStore.title) {
    try {
      await documentStore.updateTitle(editableTitle.value.trim())
      ElMessage.success('标题已更新')
    } catch (error) {
      ElMessage.error(error.message || '更新标题失败')
      editableTitle.value = documentStore.title
    }
  }
}

// 开始轮询进度
const startProgressPolling = (requestId) => {
  // 停止任何现有的轮询
  stopProgressPolling()
  
  // 验证请求ID
  if (!requestId) {
    console.error('无法开始轮询：缺少有效的请求ID')
    return
  }
  
  console.log(`开始轮询进度，请求ID: ${requestId}`)
  
  // 重置进度状态
  generationProgress.value = 0
  currentSection.value = ''
  completedSections.value = []
  generationStatusText.value = '正在准备生成详细内容...'
  
  // 创建新的轮询间隔
  progressPolling.value = setInterval(async () => {
    try {
      const response = await fetch(`/api/generation-progress/${requestId}`)
      if (response.ok) {
        const progressData = await response.json()
        
        // 更新进度状态
        generationProgress.value = progressData.progress
        generationStatusText.value = progressData.message
        
        if (progressData.current_section) {
          currentSection.value = progressData.current_section
        } else {
          currentSection.value = ''
        }
        
        completedSections.value = progressData.completed_sections || []
        
        // 如果生成完成或出错，停止轮询
        if (progressData.current_stage === 'completed' || progressData.current_stage === 'error') {
          stopProgressPolling()
        }
      }
    } catch (error) {
      console.error('获取生成进度失败:', error)
    }
  }, 500) // 每500毫秒轮询一次
}

// 停止轮询进度
const stopProgressPolling = () => {
  if (progressPolling.value) {
    clearInterval(progressPolling.value)
    progressPolling.value = null
  }
}

// 在组件卸载时停止轮询
onUnmounted(() => {
  stopProgressPolling()
})
</script>

<style scoped>
.home-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 0;
}

.main-card {
  margin-bottom: 30px;
}

.steps-container {
  margin-bottom: 30px;
}

.step-content {
  margin-top: 20px;
}

.outline-editor {
  margin-top: 20px;
}

.outline-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background-color: #ffffff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.outline-section:hover {
  box-shadow: 0 4px 12px rgba(13, 110, 253, 0.1);
  transform: translateY(-2px);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e9ecef;
}

.section-content {
  padding-left: 15px;
}

.content-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  padding: 3px 0;
}

.outline-actions {
  margin-top: 30px;
  display: flex;
  gap: 10px;
}

.loading-container, .error-container, .success-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px 0;
}

.progress-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 600px;
}

.generation-details {
  margin-top: 30px;
  width: 100%;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background-color: #f8f9fa;
  padding: 15px;
  max-height: 300px;
  overflow-y: auto;
}

.section-progress {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 8px;
  border-radius: 4px;
  background-color: #ffffff;
  transition: all 0.3s ease;
}

.section-progress.completed {
  background-color: #f0f9eb;
  border-left: 3px solid #67c23a;
}

.section-progress:last-child {
  margin-bottom: 0;
}

.section-icon {
  margin-right: 10px;
  color: #909399;
}

.section-progress.completed .section-icon {
  color: #67c23a;
}

.section-title {
  font-size: 14px;
  color: #606266;
  flex-grow: 1;
}

.section-progress.completed .section-title {
  color: #67c23a;
  font-weight: 500;
}

.mt-3 {
  margin-top: 15px;
}

/* 内容预览样式 */
.content-preview {
  margin-top: 20px;
}

.content-section {
  padding: 10px;
}

.content-text {
  white-space: pre-line;
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.5;
  max-height: 300px;
  overflow-y: auto;
}

.no-content {
  padding: 20px;
}

.content-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.title-editable {
  margin-bottom: 20px;
}

/* 标题输入框强制样式 */
.title-input {
  font-size: 1.1rem !important;
  font-weight: bold !important;
  line-height: 1.4 !important;
}

.title-input :deep(.el-input__wrapper) {
  padding: 6px 10px !important;
  box-shadow: 0 0 0 1px #dcdfe6 inset !important;
  height: auto !important;
}

.title-input :deep(.el-input__inner) {
  height: auto !important;
  font-size: 1.1rem !important;
  line-height: 1.4 !important;
  min-height: unset !important;
  padding: 0 !important;
}

/* 章节标题输入框强制样式 */
.section-header :deep(.el-input__wrapper) {
  padding: 4px 8px !important;
  box-shadow: 0 0 0 1px #dcdfe6 inset !important;
  height: auto !important;
}

.section-header :deep(.el-input__inner) {
  font-size: 0.95rem !important;
  height: auto !important;
  line-height: 1.4 !important;
  min-height: unset !important;
  padding: 0 !important;
}

/* 内容输入框强制样式 */
.content-item :deep(.el-input__wrapper) {
  padding: 3px 8px !important;
  box-shadow: 0 0 0 1px #dcdfe6 inset !important;
  height: auto !important;
}

.content-item :deep(.el-input__inner) {
  font-size: 0.85rem !important;
  height: auto !important;
  line-height: 1.4 !important;
  min-height: unset !important;
  padding: 0 !important;
}

/* 按钮样式 */
.el-button.is-circle {
  padding: 6px !important;
  min-height: unset !important;
  height: auto !important;
}

.el-button--small {
  font-size: 0.85rem !important;
  padding: 6px 10px !important;
  min-height: unset !important;
  height: auto !important;
}
</style>