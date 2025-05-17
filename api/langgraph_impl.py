"""
基于LangGraph的文档生成工作流实现。
这个文件包含了使用LangGraph构建的完整文档生成流程。
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal, Union, Annotated
import json
import traceback
import re
import os

# LangChain和LangGraph导入
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import RunnablePassthrough, Runnable
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# 导入实用工具
from utils.deepseek_client import DeepSeekClient, LangChainClient

# 初始化AI客户端
deepseek_client = DeepSeekClient()
use_langchain = False  # 强制使用原生DeepSeek客户端
langchain_client = None  # 不再初始化LangChain客户端

def get_llm():
    """获取活跃的LLM"""
    print("使用DeepSeek LLM")
    # 返回llm属性，而不是deepseek_client本身
    return deepseek_client.llm

# ===============================
# 状态和模型定义
# ===============================

class DocumentState(TypedDict):
    """文档生成工作流的状态"""
    # 用户输入
    topic: str                  # 文档主题
    page_limit: int             # 页数限制
    document_type: str          # "ppt" 或 "word"
    
    # 流程状态
    current_step: str           # 当前步骤
    error_message: Optional[str]  # 错误信息
    
    # 生成内容
    title: Optional[str]        # 标题
    outline: Optional[List[Dict[str, Any]]]  # 大纲
    content: Optional[Dict[str, str]]  # 各章节内容
    
    # 用户编辑标志
    user_edited_outline: Optional[bool]
    user_edited_title: Optional[bool]

# ===============================
# 标题生成组件
# ===============================

class TitleResponse(BaseModel):
    """标题生成响应"""
    title: str = Field(description="生成的标题")

def create_title_chain() -> Runnable:
    """创建标题生成链"""
    # 系统提示
    system_prompt = """你是一个专业的标题生成专家。你能根据用户提供的主题，生成简洁、专业且吸引人的标题。"""
    
    # 用户提示模板
    user_template = """
    请为以下主题生成一个简洁、吸引人且专业的{document_type}文档标题:
    
    主题: {topic}
    
    要求:
    1. 标题应该简洁明了，不超过20个字
    2. 标题应该能准确反映主题的核心内容
    3. 标题应该吸引读者的兴趣
    4. 只需要返回标题文本，不需要其他说明
    """
    
    # 创建提示
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_template)
    ])
    
    # 创建链
    # 使用通用处理方式
    llm = get_llm()
    
    # 组装链
    chain = prompt | llm | StrOutputParser()
    
    return chain

async def generate_title_node(state: DocumentState) -> Dict[str, Any]:
    """标题生成节点"""
    try:
        # 创建标题生成链
        title_chain = create_title_chain()
        
        # 准备参数
        params = {
            "topic": state["topic"],
            "document_type": state["document_type"].upper()
        }
        
        # 调用链生成标题
        title_result = await title_chain.ainvoke(params)
        
        # 清理标题（去除多余空格、引号等）
        title = title_result.strip().strip('"').strip("'").strip()
        
        if not title:
            # 如果标题为空，使用默认标题
            title = f"{state['topic']}研究分析"
        
        print(f"生成的标题: {title}")
        
        # 更新状态
        return {
            "title": title,
            "current_step": "title_generated"
        }
        
    except Exception as e:
        print(f"生成标题时出错: {e}")
        traceback.print_exc()
        
        # 返回默认标题和错误信息
        return {
            "title": f"{state['topic']}研究分析",
            "error_message": f"生成标题时出错: {str(e)}",
            "current_step": "title_generated_with_error"
        }

# ===============================
# 大纲生成组件
# ===============================

class OutlineSection(BaseModel):
    """大纲章节"""
    title: str = Field(description="章节标题")
    content: List[str] = Field(description="章节内容要点")

class OutlineResponse(BaseModel):
    """大纲生成响应"""
    outline: List[OutlineSection] = Field(description="文档大纲")
    estimated_pages: int = Field(description="估计总页数")

def get_topic_specific_prompt(topic: str) -> str:
    """获取主题特定提示"""
    topic_lower = topic.lower()
    
    if "强化学习" in topic or "reinforcement learning" in topic_lower:
        return """
        请确保大纲涵盖强化学习的关键方面:
        - 强化学习基本概念和理论基础
        - 经典算法
        - 深度强化学习方法
        - 实际应用案例
        - 当前研究热点和挑战
        """
    elif "机器学习" in topic or "machine learning" in topic_lower:
        return """
        请确保大纲涵盖机器学习的关键方面:
        - 监督、无监督和半监督学习基本概念
        - 经典算法
        - 神经网络和深度学习基础
        - 实际应用场景和案例分析
        - 模型评估方法和最佳实践
        """
    # 其他领域...
    else:
        return f"""
        请为{topic}主题创建专业、详细的大纲，确保内容全面且深入，
        使用与主题相关的具体专业术语和概念。每个章节有3-5个具体内容要点。
        """

def determine_section_count(document_type: str, page_limit: int) -> Dict[str, Any]:
    """根据文档类型和页数确定章节数和指南"""
    if document_type.lower() == "ppt":
        if page_limit <= 5:
            return {"count": 2, "guide": "只创建2个核心章节，每章节2-3个要点"}
        elif page_limit <= 10:
            return {"count": 3, "guide": "创建3个章节，每章节3-4个要点"}
        elif page_limit <= 15:
            return {"count": 4, "guide": "创建4个关键章节，每章节3-5个要点"}
        else:
            return {"count": 5, "guide": "创建5个详细章节，每章节4-5个要点"}
    else:  # Word文档
        if page_limit <= 3:
            return {"count": 2, "guide": "只创建2个核心章节"}
        elif page_limit <= 7:
            return {"count": 3, "guide": "创建3个章节"}
        elif page_limit <= 12:
            return {"count": 4, "guide": "创建4个关键章节"}
        else:
            return {"count": 5, "guide": "创建5个或更多详细章节"}

def create_outline_chain() -> Runnable:
    """创建大纲生成链"""
    # 系统提示
    system_prompt = """你是一个专业的文档大纲设计专家。你能根据用户提供的主题和标题，生成结构清晰、内容全面的文档大纲。"""
    
    # 用户提示模板
    user_template = """
    请为以下标题生成一个{document_type}文档的详细大纲，页数限制为{page_limit}页:
    
    标题: {title}
    主题: {topic}
    
    {topic_specific}
    
    大纲结构要求:
    1. 标题页和目录页将占用2页
    2. 根据{page_limit}页的限制，应该生成约{section_count}个章节
    3. {section_guide}
    4. 每个章节标题必须与主题紧密相关
    5. 章节标题应该简洁明了，反映该部分的核心内容
    6. 章节要点应该具体、专业，不要使用通用占位符
    
    {format_instructions}
    """
    
    # 创建提示
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_template)
    ])
    
    # 获取模型
    llm = get_llm()
    
    # 创建解析器
    parser = JsonOutputParser(pydantic_object=OutlineResponse)
    
    # 创建链
    chain = prompt | llm | parser
    
    return chain

def validate_outline(outline: Union[List[OutlineSection], List[Dict[str, Any]], Any], topic: str) -> List[Dict[str, Any]]:
    """验证和规范化大纲"""
    validated_outline = []
    
    # 处理可能的字符串输入 (JSON字符串)
    if isinstance(outline, str):
        try:
            outline = json.loads(outline)
        except:
            # 如果无法解析，创建默认大纲
            return [
                {
                    "title": "主题概述",
                    "content": ["背景介绍", "核心问题", "主要目标"]
                },
                {
                    "title": f"{topic}分析",
                    "content": ["关键发现", "重要观点", "数据解读"]
                },
                {
                    "title": "总结与展望",
                    "content": ["主要结论", "应用建议", "未来展望"]
                }
            ]
    
    # 确保outline是列表
    if not isinstance(outline, list):
        # 尝试获取可能的outline字段
        if isinstance(outline, dict) and "outline" in outline:
            outline = outline["outline"]
        else:
            # 创建默认大纲
            return [
                {
                    "title": "主题概述",
                    "content": ["背景介绍", "核心问题", "主要目标"]
                },
                {
                    "title": f"{topic}分析",
                    "content": ["关键发现", "重要观点", "数据解读"]
                },
                {
                    "title": "总结与展望",
                    "content": ["主要结论", "应用建议", "未来展望"]
                }
            ]
    
    for section in outline:
        # 处理不同类型的输入
        if isinstance(section, dict):
            section_title = section.get("title", "")
            section_content = section.get("content", [])
        else:
            # 尝试获取属性
            try:
                section_title = section.title
                section_content = section.content
            except:
                section_title = ""
                section_content = []
        
        # 检查标题
        if not section_title or section_title == "章节标题":
            section_title = f"{topic}分析"
            
        # 确保section_content是列表
        if not isinstance(section_content, list):
            try:
                # 尝试将字符串分割成列表
                if isinstance(section_content, str):
                    section_content = [item.strip() for item in section_content.split(',')]
                else:
                    section_content = ["背景介绍", "关键概念", "应用场景"]
            except:
                section_content = ["背景介绍", "关键概念", "应用场景"]
        
        # 检查内容
        if not section_content or len(section_content) == 0:
            section_content = ["背景介绍", "关键概念", "应用场景"]
        else:
            # 规范化内容点
            for i, point in enumerate(section_content):
                if point in ["具体要点1", "要点1", "关键点1"]:
                    section_content[i] = f"{section_title}的重要方面"
        
        # 添加验证后的章节
        validated_outline.append({
            "title": section_title,
            "content": section_content
        })
    
    return validated_outline

async def generate_outline_node(state: DocumentState) -> Dict[str, Any]:
    """大纲生成节点"""
    try:
        # 创建大纲生成链
        outline_chain = create_outline_chain()
        
        # 获取章节信息
        section_info = determine_section_count(state["document_type"], state["page_limit"])
        
        # 创建解析器
        parser = JsonOutputParser(pydantic_object=OutlineResponse)
        
        # 准备参数
        params = {
            "topic": state["topic"],
            "title": state["title"],
            "document_type": state["document_type"].upper(),
            "page_limit": state["page_limit"],
            "topic_specific": get_topic_specific_prompt(state["topic"]),
            "section_count": section_info["count"],
            "section_guide": section_info["guide"],
            "format_instructions": parser.get_format_instructions()
        }
        
        # 调用链生成大纲
        outline_result = await outline_chain.ainvoke(params)
        
        # 处理结果，可能是字典或OutlineResponse对象
        if isinstance(outline_result, dict):
            outline_data = outline_result.get("outline", [])
        else:
            outline_data = outline_result.outline
            
        # 验证和规范化大纲
        validated_outline = validate_outline(outline_data, state["topic"])
        
        print(f"生成大纲成功: {len(validated_outline)}个章节")
        
        # 更新状态
        return {
            "outline": validated_outline,
            "current_step": "outline_generated"
        }
        
    except Exception as e:
        print(f"生成大纲时出错: {e}")
        traceback.print_exc()
        
        # 创建默认大纲
        default_outline = [
            {
                "title": "主题概述",
                "content": ["背景介绍", "核心问题", "研究方法", "主要目标"]
            },
            {
                "title": "分析与讨论",
                "content": ["关键发现", "重要观点", "数据解读", "案例分析"]
            },
            {
                "title": "结论与建议",
                "content": ["总结要点", "应用建议", "未来展望", "实践意义"]
            }
        ]
        
        # 返回默认大纲和错误信息
        return {
            "outline": default_outline,
            "error_message": f"生成大纲时出错: {str(e)}",
            "current_step": "outline_generated_with_error"
        }

# ===============================
# 内容生成组件
# ===============================

async def generate_section_content(
    title: str,
    topic: str,
    section_title: str,
    section_points: List[str],
    document_type: str,
    page_limit: Optional[int] = None
) -> str:
    """为单个章节生成内容"""
    try:
        # 构建内容生成提示
        points_text = "\n".join([f"- {point}" for point in section_points])
        
        # 构建章节特定提示
        section_guide = f"""
        本章节'{section_title}'是关于'{title}'和'{topic}'的重要组成部分。
        请确保内容紧密围绕章节标题'{section_title}'和以下具体要点展开，不要偏离主题：
        {points_text}
        
        每个要点都应得到充分解释，并且内容必须与总主题'{title}'保持一致。
        """
        
        # 设置内容格式要求
        if document_type.lower() == "ppt":
            min_length = 300
            format_guide = """
            PPT内容格式要求:
            1. 内容精炼，适合双栏布局展示
            2. 使用要点式表达，每行控制在50-60个字符
            3. 每个要点用完整的句子表达关键信息
            4. 使用破折号(-)或短横线开始每个要点
            5. 重要概念使用单独的行展示
            6. 段落之间用空行分隔，改善PPT排版
            """
        else:
            min_length = 600
            format_guide = """
            Word文档格式要求:
            1. 内容应详细、全面，使用完整段落
            2. 每个要点展开为2-3个段落
            3. 可以使用小标题来区分不同部分
            4. 段落之间用空行分隔，便于排版
            """
        
        # 页数限制指南
        page_limit_guide = ""
        if page_limit:
            if document_type.lower() == "ppt":
                # 简单估算，假设每页PPT约200-300字
                words_per_section = (page_limit - 2) * 250 // 5  # 减去标题页和目录页
                page_limit_guide = f"内容长度控制在约{words_per_section}字左右，适合PPT展示"
            else:
                # Word文档每页约500字
                words_per_section = (page_limit - 2) * 500 // 5
                page_limit_guide = f"内容长度控制在约{words_per_section}字左右"
        
        # 构建完整提示
        prompt = f"""
        请为以下文档章节生成专业的内容，适用于{document_type.upper()}:
        
        文档标题: {title}
        文档主题: {topic}
        章节标题: {section_title}
        
        章节要点:
        {points_text}
        
        {section_guide}
        
        {format_guide}
        
        {page_limit_guide}
        
        内容要求:
        1. 内容必须高度相关，准确解释章节标题下的每个要点
        2. 使用专业、清晰的语言，引用相关概念和术语
        3. 内容应该连贯、有逻辑性，避免重复
        4. 确保内容具有教育价值和信息量
        5. 生成至少{min_length}字符的内容
        6. 不要添加额外的引言或总结，直接开始核心内容
        
        请直接返回生成的内容，不要包含额外的说明或标记。
        """
        
        # 调用LLM生成内容
        content = await get_llm().ainvoke([HumanMessage(content=prompt)])
        
        # 提取生成的文本
        generated_text = content.content.strip()
        
        # 内容质量检查
        if len(generated_text) < min_length:
            # 如果内容太短，尝试扩展
            expand_prompt = f"""
            你生成的内容太简短。请扩展并丰富以下内容，使其更加详细和专业：
            
            {generated_text}
            
            请确保扩展后的内容:
            1. 详细解释每个要点
            2. 使用专业术语和概念
            3. 提供具体的例子或应用场景
            4. 长度至少{min_length}字符
            """
            
            expanded_content = await get_llm().ainvoke([HumanMessage(content=expand_prompt)])
            generated_text = expanded_content.content.strip()
        
        # 内容格式优化
        if document_type.lower() == "ppt":
            # 对PPT内容进行格式优化
            lines = generated_text.split('\n')
            formatted_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    formatted_lines.append("")  # 保留空行
                    continue
                
                # 处理过长的行
                if len(line) > 60:
                    parts = re.split(r'([。；，！？\.;,!?])', line)
                    current_part = ""
                    for i in range(0, len(parts)-1, 2):
                        part = parts[i] + (parts[i+1] if i+1 < len(parts) else "")
                        if len(current_part) + len(part) < 60:
                            current_part += part
                        else:
                            if current_part:
                                formatted_lines.append(current_part)
                            current_part = part
                    if current_part:
                        formatted_lines.append(current_part)
                else:
                    formatted_lines.append(line)
            
            # 重新组合内容
            generated_text = '\n'.join(formatted_lines)
        
        return generated_text
        
    except Exception as e:
        print(f"生成章节'{section_title}'内容时出错: {e}")
        traceback.print_exc()
        
        # 返回默认内容
        default_content = f"本章节主要介绍{section_title}的核心内容。\n\n"
        for point in section_points:
            default_content += f"- {point}：此部分将详细阐述相关内容。\n"
        
        return default_content

async def generate_content_node(state: DocumentState) -> Dict[str, Any]:
    """内容生成节点"""
    try:
        print(f"内容智能体：正在为'{state['title']}'生成详细内容...")
        
        outline = state["outline"]
        content_dict = {}
        success_count = 0
        error_count = 0
        
        # 为每个章节生成内容
        for section in outline:
            section_title = section["title"]
            section_points = section["content"]
            
            try:
                print(f"正在生成章节'{section_title}'的内容...")
                
                # 生成章节内容
                section_content = await generate_section_content(
                    title=state["title"],
                    topic=state["topic"],
                    section_title=section_title,
                    section_points=section_points,
                    document_type=state["document_type"],
                    page_limit=state["page_limit"]
                )
                
                # 保存内容
                content_dict[section_title] = section_content
                success_count += 1
                print(f"成功生成章节'{section_title}'的内容")
                
            except Exception as section_error:
                print(f"生成章节'{section_title}'内容时出错: {section_error}")
                
                # 创建默认内容
                default_content = f"本章节主要介绍{section_title}的核心内容。\n\n"
                for point in section_points:
                    default_content += f"- {point}：此部分将详细阐述相关内容。\n"
                
                content_dict[section_title] = default_content
                error_count += 1
        
        # 确定成功状态
        overall_success = error_count == 0
        
        # 创建状态更新
        status_update = {
            "content": content_dict,
            "current_step": "content_generated",
        }
        
        if not overall_success:
            status_update["error_message"] = f"{error_count}个章节内容生成失败"
        
        return status_update
        
    except Exception as e:
        print(f"内容生成节点错误: {e}")
        traceback.print_exc()
        
        # 创建所有章节的默认内容
        content_dict = {}
        for section in state["outline"]:
            section_title = section["title"]
            section_points = section["content"]
            
            default_content = f"本章节主要介绍{section_title}的核心内容。\n\n"
            for point in section_points:
                default_content += f"- {point}：此部分将详细阐述相关内容。\n"
            
            content_dict[section_title] = default_content
        
        # 返回默认内容和错误信息
        return {
            "content": content_dict,
            "error_message": f"内容生成时出错: {str(e)}",
            "current_step": "content_generated_with_error"
        }

# ===============================
# 主工作流
# ===============================

def create_complete_workflow() -> Runnable:
    """创建完整的文档生成工作流"""
    # 创建工作流图
    workflow = StateGraph(DocumentState)
    
    # 添加节点
    workflow.add_node("generate_title", generate_title_node)
    workflow.add_node("generate_outline", generate_outline_node)
    workflow.add_node("generate_content", generate_content_node)
    
    # 添加边
    workflow.add_edge("generate_title", "generate_outline")
    workflow.add_edge("generate_outline", "generate_content")
    workflow.add_edge("generate_content", END)
    
    # 当标题或大纲生成失败时的路由
    def route_on_error(state: DocumentState):
        if state.get("error_message"):
            # 即使有错误也继续到下一步
            return True
        return True
    
    # 添加条件边
    workflow.add_conditional_edges(
        "generate_title",
        route_on_error,
        {
            True: "generate_outline",
        }
    )
    
    workflow.add_conditional_edges(
        "generate_outline",
        route_on_error,
        {
            True: "generate_content",
        }
    )
    
    # 设置入口点
    workflow.set_entry_point("generate_title")
    
    # 编译工作流 - 更新为适配LangGraph 0.3.0+版本
    return workflow.compile()

async def run_document_workflow(
    topic: str,
    page_limit: int,
    document_type: str,
    initial_state: Optional[DocumentState] = None,
    stop_at: Optional[str] = None  # 添加stop_at参数
) -> DocumentState:
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
    # 初始化状态
    if initial_state is None:
        initial_state = {
            "topic": topic,
            "page_limit": page_limit,
            "document_type": document_type,
            "current_step": "started",
            "error_message": None,
            "title": None,
            "outline": None,
            "content": None,
            "user_edited_outline": False,
            "user_edited_title": False
        }
    else:
        # 确保基本参数一致
        initial_state["topic"] = topic
        initial_state["page_limit"] = page_limit
        initial_state["document_type"] = document_type
    
    # 创建工作流
    workflow = create_complete_workflow()
    
    # 确定入口点 - 在新版LangGraph中需要手动处理不同的入口点
    entry_point = "generate_title"  # 默认从开始
    
    # 记录工作流执行开始
    print(f"开始执行文档生成工作流，入口点: {entry_point}")
    print(f"主题: {topic}, 页数: {page_limit}, 文档类型: {document_type}")
    
    # 运行工作流
    try:
        # 根据当前状态和stop_at参数决定执行策略
        current_step = initial_state.get("current_step", "started")
        
        # 如果当前已经达到停止步骤，直接返回
        if stop_at and current_step == stop_at:
            return initial_state
            
        # 只生成标题
        if current_step == "started":
            result = await generate_title_node(initial_state)
            initial_state.update(result)
            
            # 如果设置了在生成标题后停止，则返回
            if stop_at == "title_generated":
                return initial_state
        
        # 只生成大纲
        if current_step in ["started", "title_generated"] and initial_state.get("title"):
            if current_step == "title_generated" or initial_state.get("current_step") == "title_generated":
                outline_result = await generate_outline_node(initial_state)
                initial_state.update(outline_result)
                
                # 如果设置了在生成大纲后停止，则返回
                if stop_at == "outline_generated":
                    return initial_state
        
        # 只生成内容
        if current_step in ["started", "title_generated", "outline_generated"] and initial_state.get("outline"):
            if current_step == "outline_generated" or initial_state.get("current_step") == "outline_generated":
                content_result = await generate_content_node(initial_state)
                initial_state.update(content_result)
                
                # 如果设置了在生成内容后停止，则返回
                if stop_at == "content_generated":
                    return initial_state
        
        # 如果未设置停止点，或者当前状态不符合分步执行的条件，执行完整工作流
        if not stop_at and (current_step == "started" or not initial_state.get("content")):
            result = await workflow.ainvoke(initial_state)
            initial_state = result
        
        # 记录工作流完成
        print(f"文档生成工作流完成: {initial_state.get('current_step')}")
        
        return initial_state
        
    except Exception as e:
        # 记录错误
        print(f"工作流执行错误: {e}")
        traceback.print_exc()
        
        # 更新状态
        initial_state["error_message"] = str(e)
        initial_state["current_step"] = "workflow_failed"
        
        return initial_state 