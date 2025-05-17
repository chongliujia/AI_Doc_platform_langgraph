"""
基于LangGraph的文档生成工作流包装器
这个文件作为兼容层，将原有API调用转发到新的LangGraph实现
"""

from typing import TypedDict, List, Dict, Any, Optional
import traceback

# 导入LangGraph实现
from api.langgraph_impl import (
    run_document_workflow,
    DocumentState
)

# 保留generate_default_outline函数作为备用
def generate_default_outline(topic: str, page_limit: int):
    """当API调用失败时生成默认大纲"""
    # 改进的页数计算逻辑
    # 标题页和目录页占用2页
    # 每个主要章节平均占用1-2页
    # 在有详细内容的情况下，每个章节可能需要额外的页数
    available_pages = max(3, page_limit - 2)  # 减去标题和目录页
    max_sections = min(10, available_pages)  # 最多10个章节
    
    # 根据可用页数调整章节数
    if available_pages <= 5:
        sections_count = 3  # 精简版，3个章节
    elif available_pages <= 10:
        sections_count = 4  # 标准版，4个章节
    else:
        sections_count = 5 + (available_pages - 10) // 3  # 更多页数，更多章节
        sections_count = min(max_sections, sections_count)  # 限制最大章节数
    
    # 根据章节数调整每个章节的内容点数
    points_per_section = 3
    if available_pages > 8:
        points_per_section = 4
    if available_pages > 15:
        points_per_section = 5
    
    default_outline = []
    if sections_count >= 5:
        # 扩展版大纲 (5+ 章节)
        default_outline = [
            {
                "title": "引言与背景",
                "content": ["研究背景", "主题重要性", "研究目的与范围"][:points_per_section]
            },
            {
                "title": "理论基础",
                "content": ["核心概念定义", "相关理论综述", "研究方法论", "理论框架"][:points_per_section]
            },
            {
                "title": "现状分析",
                "content": ["行业/领域现状", "关键问题与挑战", "案例研究", "数据分析"][:points_per_section]
            },
            {
                "title": "解决方案与实践",
                "content": ["创新思路", "实施策略", "应用案例", "效果评估", "优化建议"][:points_per_section]
            },
            {
                "title": "总结与展望",
                "content": ["研究结论", "主要贡献", "局限性", "未来研究方向", "政策或实践建议"][:points_per_section]
            }
        ]
        
        # 如果章节数 > 5，添加额外章节
        if sections_count > 5:
            additional_sections = [
                {
                    "title": "对比研究",
                    "content": ["方法比较", "不同视角分析", "优缺点评估", "适用场景"][:points_per_section]
                },
                {
                    "title": "技术实现",
                    "content": ["技术架构", "关键组件", "实现流程", "性能评估", "安全考虑"][:points_per_section]
                },
                {
                    "title": "经济与社会影响",
                    "content": ["经济效益分析", "社会影响评估", "可持续性考量", "伦理问题讨论"][:points_per_section]
                },
                {
                    "title": "用户研究",
                    "content": ["用户需求分析", "用户体验设计", "用户反馈与评估", "改进策略"][:points_per_section]
                },
                {
                    "title": "前沿趋势",
                    "content": ["最新研究动态", "技术发展趋势", "创新方向", "未来应用场景"][:points_per_section]
                }
            ]
            default_outline.extend(additional_sections[:sections_count-5])
            
    elif sections_count >= 4:
        # 标准版大纲 (4 章节)
        default_outline = [
            {
                "title": "概述与背景",
                "content": ["主题概述", "背景信息", "研究意义", "核心问题"][:points_per_section]
            },
            {
                "title": "核心内容分析",
                "content": ["关键要素", "主要观点", "数据分析", "理论基础", "方法论"][:points_per_section]
            },
            {
                "title": "应用与实践",
                "content": ["实际应用场景", "实施方法", "案例分析", "效果评估", "优化建议"][:points_per_section]
            },
            {
                "title": "总结与展望",
                "content": ["主要结论", "未来趋势", "建议与展望", "研究局限性"][:points_per_section]
            }
        ]
    else:
        # 精简版大纲 (3 章节)
        default_outline = [
            {
                "title": "主题概述",
                "content": ["背景介绍", "核心问题", "研究方法", "主要目标"][:points_per_section]
            },
            {
                "title": "分析与讨论",
                "content": ["关键发现", "重要观点", "数据解读", "案例分析", "比较研究"][:points_per_section]
            },
            {
                "title": "结论与建议",
                "content": ["总结要点", "应用建议", "未来展望", "实践意义"][:points_per_section]
            }
        ]
    
    # 根据页数限制调整章节数量
    default_outline = default_outline[:sections_count]
    
    return {
        "title": f"{topic}研究分析",
        "outline": default_outline,
        "estimated_pages": 2 + len(default_outline)  # 标题页+目录页+章节数
    }

# 为了兼容现有API，我们提供与原始函数签名匹配的包装器

