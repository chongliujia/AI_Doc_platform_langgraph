// 全局变量
let currentRequestId = null;
let outlineData = null;
let documentTitle = null;

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 表单提交事件
    document.getElementById('topic-form').addEventListener('submit', function(e) {
        e.preventDefault();
        generateOutline();
    });

    // 返回按钮事件
    document.getElementById('back-to-step1-btn').addEventListener('click', function() {
        showStep(1);
    });

    // 添加章节按钮事件
    document.getElementById('add-section-btn').addEventListener('click', function() {
        addNewSection();
    });

    // 确认大纲按钮事件
    document.getElementById('confirm-outline-btn').addEventListener('click', function() {
        saveOutline();
    });

    // 重新开始按钮事件
    document.getElementById('start-over-btn').addEventListener('click', function() {
        resetForm();
        showStep(1);
    });

    // 返回修改按钮事件
    document.getElementById('try-again-btn').addEventListener('click', function() {
        showStep(2);
    });
});

// 生成大纲
async function generateOutline() {
    const topic = document.getElementById('topic').value.trim();
    const pageLimit = parseInt(document.getElementById('page-limit').value);
    const documentType = document.querySelector('input[name="document-type"]:checked').value;

    if (!topic) {
        alert('请输入文档主题');
        return;
    }

    // 显示加载状态
    document.getElementById('generate-outline-btn').disabled = true;
    document.getElementById('generate-outline-btn').innerHTML = '正在生成大纲...';

    try {
        const response = await fetch('/api/generate-outline', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                topic: topic,
                page_limit: pageLimit,
                document_type: documentType
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '生成大纲失败');
        }

        const data = await response.json();
        
        // 保存数据
        currentRequestId = data.request_id;
        outlineData = data.outline;
        documentTitle = data.title;

        // 渲染大纲
        renderOutline(data.title, data.outline);
        
        // 显示步骤2
        showStep(2);
    } catch (error) {
        alert('错误: ' + error.message);
    } finally {
        // 恢复按钮状态
        document.getElementById('generate-outline-btn').disabled = false;
        document.getElementById('generate-outline-btn').innerHTML = '生成大纲';
    }
}

// 渲染大纲
function renderOutline(title, outline) {
    // 设置标题
    document.getElementById('document-title').textContent = title;
    
    // 清空现有内容
    const outlineContainer = document.getElementById('outline-container');
    outlineContainer.innerHTML = '';

    // 渲染每个章节
    outline.forEach((section, sectionIndex) => {
        const sectionElement = createSectionElement(section, sectionIndex);
        outlineContainer.appendChild(sectionElement);
    });
}

