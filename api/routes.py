from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import traceback
import json
import logging
import uuid

from api.graph import run_document_workflow, generate_outline, generate_title
from utils.document_generator import DocumentGenerator
from api.state import generation_progress, document_requests

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("api.routes")

router = APIRouter()

# 输入模型
class DocumentRequest(BaseModel):
    topic: str
    page_limit: int
    document_type: str  # "ppt" 或 "word"

# 大纲生成请求模型
class OutlineRequest(BaseModel):
    topic: str
    title: str
    page_limit: int
    document_type: str = "ppt"

# 大纲条目模型
class OutlineItem(BaseModel):
    title: str
    content: List[str]

# 大纲编辑模型
class OutlineEditRequest(BaseModel):
    outline: List[OutlineItem]
    title: Optional[str] = None

# 标题编辑模型
class TitleEditRequest(BaseModel):
    title: str

# 大纲响应模型
class OutlineResponse(BaseModel):
    success: bool
    outline: List[Dict[str, Any]]
    estimated_pages: int
    error: Optional[str] = None
    title: str
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# 响应模型
class WorkflowResponse(BaseModel):
    success: bool
    title: str
    outline: List[Dict[str, Any]]
    content: Optional[Dict[str, str]] = None
    request_id: str
    message: Optional[str] = None

class GenerateDocumentResponse(BaseModel):
    success: bool
    message: str
    file_path: Optional[str] = None

# 添加获取生成进度的API端点
@router.get("/generation-progress/{request_id}")
async def get_generation_progress(request_id: str):
    """获取内容生成进度"""
    logger.info(f"获取生成进度: request_id={request_id}")
    
    if request_id not in generation_progress:
        return {
            "progress": 0,
            "current_stage": "not_started",
            "message": "生成尚未开始",
            "current_section": None,
            "completed_sections": []
        }
    
    return generation_progress[request_id]

# 添加兼容旧API的大纲生成端点
@router.post("/generate-outline", response_model=OutlineResponse)
async def api_generate_outline(request: DocumentRequest):
    """生成文档大纲API"""
    try:
        logger.info(f"收到大纲生成请求: 主题={request.topic}, 页数={request.page_limit}, 类型={request.document_type}")
        
        # 首先生成标题
        title_result = await generate_title(request.topic, request.document_type, request.page_limit)
        title = title_result["title"]
        
        logger.info(f"生成的标题: {title}")
        
        # 然后调用大纲生成函数
        outline_result = await generate_outline(
            topic=request.topic,
            title=title,
            page_limit=request.page_limit,
            document_type=request.document_type
        )
        
        logger.info(f"大纲生成完成，包含{len(outline_result['outline'])}个章节")
        
        # 生成唯一请求ID
        request_id = str(uuid.uuid4())
        
        # 保存请求数据到内存存储，便于后续使用
        document_requests[request_id] = {
            "topic": request.topic,
            "title": title,
            "outline": outline_result["outline"],
            "document_type": request.document_type,
            "page_limit": request.page_limit,
            "content": None,
            "user_edited_title": False,
            "user_edited_outline": False
        }
        
        return {
            "success": outline_result["success"],
            "outline": outline_result["outline"],
            "estimated_pages": outline_result.get("estimated_pages", request.page_limit),
            "error": outline_result.get("error"),
            "title": title,
            "request_id": request_id
        }
        
    except Exception as e:
        logger.error(f"大纲生成异常: {e}")
        logger.error(traceback.format_exc())
        
        # 使用graph.py中的默认大纲
        from api.graph import generate_default_outline
        default_data = generate_default_outline(request.topic, request.page_limit)
        
        return {
            "success": False,
            "outline": default_data["outline"],
            "estimated_pages": default_data["estimated_pages"],
            "error": f"大纲生成失败: {str(e)}",
            "title": f"{request.topic}研究分析",
            "request_id": str(uuid.uuid4())
        }

