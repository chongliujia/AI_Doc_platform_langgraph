from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import tempfile
import os
import traceback
import json
import logging
import uuid
from io import BytesIO

from api.graph import generate_title, generate_outline, generate_content
from utils.document_generator import DocumentGenerator

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("api.routes")

router = APIRouter()

# 输入模型
class DocumentRequest(BaseModel):
    topic: str
    page_limit: int
    document_type: str  # "ppt" 或 "word"

# 标题生成请求
class TitleRequest(BaseModel):
    topic: str
    document_type: str

# 大纲生成请求
class OutlineRequest(BaseModel):
    topic: str
    title: str
    page_limit: int
    document_type: str

# 内容生成请求
class ContentRequest(BaseModel):
    topic: str
    title: str
    outline: List[Dict[str, Any]]
    document_type: str

# 大纲条目模型
class OutlineItem(BaseModel):
    title: str
    content: List[str]

# 大纲编辑模型
class OutlineEditRequest(BaseModel):
    outline: List[OutlineItem]

# 标题编辑模型
class TitleEditRequest(BaseModel):
    title: str

# 响应模型
class TitleResponse(BaseModel):
    success: bool
    title: str
    message: Optional[str] = None

class OutlineResponse(BaseModel):
    success: bool
    title: str
    outline: List[Dict[str, Any]]
    request_id: str
    message: Optional[str] = None

class ContentResponse(BaseModel):
    success: bool
    title: str
    outline: List[Dict[str, Any]]
    content: Dict[str, str]
    request_id: str
    message: Optional[str] = None

class GenerateDocumentResponse(BaseModel):
    success: bool
    message: str
    file_path: Optional[str] = None

# 内存存储（实际应用中应使用数据库）
document_requests = {}

@router.post("/generate-title", response_model=TitleResponse)
async def generate_title_endpoint(request: TitleRequest):
    """第一步：生成文档标题"""
    try:
        logger.info(f"收到标题生成请求: 主题={request.topic}, 类型={request.document_type}")
        
        # 调用标题生成智能体
        result = await generate_title(
            topic=request.topic, 
            document_type=request.document_type
        )
        
        if not result["success"]:
            logger.warning(f"标题生成失败: {result.get('error')}")
            return {
                "success": False,
                "title": result["title"],
                "message": f"标题生成过程中出现问题: {result.get('error')}"
            }
        
        logger.info(f"成功生成标题: {result['title']}")
        return {
            "success": True,
            "title": result["title"],
            "message": "标题生成成功"
        }
        
    except Exception as e:
        logger.error(f"标题生成异常: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "title": f"{request.topic}研究分析",
            "message": f"标题生成失败: {str(e)}"
        }

@router.post("/generate-outline", response_model=OutlineResponse)
async def generate_outline_endpoint(request: DocumentRequest):
    """第二步：基于主题生成标题和大纲（适配原有前端）"""
    try:
        logger.info(f"收到大纲生成请求: 主题={request.topic}, 页数={request.page_limit}")
        
        # 首先生成标题
        title_result = await generate_title(
            topic=request.topic, 
            document_type=request.document_type
        )
        
        title = title_result["title"]
        logger.info(f"生成标题: {title}")
        
        # 然后生成大纲
        outline_result = await generate_outline(
            topic=request.topic,
            title=title,
            page_limit=request.page_limit,
            document_type=request.document_type
        )
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        logger.info(f"生成请求ID: {request_id}")
        
        # 保存请求数据
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
        
        message = "大纲生成成功"
        if outline_result.get("error"):
            message = f"大纲生成部分成功，但有问题: {outline_result.get('error')}"
            
        logger.info(f"成功生成大纲，返回 {len(outline_result['outline'])} 个章节")
        return {
            "success": outline_result["success"],
            "title": title,
            "outline": outline_result["outline"],
            "request_id": request_id,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"大纲生成异常: {e}")
        logger.error(traceback.format_exc())
        
        # 创建基本大纲
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
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 保存基本数据
        document_requests[request_id] = {
            "topic": request.topic,
            "title": default_title,
            "outline": basic_outline,
            "document_type": request.document_type,
            "page_limit": request.page_limit,
            "content": None,
            "user_edited_title": False,
            "user_edited_outline": False
        }
        
        return {
            "success": False,
            "title": default_title,
            "outline": basic_outline,
            "request_id": request_id,
            "message": f"大纲生成失败，使用基本模板: {str(e)}"
        }