// 创建章节元素
function createSectionElement(section, sectionIndex) {
    const sectionDiv = document.createElement('div');
    sectionDiv.className = 'outline-section';
    sectionDiv.dataset.index = sectionIndex + 1; // 使用1开始的索引，对用户更友好
    
    // 章节标题
    const headerDiv = document.createElement('div');
    headerDiv.className = 'outline-section-header';
    
    const titleInput = document.createElement('input');
    titleInput.type = 'text';
    titleInput.className = 'form-control outline-section-title';
    titleInput.value = section.title;
    titleInput.placeholder = '请输入有意义的章节标题';
    
    // 添加标题提示和自动调整功能
    titleInput.maxLength = 50; // 限制最大长度
    titleInput.title = "章节标题应简明扼要，能够清晰表达本章内容";
    
    // 添加输入事件监听器，自动调整字体大小
    titleInput.addEventListener('input', function() {
        if (this.value.length > 30) {
            this.style.fontSize = '0.95rem';
        } else {
            this.style.fontSize = '1.1rem';
        }
        
        // 如果标题为空，添加提示类
        if (this.value.trim() === '') {
            this.classList.add('empty-title');
        } else {
            this.classList.remove('empty-title');
        }
    });
    
    // 添加聚焦事件
    titleInput.addEventListener('focus', function() {
        // 创建临时提示元素
        if (!document.getElementById('title-tooltip')) {
            const tooltip = document.createElement('div');
            tooltip.id = 'title-tooltip';
            tooltip.className = 'title-tooltip';
            tooltip.textContent = '好的章节标题应该简洁明了，能够概括本章要点';
            document.body.appendChild(tooltip);
            
            // 定位提示元素
            const rect = this.getBoundingClientRect();
            tooltip.style.position = 'absolute';
            tooltip.style.top = (rect.bottom + window.scrollY + 5) + 'px';
            tooltip.style.left = (rect.left + window.scrollX) + 'px';
            tooltip.style.backgroundColor = '#333';
            tooltip.style.color = '#fff';
            tooltip.style.padding = '5px 10px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.fontSize = '12px';
            tooltip.style.zIndex = '1000';
            tooltip.style.opacity = '0';
            tooltip.style.transition = 'opacity 0.3s';
            
            // 显示提示
            setTimeout(() => {
                tooltip.style.opacity = '1';
            }, 100);
        }
    });
    
    // 添加失焦事件
    titleInput.addEventListener('blur', function() {
        // 移除提示元素
        const tooltip = document.getElementById('title-tooltip');
        if (tooltip) {
            tooltip.style.opacity = '0';
            setTimeout(() => {
                tooltip.remove();
            }, 300);
        }
    });
    
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'outline-actions';
    
    const addPointBtn = document.createElement('button');
    addPointBtn.type = 'button';
    addPointBtn.className = 'btn btn-outline-primary btn-sm';
    addPointBtn.textContent = '添加要点';
    addPointBtn.onclick = function() {
        addContentItem(sectionDiv.querySelector('.outline-content'));
    };
    
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'btn btn-outline-danger btn-sm';
    deleteBtn.textContent = '删除章节';
    deleteBtn.onclick = function() {
        if (confirm('确定要删除此章节吗？')) {
            // 添加渐变消失动画
            sectionDiv.style.transition = 'opacity 0.3s, transform 0.3s';
            sectionDiv.style.opacity = '0';
            sectionDiv.style.transform = 'translateX(10px)';
            
            // 等待动画完成后移除元素
            setTimeout(() => {
                sectionDiv.remove();
                // 更新所有章节的序号
                updateSectionNumbers();
            }, 300);
        }
    };
    
    actionsDiv.appendChild(addPointBtn);
    actionsDiv.appendChild(deleteBtn);
    
    headerDiv.appendChild(titleInput);
    headerDiv.appendChild(actionsDiv);
    
    // 章节内容
    const contentDiv = document.createElement('div');
    contentDiv.className = 'outline-content mt-3';
    
    section.content.forEach((point, pointIndex) => {
        const contentItem = createContentItemElement(point, pointIndex);
        contentDiv.appendChild(contentItem);
    });
    
    sectionDiv.appendChild(headerDiv);
    sectionDiv.appendChild(contentDiv);
    
    return sectionDiv;
}

// 创建内容项元素
function createContentItemElement(content = '', pointIndex) {
    const itemDiv = document.createElement('div');
    itemDiv.className = 'content-item';
    itemDiv.dataset.index = pointIndex;
    
    // 添加序号标签
    const numberLabel = document.createElement('span');
    numberLabel.className = 'point-number';
    numberLabel.textContent = (pointIndex + 1) + '.';
    numberLabel.style.marginRight = '8px';
    numberLabel.style.color = '#6c757d';
    numberLabel.style.fontWeight = '500';
    numberLabel.style.minWidth = '25px';
    numberLabel.style.display = 'inline-block';
    numberLabel.style.textAlign = 'right';
    
    const contentInput = document.createElement('input');
    contentInput.type = 'text';
    contentInput.className = 'form-control content-input';
    contentInput.value = content;
    contentInput.placeholder = '输入要点';
    
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'btn btn-outline-danger btn-sm';
    deleteBtn.innerHTML = '&times;';
    deleteBtn.title = '删除此要点';
    deleteBtn.style.marginLeft = '8px';
    deleteBtn.onclick = function() {
        // 添加渐变消失动画
        itemDiv.style.transition = 'opacity 0.3s, transform 0.3s';
        itemDiv.style.opacity = '0';
        itemDiv.style.transform = 'translateX(10px)';
        
        // 等待动画完成后移除元素
        setTimeout(() => {
            itemDiv.remove();
            // 更新其他要点的序号
            updatePointNumbers();
        }, 300);
    };
    
    itemDiv.appendChild(numberLabel);
    itemDiv.appendChild(contentInput);
    itemDiv.appendChild(deleteBtn);
    
    return itemDiv;
}

// 更新要点序号
function updatePointNumbers() {
    const sections = document.querySelectorAll('.outline-section');
    sections.forEach(section => {
        const points = section.querySelectorAll('.content-item');
        points.forEach((point, index) => {
            const numberLabel = point.querySelector('.point-number');
            if (numberLabel) {
                numberLabel.textContent = (index + 1) + '.';
            }
            point.dataset.index = index;
        });
    });
}

// 更新章节序号
function updateSectionNumbers() {
    const sections = document.querySelectorAll('.outline-section');
    sections.forEach((section, index) => {
        section.dataset.index = index + 1;
    });
}

