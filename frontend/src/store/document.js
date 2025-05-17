import { defineStore } from 'pinia'
import axios from 'axios'

export const useDocumentStore = defineStore('document', {
  state: () => ({
    topic: '',
    pageLimit: 10,
    documentType: 'ppt',
    title: '',
    outline: [],
    content: {},
    requestId: null,
    loading: false,
    error: null,
    documentUrl: null,
    currentStep: 1
  }),
  
  actions: {
    setCurrentStep(step) {
      this.currentStep = step
    },
    
    resetState() {
      this.topic = ''
      this.pageLimit = 10
      this.documentType = 'ppt'
      this.title = ''
      this.outline = []
      this.content = {}
      this.requestId = null
      this.error = null
      this.documentUrl = null
      this.currentStep = 1
    },
    
    async generateOutline(formData) {
      this.loading = true
      this.error = null
      
      try {
        const response = await axios.post('/api/generate-outline', {
          topic: formData.topic,
          page_limit: formData.pageLimit,
          document_type: formData.documentType
        })
        
        this.topic = formData.topic
        this.pageLimit = formData.pageLimit
        this.documentType = formData.documentType
        this.title = response.data.title
        this.outline = response.data.outline
        this.requestId = response.data.request_id
        this.currentStep = 2
        
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || '生成大纲时出错'
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateOutline(outline) {
      this.loading = true
      this.error = null
      
      try {
        const response = await axios.put(`/api/edit-outline/${this.requestId}`, {
          outline: outline
        })
        
        this.outline = response.data.outline
        this.content = {}
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || '更新大纲时出错'
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateTitle(title) {
      this.loading = true
      this.error = null
      
      try {
        const response = await axios.put(`/api/edit-title/${this.requestId}`, {
          title: title
        })
        
        this.title = title
        this.content = {}
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || '更新标题时出错'
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async generateContent() {
      this.loading = true
      this.error = null
      
      try {
        const response = await axios.post(`/api/generate-content/${this.requestId}`)
        this.content = response.data.content
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || '生成内容时出错'
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async generateDocument() {
      this.loading = true
      this.error = null
      
      try {
        const response = await axios.post(`/api/generate-document/${this.requestId}`)
        
        if (response.data.success) {
          if (response.data.file_path) {
            this.documentUrl = `/download/${response.data.file_path}`
          } else {
            this.error = '文档生成成功但无法获取下载路径'
          }
        } else {
          this.error = response.data.message || '生成文档失败，请重试'
          this.documentUrl = null
        }
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || '生成文档时出错'
        throw error
      } finally {
        this.loading = false
      }
    }
  }
}) 