@router.put("/edit-title/{request_id}", response_model=OutlineResponse)
async def edit_title(request_id: str, title_edit: TitleEditRequest):
    """编辑文档标题"""
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
        
        # 标记内容需要重新生成
        request_data["content"] = None
        
        logger.info(f"标题已更新: {title_edit.title}")
        
        return {
            "success": True,
            "title": request_data["title"],
            "outline": request_data["outline"],
            "request_id": request_id,
            "message": "标题已更新"
        }
        
    except Exception as e:
        logger.error(f"编辑标题时出错: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"编辑标题失败: {str(e)}")

@router.put("/edit-outline/{request_id}", response_model=OutlineResponse)
async def edit_outline(request_id: str, outline_edit: OutlineEditRequest):
    """编辑文档大纲"""
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
        
        # 标记内容需要重新生成
        request_data["content"] = None
        
        logger.info(f"大纲已更新: {json.dumps(outline_dict)[:200]}...")
        
        return {
            "success": True,
            "title": request_data["title"],
            "outline": request_data["outline"],
            "request_id": request_id,
            "message": "大纲已更新"
        }
        
    except Exception as e:
        logger.error(f"编辑大纲时出错: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"编辑大纲失败: {str(e)}")

@router.post("/generate-content/{request_id}", response_model=ContentResponse)
async def generate_content_endpoint(request_id: str):
    """第三步：基于标题和大纲生成详细内容"""
    logger.info(f"收到内容生成请求: request_id={request_id}")
    
    if request_id not in document_requests:
        logger.warning(f"请求ID不存在: {request_id}")
        raise HTTPException(status_code=404, detail="请求ID不存在")
    
    try:
        # 获取原始请求数据
        request_data = document_requests[request_id]
        
        # 检查是否已有内容且未被编辑过大纲
        if request_data.get("content") and not request_data.get("user_edited_outline"):
            logger.info("已有内容且大纲未被编辑，直接返回")
            return {
                "success": True,
                "title": request_data["title"],
                "outline": request_data["outline"],
                "content": request_data["content"],
                "request_id": request_id,
                "message": "使用已有内容"
            }
        
        # 调用内容生成智能体，传递页数限制参数
        result = await generate_content(
            title=request_data["title"],
            topic=request_data["topic"],
            outline=request_data["outline"],
            document_type=request_data["document_type"],
            page_limit=request_data["page_limit"]  # 传递页数限制
        )
        
        # 更新保存的状态
        request_data["content"] = result["content"]
        
        message = result.get("status", "内容生成完成")
        if not result["success"] and result.get("partial_success"):
            message = "部分内容生成成功，部分失败"
        elif not result["success"]:
            message = f"内容生成失败: {result.get('error')}"
        
        logger.info(f"内容生成完成: {message}")
        return {
            "success": result["success"] or result.get("partial_success", False),
            "title": request_data["title"],
            "outline": request_data["outline"],
            "content": result["content"],
            "request_id": request_id,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"生成内容时出错: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        
        # 创建空内容
        empty_content = {}
        for section in document_requests[request_id]["outline"]:
            empty_content[section["title"]] = "内容生成失败，请手动填写或重试。"
        
        # 更新请求数据
        document_requests[request_id]["content"] = empty_content
        
        return {
            "success": False,
            "title": document_requests[request_id]["title"],
            "outline": document_requests[request_id]["outline"],
            "content": empty_content,
            "request_id": request_id,
            "message": f"内容生成失败: {str(e)}"
        }

@router.post("/generate-document/{request_id}", response_model=GenerateDocumentResponse)
async def generate_document(request_id: str, background_tasks: BackgroundTasks):
    """第四步：生成最终文档（如果还没有内容数据，会先自动生成内容）"""
    try:
        logger.info(f"收到生成文档请求: request_id={request_id}")
        
        if request_id not in document_requests:
            logger.warning(f"找不到request_id: {request_id}")
            raise HTTPException(status_code=404, detail=f"找不到对应的请求记录")
        
        request_data = document_requests[request_id]
        title = request_data["title"]
        outline_data = request_data["outline"]
        document_type = request_data["document_type"]
        page_limit = request_data["page_limit"]
        content_data = request_data.get("content")
        
        # 如果没有内容数据，尝试生成内容
        if not content_data:
            logger.info(f"内容数据不存在，尝试生成内容...")
            
            # 生成内容
            content_result = await generate_content(
                title=title,
                outline=outline_data,
                topic=request_data["topic"],
                document_type=document_type,
                page_limit=page_limit
            )
            
            if content_result["success"] or content_result.get("partial_success", False):
                content_data = content_result["content"]
                logger.info(f"成功生成内容: {len(content_data)} 个章节")
                request_data["content"] = content_data
            else:
                # 如果内容生成失败，返回错误
                logger.warning(f"内容生成失败: {content_result.get('error')}")
                raise HTTPException(status_code=500, detail=f"内容生成失败: {content_result.get('error')}")
        
        # 验证内容数据
        if not content_data or not any(content_data.values()):
            logger.warning("内容数据为空")
            raise HTTPException(status_code=500, detail="内容数据为空，无法生成文档")
        
        # 获取静态文件目录，用于保存生成的文件
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "static", "documents")
        os.makedirs(static_dir, exist_ok=True)
        
        # 根据文档类型生成相应的文档
        file_name = f"{title.replace(' ', '_').replace('/', '_')}_{request_id[-8:]}"
        
        if document_type.lower() == "ppt":
            # 生成PPT
            logger.info(f"生成PPT文档，页数限制: {page_limit}")
            logger.info(f"内容数据章节: {list(content_data.keys()) if content_data else '无'}")
            
            # 打印一些内容数据的样本，帮助调试
            if content_data:
                for key, value in list(content_data.items())[:1]:  # 只打印第一个章节的样本
                    logger.info(f"章节 '{key}' 内容样本: {value[:100]}...")
            
            ppt = DocumentGenerator.generate_ppt(title, outline_data, content_data, page_limit)
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

# 为保持向后兼容，保留旧的API端点
@router.post("/generate-outline-legacy", response_model=OutlineResponse)
async def generate_outline_legacy(request: DocumentRequest):
    """旧版API：一次性生成标题和大纲"""
    logger.info(f"收到旧版大纲生成请求: 主题={request.topic}, 页数={request.page_limit}, 类型={request.document_type}")
    
    try:
        # 首先生成标题
        title_result = await generate_title(
            topic=request.topic, 
            document_type=request.document_type
        )
        
        title = title_result["title"]
        
        # 然后生成大纲
        outline_result = await generate_outline(
            topic=request.topic,
            title=title,
            page_limit=request.page_limit,
            document_type=request.document_type
        )
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        logger.info(f"生成请求ID: {request_id}")
        
        # 保存请求数据
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
        
        logger.info(f"成功生成标题和大纲: {title}")
        return {
            "success": True,
            "title": title,
            "outline": outline_result["outline"],
            "request_id": request_id,
            "message": "标题和大纲生成成功"
        }
        
    except Exception as e:
        logger.error(f"标题和大纲生成异常: {e}")
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
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 保存基本数据
        document_requests[request_id] = {
            "topic": request.topic,
            "title": default_title,
            "outline": basic_outline,
            "document_type": request.document_type,
            "page_limit": request.page_limit,
            "content": None,
            "user_edited_title": False,
            "user_edited_outline": False
        }
        
        return {
            "success": False,
            "title": default_title,
            "outline": basic_outline,
            "request_id": request_id,
            "message": f"生成失败，使用基本模板: {str(e)}"
        } 