# 1. 标题智能体包装器
async def generate_title(topic: str, document_type: str, page_limit: int = 10):
    """根据主题生成标题（LangGraph实现）"""
    try:
        # 运行工作流，只执行到标题生成步骤
        initial_state: DocumentState = {
            "topic": topic,
            "document_type": document_type,
            "page_limit": page_limit,  # 使用传入的页数参数
            "current_step": "started",
            "error_message": None,
            "title": None,
            "outline": None,
            "content": None,
            "user_edited_outline": False,
            "user_edited_title": False
        }
        
        # 配置只运行到标题生成
        result = await run_document_workflow(
            topic=topic,
            page_limit=page_limit,  # 使用传入的页数参数
            document_type=document_type,
            initial_state=initial_state,
            stop_at="title_generated"  # 在生成标题后停止
        )
        
        success = result["current_step"] == "title_generated"
        title = result["title"] or f"{topic}研究分析"
        error = result.get("error_message")
        
        return {
            "success": success,
            "title": title,
            "error": error
        }
    
    except Exception as e:
        print(f"标题智能体执行出错: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        
        # 返回默认标题
        return {
            "success": False,
            "title": f"{topic}研究分析",
            "error": f"生成标题时出错: {str(e)}"
        }

# 2. 大纲智能体包装器
async def generate_outline(topic: str, title: str, page_limit: int, document_type: str):
    """根据标题和页数限制生成大纲（LangGraph实现）"""
    try:
        # 运行工作流，从标题开始，执行到大纲生成步骤
        initial_state: DocumentState = {
            "topic": topic,
            "document_type": document_type,
            "page_limit": page_limit,
            "current_step": "title_generated",
            "error_message": None,
            "title": title,
            "outline": None,
            "content": None,
            "user_edited_outline": False,
            "user_edited_title": False
        }
        
        # 配置从标题生成之后运行，到大纲生成后停止
        result = await run_document_workflow(
            topic=topic,
            page_limit=page_limit,
            document_type=document_type,
            initial_state=initial_state,
            stop_at="outline_generated"  # 在生成大纲后停止
        )
        
        success = result["current_step"] == "outline_generated"
        outline = result["outline"]
        error = result.get("error_message")
        
        # 如果大纲为空，使用默认大纲
        if not outline:
            default_data = generate_default_outline(topic, page_limit)
            outline = default_data["outline"]
            
        return {
            "success": success,
            "outline": outline,
            "estimated_pages": 2 + len(outline),  # 简单估算: 标题页+目录页+章节数
            "error": error
        }
    
    except Exception as e:
        print(f"大纲智能体执行出错: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        
        # 使用默认大纲
        default_data = generate_default_outline(topic, page_limit)
        
        return {
            "success": False,
            "outline": default_data["outline"],
            "estimated_pages": default_data.get("estimated_pages", 2 + len(default_data["outline"])),
            "error": f"大纲生成过程中出错: {str(e)}"
        }

# 3. 内容智能体包装器
async def generate_content(title: str, topic: str, outline: List[Dict[str, Any]], document_type: str = "ppt", page_limit: int = None):
    """根据标题和大纲生成每个章节的详细内容（LangGraph实现）"""
    try:
        # 运行工作流，从大纲开始，执行到内容生成步骤
        initial_state: DocumentState = {
            "topic": topic,
            "document_type": document_type,
            "page_limit": page_limit or 15,  # 提供默认值
            "current_step": "outline_generated",
            "error_message": None,
            "title": title,
            "outline": outline,
            "content": None,
            "user_edited_outline": False,
            "user_edited_title": False
        }
        
        # 配置从大纲生成之后运行，到内容生成后停止
        result = await run_document_workflow(
            topic=topic,
            page_limit=page_limit or 15,
            document_type=document_type,
            initial_state=initial_state,
            stop_at="content_generated"  # 在生成内容后停止
        )
        
        success = result["current_step"] == "content_generated"
        content = result["content"]
        error = result.get("error_message")
        
        # 如果内容为空，创建默认内容
        if not content:
            content = {}
            for section in outline:
                section_title = section["title"]
                section_points = section["content"]
                
                default_content = f"本章节主要介绍{section_title}的核心内容。\n\n"
                for point in section_points:
                    default_content += f"- {point}：此部分将详细阐述相关内容。\n"
                
                content[section_title] = default_content
        
        return {
            "success": success,
            "partial_success": True,  # 即使有错误，也至少返回部分内容
            "content": content,
            "status": "内容生成完成",
            "error": error
        }
    
    except Exception as e:
        print(f"内容智能体执行出错: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        
        # 创建默认内容
        content = {}
        for section in outline:
            section_title = section["title"]
            section_points = section["content"]
            
            default_content = f"本章节主要介绍{section_title}的核心内容。\n\n"
            for point in section_points:
                default_content += f"- {point}：此部分将详细阐述相关内容。\n"
            
            content[section_title] = default_content
        
        return {
            "success": False,
            "partial_success": True,  # 提供默认内容
            "content": content,
            "status": "内容生成过程中发生错误，使用默认内容替代",
            "error": f"生成内容时出错: {str(e)}"
        }

# 使用LangGraph定义文档生成工作流
def create_document_workflow():
    """使用LangGraph创建文档生成工作流
    
    注意：这个函数只是为了保持API兼容，实际实现已经移到langgraph_impl模块中
    """
    # 直接导入langgraph_impl中的工作流创建函数
    from api.langgraph_impl import create_complete_workflow
    return create_complete_workflow()

# 提供一个运行完整工作流的函数
async def run_document_workflow(topic: str, page_limit: int, document_type: str, initial_state: Optional[DocumentState] = None, stop_at: Optional[str] = None) -> DocumentState:
    """运行文档生成工作流，可以在指定步骤停止
    
    Args:
        topic: 文档主题
        page_limit: 页数限制
        document_type: 文档类型 ("ppt" 或 "word")
        initial_state: 可选的初始状态，用于从特定阶段开始工作流
        stop_at: 可选，工作流执行到此步骤后停止，例如 "title_generated" 或 "outline_generated"
        
    Returns:
        完成的工作流状态
    """
    # 这里直接调用langgraph_impl中的实现，确保行为一致
    from api.langgraph_impl import run_document_workflow as run_workflow_impl
    return await run_workflow_impl(topic, page_limit, document_type, initial_state, stop_at) 