@router.post("/document-workflow", response_model=WorkflowResponse)
async def document_workflow(request: DocumentRequest):
    """LangGraph工作流：一次性生成包含标题、大纲和内容的完整文档"""
    try:
        logger.info(f"收到文档工作流请求: 主题={request.topic}, 页数={request.page_limit}, 类型={request.document_type}")
        
        # 运行基于LangGraph的完整工作流
        workflow_result = await run_document_workflow(
            topic=request.topic,
            page_limit=request.page_limit,
            document_type=request.document_type
        )
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        logger.info(f"生成请求ID: {request_id}")
        
        # 保存请求数据到内存存储
        document_requests[request_id] = {
            "topic": request.topic,
            "title": workflow_result["title"],
            "outline": workflow_result["outline"],
            "document_type": request.document_type,
            "page_limit": request.page_limit,
            "content": workflow_result["content"],
            "user_edited_title": False,
            "user_edited_outline": False,
            "error_message": workflow_result.get("error_message")
        }
        
        # 构建响应信息
        message = "文档内容生成成功"
        if workflow_result.get("error_message"):
            message = f"文档生成部分成功，但有问题: {workflow_result.get('error_message')}"
        
        logger.info(f"工作流执行完成: {workflow_result['current_step']}")
        
        return {
            "success": workflow_result["current_step"] == "content_generated",
            "title": workflow_result["title"],
            "outline": workflow_result["outline"],
            "content": workflow_result["content"] or {},
            "request_id": request_id,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"工作流执行异常: {e}")
        logger.error(traceback.format_exc())
        
        # 创建基本响应
        default_title = f"{request.topic}研究分析"
        basic_outline = [
            {
                "title": "主题概述",
                "content": ["背景信息", "核心内容", "主要目标"]
            },
            {
                "title": "主要分析",
                "content": ["关键要素", "分析方法", "结果解读"]
            },
            {
                "title": "总结",
                "content": ["主要发现", "建议", "未来展望"]
            }
        ]
        
        # 空内容
        empty_content = {}
        for section in basic_outline:
            empty_content[section["title"]] = "内容生成失败，请手动填写或重试。"
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 保存基本数据
        document_requests[request_id] = {
            "topic": request.topic,
            "title": default_title,
            "outline": basic_outline,
            "document_type": request.document_type,
            "page_limit": request.page_limit,
            "content": empty_content,
            "user_edited_title": False,
            "user_edited_outline": False
        }
        
        return {
            "success": False,
            "title": default_title,
            "outline": basic_outline,
            "content": empty_content,
            "request_id": request_id,
            "message": f"工作流执行失败: {str(e)}"
        }