// 添加新章节
function addNewSection() {
    const outlineContainer = document.getElementById('outline-container');
    const newSection = {
        title: '新章节',
        content: ['要点1']
    };
    
    const sectionElement = createSectionElement(
        newSection, 
        document.querySelectorAll('.outline-section').length
    );
    
    // 先隐藏新章节，准备添加动画
    sectionElement.style.opacity = '0';
    sectionElement.style.transform = 'translateY(20px)';
    sectionElement.style.transition = 'opacity 0.5s, transform 0.5s';
    
    outlineContainer.appendChild(sectionElement);
    
    // 更新所有章节的序号
    updateSectionNumbers();
    
    // 触发布局更新，然后添加动画
    setTimeout(() => {
        sectionElement.style.opacity = '1';
        sectionElement.style.transform = 'translateY(0)';
        
        // 自动聚焦到新章节的标题输入框
        const titleInput = sectionElement.querySelector('.outline-section-title');
        if (titleInput) {
            titleInput.focus();
            titleInput.select();
        }
    }, 10);
    
    // 滚动到新添加的章节
    sectionElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// 添加内容项
function addContentItem(contentDiv) {
    const contentItem = createContentItemElement(
        '', 
        contentDiv.querySelectorAll('.content-item').length
    );
    contentDiv.appendChild(contentItem);
}

// 保存大纲并生成文档
async function saveOutline() {
    // 获取修改后的大纲数据
    const sections = document.querySelectorAll('.outline-section');
    const updatedOutline = Array.from(sections).map(section => {
        const title = section.querySelector('.outline-section-title').value;
        const contentItems = section.querySelectorAll('.content-input');
        const content = Array.from(contentItems)
            .map(item => item.value)
            .filter(text => text.trim() !== '');
            
        return {
            title: title,
            content: content
        };
    });
    
    try {
        // 首先更新大纲
        const updateResponse = await fetch(`/api/edit-workflow-outline/${currentRequestId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                outline: updatedOutline
            })
        });
        
        if (!updateResponse.ok) {
            const errorData = await updateResponse.json();
            throw new Error(errorData.detail || '更新大纲失败');
        }
        
        // 显示步骤3（内容生成中）
        showStep(3);
        document.getElementById('generation-status').textContent = '正在生成内容...';
        
        // 生成内容（新增步骤）
        const contentResponse = await fetch(`/api/regenerate-content/${currentRequestId}`, {
            method: 'POST'
        });
        
        if (!contentResponse.ok) {
            const errorData = await contentResponse.json();
            throw new Error(errorData.detail || '生成内容失败');
        }
        
        document.getElementById('generation-status').textContent = '正在生成文档...';
        
        // 最后生成文档
        const generateResponse = await fetch(`/api/generate-document/${currentRequestId}`, {
            method: 'POST'
        });
        
        if (!generateResponse.ok) {
            const errorData = await generateResponse.json();
            throw new Error(errorData.detail || '生成文档失败');
        }
        
        const data = await generateResponse.json();
        
        // 显示下载链接
        document.getElementById('loading-container').style.display = 'none';
        document.getElementById('download-container').style.display = 'block';
        
        const downloadLink = document.getElementById('download-link');
        downloadLink.href = `/download/${encodeURIComponent(data.file_path)}`;
        
    } catch (error) {
        document.getElementById('loading-container').style.display = 'none';
        document.getElementById('error-container').style.display = 'block';
        document.getElementById('error-message').textContent = error.message;
    }
}

// 显示指定步骤
function showStep(stepNumber) {
    // 隐藏所有步骤内容
    document.getElementById('step1-content').style.display = 'none';
    document.getElementById('step2-content').style.display = 'none';
    document.getElementById('step3-content').style.display = 'none';
    
    // 更新步骤样式
    document.querySelectorAll('.step').forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index + 1 < stepNumber) {
            step.classList.add('completed');
        } else if (index + 1 === stepNumber) {
            step.classList.add('active');
        }
    });
    
    // 显示当前步骤
    if (stepNumber <= 3) {
        document.getElementById(`step${stepNumber}-content`).style.display = 'block';
    }
    
    // 重置步骤3的状态
    if (stepNumber === 3) {
        document.getElementById('loading-container').style.display = 'block';
        document.getElementById('download-container').style.display = 'none';
        document.getElementById('error-container').style.display = 'none';
    }
}

// 重置表单
function resetForm() {
    document.getElementById('topic-form').reset();
    document.getElementById('outline-container').innerHTML = '';
    currentRequestId = null;
    outlineData = null;
    documentTitle = null;
} 