// LangGraph工作流API客户端示例
// 用于演示如何调用基于LangGraph的文档生成API

// API端点基础URL
const API_BASE_URL = '/api';

/**
 * 运行完整的LangGraph文档生成工作流
 * @param {string} topic 文档主题
 * @param {number} pageLimit 页数限制
 * @param {string} documentType 文档类型 ('ppt' 或 'word')
 * @returns {Promise<Object>} 包含标题、大纲和内容的工作流结果
 */
async function runDocumentWorkflow(topic, pageLimit, documentType) {
  try {
    const response = await fetch(`${API_BASE_URL}/document-workflow`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        topic,
        page_limit: pageLimit,
        document_type: documentType,
      }),
    });

    if (!response.ok) {
      throw new Error(`API错误: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('运行文档工作流失败:', error);
    throw error;
  }
}

/**
 * 编辑工作流生成的标题
 * @param {string} requestId 请求ID
 * @param {string} newTitle 新标题
 * @returns {Promise<Object>} 更新后的工作流状态
 */
async function editWorkflowTitle(requestId, newTitle) {
  try {
    const response = await fetch(`${API_BASE_URL}/edit-workflow-title/${requestId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title: newTitle,
      }),
    });

    if (!response.ok) {
      throw new Error(`API错误: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('编辑标题失败:', error);
    throw error;
  }
}

/**
 * 编辑工作流生成的大纲
 * @param {string} requestId 请求ID
 * @param {Array<Object>} outline 新大纲
 * @returns {Promise<Object>} 更新后的工作流状态
 */
async function editWorkflowOutline(requestId, outline) {
  try {
    const response = await fetch(`${API_BASE_URL}/edit-workflow-outline/${requestId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        outline,
      }),
    });

    if (!response.ok) {
      throw new Error(`API错误: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('编辑大纲失败:', error);
    throw error;
  }
}

/**
 * 在编辑标题或大纲后重新生成内容
 * @param {string} requestId 请求ID
 * @returns {Promise<Object>} 更新后的工作流状态，包含新生成的内容
 */
async function regenerateContent(requestId) {
  try {
    const response = await fetch(`${API_BASE_URL}/regenerate-content/${requestId}`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`API错误: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('重新生成内容失败:', error);
    throw error;
  }
}

/**
 * 生成最终文档
 * @param {string} requestId 请求ID
 * @returns {Promise<Object>} 生成文档的结果，包含文件路径
 */
async function generateDocument(requestId) {
  try {
    const response = await fetch(`${API_BASE_URL}/generate-document/${requestId}`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`API错误: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('生成文档失败:', error);
    throw error;
  }
}

/**
 * 完整的文档生成流程示例
 */
async function documentGenerationExample() {
  try {
    // 1. 运行完整工作流
    console.log('开始运行LangGraph文档工作流...');
    const workflowResult = await runDocumentWorkflow('量化投资策略', 15, 'ppt');
    console.log('工作流完成，获得请求ID:', workflowResult.request_id);
    
    // 2. 编辑标题
    console.log('编辑标题...');
    const titleEditResult = await editWorkflowTitle(
      workflowResult.request_id, 
      '量化投资：数据驱动的财富增长策略'
    );
    console.log('标题已更新');
    
    // 3. 编辑大纲
    console.log('编辑大纲...');
    const outlineEditResult = await editWorkflowOutline(
      workflowResult.request_id,
      [
        {
          title: '量化投资概述',
          content: ['定义与起源', '与传统投资的区别', '市场应用现状']
        },
        {
          title: '核心策略分析',
          content: ['动量策略', '均值回归', '因子投资', '高频交易']
        },
        {
          title: '技术基础设施',
          content: ['数据获取与处理', '回测系统', '执行系统', '风险控制']
        },
        {
          title: '实际案例研究',
          content: ['成功案例分析', '失败教训', '绩效评估']
        },
        {
          title: '未来发展趋势',
          content: ['AI与机器学习应用', '新兴市场机会', '监管变化影响']
        }
      ]
    );
    console.log('大纲已更新');
    
    // 4. 重新生成内容
    console.log('重新生成内容...');
    const contentResult = await regenerateContent(workflowResult.request_id);
    console.log('内容已重新生成');
    
    // 5. 生成最终文档
    console.log('生成最终文档...');
    const documentResult = await generateDocument(workflowResult.request_id);
    console.log('文档已生成，下载路径:', documentResult.file_path);
    
    return {
      message: '文档生成流程完成',
      documentPath: documentResult.file_path,
      requestId: workflowResult.request_id
    };
    
  } catch (error) {
    console.error('文档生成流程出错:', error);
    throw error;
  }
}

// 导出API函数
export {
  runDocumentWorkflow,
  editWorkflowTitle,
  editWorkflowOutline,
  regenerateContent,
  generateDocument,
  documentGenerationExample
}; 