@router.put("/edit-workflow-title/{request_id}", response_model=WorkflowResponse)
async def edit_workflow_title(request_id: str, title_edit: TitleEditRequest):
    """编辑文档标题（工作流版本）"""
    logger.info(f"收到标题编辑请求: request_id={request_id}")
    
    if request_id not in document_requests:
        logger.warning(f"请求ID不存在: {request_id}")
        raise HTTPException(status_code=404, detail="请求ID不存在")
    
    try:
        # 获取原始请求数据
        request_data = document_requests[request_id]
        
        # 更新标题
        request_data["title"] = title_edit.title
        request_data["user_edited_title"] = True
        
        # 提示需要重新生成内容
        request_data["needs_content_update"] = True
        
        logger.info(f"标题已更新: {title_edit.title}")
        
        return {
            "success": True,
            "title": request_data["title"],
            "outline": request_data["outline"],
            "content": request_data.get("content", {}),
            "request_id": request_id,
            "message": "标题已更新"
        }
        
    except Exception as e:
        logger.error(f"编辑标题时出错: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"编辑标题失败: {str(e)}")

@router.put("/edit-workflow-outline/{request_id}", response_model=WorkflowResponse)
async def edit_workflow_outline(request_id: str, outline_edit: OutlineEditRequest):
    """编辑文档大纲（工作流版本）"""
    logger.info(f"收到大纲编辑请求: request_id={request_id}")
    
    if request_id not in document_requests:
        logger.warning(f"请求ID不存在: {request_id}")
        raise HTTPException(status_code=404, detail="请求ID不存在")
    
    try:
        # 获取原始请求数据
        request_data = document_requests[request_id]
        
        # 更新大纲
        outline_dict = [item.dict() for item in outline_edit.outline]
        request_data["outline"] = outline_dict
        request_data["user_edited_outline"] = True
        
        # 更新标题（如果提供）
        if outline_edit.title:
            request_data["title"] = outline_edit.title
            request_data["user_edited_title"] = True
            logger.info(f"标题已更新: {outline_edit.title}")
        
        # 提示需要重新生成内容
        request_data["needs_content_update"] = True
        
        logger.info(f"大纲已更新: {json.dumps(outline_dict)[:200]}...")
        
        return {
            "success": True,
            "title": request_data["title"],
            "outline": request_data["outline"],
            "content": request_data.get("content", {}),
            "request_id": request_id,
            "message": "大纲和标题已更新"
        }
        
    except Exception as e:
        logger.error(f"编辑大纲时出错: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"编辑大纲失败: {str(e)}")

# 添加别名端点，使/api/edit-outline/{request_id}也能工作
@router.put("/edit-outline/{request_id}", response_model=WorkflowResponse)
async def edit_outline_alias(request_id: str, outline_edit: OutlineEditRequest):
    """编辑文档大纲的别名端点，转发到edit_workflow_outline"""
    logger.info(f"通过别名端点收到大纲编辑请求: request_id={request_id}")
    return await edit_workflow_outline(request_id, outline_edit)

@router.post("/generate-document/{request_id}", response_model=GenerateDocumentResponse)
async def generate_document(request_id: str, background_tasks: BackgroundTasks):
    """根据LangGraph工作流生成的内容，生成最终文档"""
    try:
        logger.info(f"收到生成文档请求: request_id={request_id}")
        
        if request_id not in document_requests:
            logger.warning(f"找不到request_id: {request_id}")
            
            # 为了前端体验，返回更友好的错误而不是抛出异常
            return {
                "success": False,
                "message": f"找不到对应的请求记录，可能由于服务器重启导致数据丢失。请重新生成内容后再试。",
                "file_path": None
            }
        
        request_data = document_requests[request_id]
        title = request_data["title"]
        outline_data = request_data["outline"]
        document_type = request_data["document_type"]
        content_data = request_data.get("content")
        
        # 验证内容数据
        if not content_data or not any(content_data.values()):
            logger.warning("内容数据为空")
            return {
                "success": False,
                "message": "内容数据为空，无法生成文档。请先生成内容。",
                "file_path": None
            }
        
        # 获取静态文件目录，用于保存生成的文件
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "static", "documents")
        os.makedirs(static_dir, exist_ok=True)
        
        # 根据文档类型生成相应的文档
        file_name = f"{title.replace(' ', '_').replace('/', '_')}_{request_id[-8:]}"
        
        if document_type.lower() == "ppt":
            # 生成PPT
            logger.info(f"生成PPT文档，页数限制: {request_data.get('page_limit')}")
            logger.info(f"内容数据章节: {list(content_data.keys()) if content_data else '无'}")
            
            ppt = DocumentGenerator.generate_ppt(title, outline_data, content_data, request_data.get("page_limit"))
            file_path = os.path.join(static_dir, f"{file_name}.pptx")
            ppt.save(file_path)
            # 构建相对URL路径，而不是绝对文件系统路径
            relative_path = f"documents/{file_name}.pptx"
            logger.info(f"PPT已保存: {file_path}, 相对路径: {relative_path}")
            
        elif document_type.lower() == "word":
            # 生成Word文档
            logger.info(f"生成Word文档")
            logger.info(f"内容数据章节: {list(content_data.keys()) if content_data else '无'}")
            
            doc = DocumentGenerator.generate_word(title, outline_data, content_data)
            file_path = os.path.join(static_dir, f"{file_name}.docx")
            doc.save(file_path)
            # 构建相对URL路径，而不是绝对文件系统路径
            relative_path = f"documents/{file_name}.docx"
            logger.info(f"Word文档已保存: {file_path}, 相对路径: {relative_path}")
            
        else:
            logger.warning(f"不支持的文档类型: {document_type}")
            raise HTTPException(status_code=400, detail="不支持的文档类型")
        
        # 保存文件路径到请求数据中
        request_data["file_path"] = file_path
        request_data["relative_path"] = relative_path
        
        return {
            "success": True,
            "message": f"成功生成{document_type.upper()}文档",
            "file_path": relative_path  # 返回相对路径
        }
        
    except Exception as e:
        logger.error(f"生成文档时出错: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"生成文档失败: {str(e)}")

@router.post("/regenerate-content/{request_id}", response_model=WorkflowResponse)
async def regenerate_content(request_id: str):
    """当编辑标题或大纲后，重新生成内容"""
    logger.info(f"收到重新生成内容请求: request_id={request_id}")
    
    if request_id not in document_requests:
        logger.warning(f"请求ID不存在: {request_id}")
        raise HTTPException(status_code=404, detail="请求ID不存在")
    
    try:
        # 获取原始请求数据
        request_data = document_requests[request_id]
        
        # 记录重要信息以便调试
        logger.info(f"开始内容生成，标题: {request_data['title']}")
        logger.info(f"大纲章节数: {len(request_data['outline'])}")
        logger.info(f"大纲第一章节: {request_data['outline'][0]['title'] if request_data['outline'] else 'N/A'}")
        logger.info(f"用户是否编辑了标题: {request_data.get('user_edited_title', False)}")
        logger.info(f"用户是否编辑了大纲: {request_data.get('user_edited_outline', False)}")
        
        # 重新运行工作流，只执行内容生成阶段
        # 创建一个已包含标题和大纲的初始状态
        initial_state = {
            "topic": request_data["topic"],
            "page_limit": request_data["page_limit"],
            "document_type": request_data["document_type"],
            "current_step": "outline_generated",  # 从大纲完成阶段开始
            "error_message": None,
            "title": request_data["title"],
            "outline": request_data["outline"],
            "content": None,
            "user_edited_outline": request_data.get("user_edited_outline", False),
            "user_edited_title": request_data.get("user_edited_title", False),
            "request_id": request_id  # 添加请求ID到状态中
        }
        
        # 初始化进度
        generation_progress[request_id] = {
            "progress": 0,
            "current_stage": "initializing",
            "message": "正在初始化内容生成...",
            "current_section": None,
            "completed_sections": []
        }
        
        # 运行工作流获取新内容
        logger.info("开始调用工作流生成内容...")
        workflow_result = await run_document_workflow(
            topic=request_data["topic"],
            page_limit=request_data["page_limit"],
            document_type=request_data["document_type"],
            initial_state=initial_state,
            stop_at="content_generated"  # 执行到内容生成后停止
        )
        
        # 检查结果
        if workflow_result.get("content"):
            logger.info(f"内容生成成功，章节数: {len(workflow_result['content'])}")
            for chapter in workflow_result["content"].keys():
                logger.info(f"已生成章节: {chapter}")
        else:
            logger.warning("内容生成结果为空")
        
        # 更新请求数据的内容
        request_data["content"] = workflow_result["content"]
        request_data["needs_content_update"] = False
        
        message = "内容重新生成成功"
        if workflow_result.get("error_message"):
            message = f"内容部分重新生成成功，但有问题: {workflow_result.get('error_message')}"
        
        logger.info(f"内容重新生成完成: {message}")
        
        return {
            "success": workflow_result["current_step"] == "content_generated",
            "title": request_data["title"],
            "outline": request_data["outline"],
            "content": workflow_result["content"] or {},
            "request_id": request_id,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"重新生成内容时出错: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        
        return {
            "success": False,
            "title": document_requests[request_id]["title"],
            "outline": document_requests[request_id]["outline"],
            "content": document_requests[request_id].get("content", {}),
            "request_id": request_id,
            "message": f"重新生成内容失败: {str(e)}"
        }

# 添加别名端点，使/api/generate-content/{request_id}也能工作
@router.post("/generate-content/{request_id}", response_model=WorkflowResponse)
async def generate_content_alias(request_id: str):
    """生成内容的别名端点，转发到regenerate_content"""
    logger.info(f"通过别名端点收到内容生成请求: request_id={request_id}")
    return await regenerate_content(request_id) 