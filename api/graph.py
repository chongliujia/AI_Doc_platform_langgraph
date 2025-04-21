from typing import TypedDict, List, Dict, Any, Optional
from utils.deepseek_client import DeepSeekClient
import json
import traceback
import re

deepseek_client = DeepSeekClient()

# 定义状态类型
class DocumentState(TypedDict):
    # 用户输入
    topic: str
    page_limit: int
    document_type: str  # "ppt" 或 "word"
    
    # 流程状态
    current_step: str
    error_message: Optional[str]
    
    # 生成内容
    title: Optional[str]
    outline: Optional[List[Dict[str, Any]]]
    content: Optional[Dict[str, str]]  # 存储每个章节的详细内容
    user_edited_outline: Optional[bool]
    user_edited_title: Optional[bool]

# 生成默认大纲
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

# 1. 标题智能体
async def generate_title(topic: str, document_type: str):
    """根据主题生成标题"""
    try:
        print(f"标题智能体：正在为主题'{topic}'生成标题...")
        
        # 构建生成标题的提示
        prompt = f"""
        请为以下主题生成一个简洁、吸引人且专业的{document_type.upper()}文档标题:
        
        主题: {topic}
        
        要求:
        1. 标题应该简洁明了，不超过20个字
        2. 标题应该能准确反映主题的核心内容
        3. 标题应该吸引读者的兴趣
        4. 只需要返回标题文本，不需要其他说明
        """
        
        try:
            # 调用DeepSeek API生成标题
            title_response = await deepseek_client.generate_content(prompt)
            
            # 清理响应（去除多余空格、引号等）
            title = title_response.strip().strip('"').strip("'").strip()
            
            if not title:
                # 如果标题为空，使用默认标题
                title = f"{topic}研究分析"
                
            print(f"生成的标题: {title}")
            return {
                "success": True,
                "title": title,
                "error": None
            }
        
        except Exception as e:
            print(f"生成标题时出错: {e}")
            # 使用默认标题
            default_title = f"{topic}研究分析"
            return {
                "success": True,
                "title": default_title,
                "error": f"API调用失败: {str(e)}"
            }
    
    except Exception as e:
        print(f"标题智能体执行出错: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        
        # 使用主题作为默认标题
        return {
            "success": False,
            "title": f"{topic}研究分析",
            "error": f"生成标题时出错: {str(e)}"
        }

# 2. 大纲智能体
async def generate_outline(topic: str, title: str, page_limit: int, document_type: str):
    """根据标题和页数限制生成大纲"""
    try:
        print(f"大纲智能体：正在为标题'{title}'生成大纲，页数限制: {page_limit}...")
        
        # 构建提示，针对主题进行定制
        topic_specific_prompts = {}
        
        # 为常见主题添加专业化提示
        topic_lower = topic.lower()
        if "强化学习" in topic or "reinforcement learning" in topic_lower:
            topic_specific = """
            请确保大纲涵盖强化学习的以下关键方面:
            1. 强化学习的基本概念和理论基础（如MDP、奖励机制等）
            2. 经典算法（如Q-learning、SARSA、策略梯度方法等）
            3. 深度强化学习方法（如DQN、A3C、PPO等）
            4. 实际应用案例（如游戏、机器人控制、推荐系统等）
            5. 当前研究热点和挑战
            """
        elif "机器学习" in topic or "machine learning" in topic_lower:
            topic_specific = """
            请确保大纲涵盖机器学习的以下关键方面:
            1. 监督学习、无监督学习和半监督学习的基本概念
            2. 经典算法（如回归、决策树、SVM、聚类等）
            3. 神经网络和深度学习基础
            4. 实际应用场景和案例分析
            5. 模型评估方法和最佳实践
            """
        elif "深度学习" in topic or "deep learning" in topic_lower:
            topic_specific = """
            请确保大纲涵盖深度学习的以下关键方面:
            1. 神经网络基础（感知器、激活函数、反向传播等）
            2. 主要网络架构（CNN、RNN、LSTM、Transformer等）
            3. 训练技巧与优化方法（正则化、批量归一化等）
            4. 前沿应用（计算机视觉、NLP、生成模型等）
            5. 行业实践和部署考虑
            """
        elif "自然语言处理" in topic or "nlp" in topic_lower or "natural language processing" in topic_lower:
            topic_specific = """
            请确保大纲涵盖自然语言处理的以下关键方面:
            1. 文本预处理和表示方法（词袋、词嵌入等）
            2. 语言模型（n-gram、神经网络语言模型等）
            3. 序列标注和分类任务（命名实体识别、情感分析等）
            4. 机器翻译和文本生成
            5. 大型语言模型及其应用
            """
        elif "计算机视觉" in topic or "computer vision" in topic_lower:
            topic_specific = """
            请确保大纲涵盖计算机视觉的以下关键方面:
            1. 图像处理基础（滤波、边缘检测等）
            2. 传统视觉算法（SIFT、HOG等特征提取方法）
            3. 深度学习视觉模型（CNN、R-CNN系列、Transformer等）
            4. 视觉任务（图像分类、目标检测、分割、跟踪等）
            5. 计算机视觉的应用场景
            """
        elif "数据分析" in topic or "data analysis" in topic_lower:
            topic_specific = """
            请确保大纲涵盖数据分析的以下关键方面:
            1. 数据获取和预处理技术
            2. 探索性数据分析方法
            3. 统计分析与假设检验
            4. 数据可视化技术
            5. 商业智能与决策支持
            """
        else:
            topic_specific = f"""
            请为{topic}主题创建专业、详细的大纲，确保内容全面且深入，避免使用通用的占位符（如"关键点1"），
            而是使用与主题相关的具体专业术语和概念。确保大纲紧密围绕标题"{title}"展开，
            并且每个章节都有3-5个具体的内容要点。
            """
        
        # 根据页数限制和文档类型，确定合适的章节数
        if document_type.lower() == "ppt":
            # PPT通常需要更精简的章节结构
            if page_limit <= 5:
                target_sections = 2  # 非常精简
                section_guide = "由于页数限制非常小，只创建2个核心章节，每个章节2-3个要点"
            elif page_limit <= 10:
                target_sections = 3  # 精简
                section_guide = "由于页数限制较小，创建3个章节，每个章节3-4个要点"
            elif page_limit <= 15:
                target_sections = 4  # 标准
                section_guide = "创建4个关键章节，每个章节3-5个要点"
            else:
                target_sections = 5  # 详细
                section_guide = "可以创建5个详细章节，每个章节4-5个要点"
        else:  # Word文档
            # Word文档可以包含更多内容
            if page_limit <= 3:
                target_sections = 2  # 非常精简
                section_guide = "由于页数限制非常小，只创建2个核心章节"
            elif page_limit <= 7:
                target_sections = 3  # 精简
                section_guide = "由于页数限制较小，创建3个章节"
            elif page_limit <= 12:
                target_sections = 4  # 标准
                section_guide = "创建4个关键章节"
            else:
                target_sections = 5  # 详细
                section_guide = "可以创建5个或更多详细章节"
        
        # 构建最终提示，强化页数限制的说明
        prompt = f"""
        请为以下标题生成一个{document_type.upper()}文档的详细大纲，页数限制为{page_limit}页:
        
        标题: {title}
        主题: {topic}
        
        {topic_specific}
        
        大纲结构要求:
        1. 标题页和目录页将占用2页
        2. 根据{page_limit}页的限制，应该生成约{target_sections}个章节
        3. {section_guide}
        4. 每个章节标题必须与"{title}"和"{topic}"紧密相关
        5. 章节标题应该简洁明了，反映该部分的核心内容
        6. 章节要点应该具体、专业，不要使用通用占位符
        
        请按照以下JSON格式返回结果:
        {{
            "outline": [
                {{
                    "title": "章节标题1",
                    "content": ["具体要点1", "具体要点2", "具体要点3"]
                }},
                {{
                    "title": "章节标题2",
                    "content": ["具体要点1", "具体要点2", "具体要点3"]
                }}
            ],
            "estimated_pages": 总页数估计(包括标题页和目录页)
        }}
        
        重要提示:
        1. 大纲章节数必须与上述要求一致，约为{target_sections}个章节
        2. 章节标题和内容要点必须使用专业术语，不要使用通用标题
        3. 章节内容必须紧密围绕主题"{topic}"和标题"{title}"
        4. 请仅返回JSON格式，不要有其他文本
        """
        
        try:
            print("调用DeepSeek API生成大纲...")
            response = await deepseek_client.generate_content(prompt)
            
            # 清理响应数据，确保它是有效的JSON
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # 解析JSON响应
            try:
                result = json.loads(cleaned_response)
                
                # 检查是否有outline字段
                if "outline" not in result or not result["outline"]:
                    print("API返回的JSON数据结构不完整或为空，使用默认数据")
                    default_data = generate_default_outline(topic, page_limit)
                    outline = default_data["outline"]
                else:
                    outline = result["outline"]
                    
                    # 验证大纲的质量
                    for section in outline:
                        # 检查标题是否为空
                        if not section.get("title") or section.get("title") == "章节标题":
                            section["title"] = f"{topic}分析"
                            
                        # 检查内容是否为空或通用
                        if not section.get("content") or len(section.get("content", [])) == 0:
                            section["content"] = ["背景介绍", "关键概念", "应用场景"]
                        else:
                            # 检查内容点是否为通用占位符
                            content = section.get("content", [])
                            for i, point in enumerate(content):
                                if point in ["具体要点1", "具体要点2", "具体要点3", "关键点1", "要点1"]:
                                    content[i] = f"{section['title']}的重要方面"
                                    
                # 验证页数是否符合限制
                estimated_pages = result.get("estimated_pages", 2 + len(outline))  # 默认是标题页+目录页+章节数
                
                # 如果预计页数超出限制，调整大纲
                if estimated_pages > page_limit:
                    print(f"警告：估计页数({estimated_pages})超过了限制({page_limit})，调整大纲结构")
                    # 保留前面的章节，确保不超过页数限制
                    max_sections = max(2, page_limit - 2)  # 至少保留2个章节
                    if len(outline) > max_sections:
                        outline = outline[:max_sections]
                        print(f"调整后的章节数：{len(outline)}")
                
                return {
                    "success": True,
                    "outline": outline,
                    "estimated_pages": min(estimated_pages, page_limit),
                    "error": None
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"解析JSON失败: {e}")
                # 使用默认大纲
                default_data = generate_default_outline(topic, page_limit)
                return {
                    "success": True,
                    "outline": default_data["outline"],
                    "estimated_pages": default_data.get("estimated_pages", 2 + len(default_data["outline"])),
                    "error": f"解析响应失败: {str(e)}"
                }
                
        except Exception as api_error:
            print(f"API调用失败: {api_error}")
            # 使用默认大纲
            default_data = generate_default_outline(topic, page_limit)
            return {
                "success": True,
                "outline": default_data["outline"],
                "estimated_pages": default_data.get("estimated_pages", 2 + len(default_data["outline"])),
                "error": f"API调用失败: {str(api_error)}"
            }
            
    except Exception as e:
        print(f"大纲智能体执行出错: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        
        try:
            # 使用默认大纲
            default_data = generate_default_outline(topic, page_limit)
            
            return {
                "success": False,
                "outline": default_data["outline"],
                "estimated_pages": default_data.get("estimated_pages", 2 + len(default_data["outline"])),
                "error": f"大纲生成过程中出错: {str(e)}"
            }
        except:
            # 如果连默认数据都无法生成，则返回错误
            return {
                "success": False,
                "outline": [],
                "estimated_pages": 2,  # 最少有标题页和目录页
                "error": f"大纲生成过程中严重错误: {str(e)}"
            }

# 3. 内容智能体
async def generate_content(title: str, topic: str, outline: List[Dict[str, Any]], document_type: str = "ppt", page_limit: int = None):
    """根据标题和大纲生成每个章节的详细内容"""
    try:
        print(f"内容智能体：正在为'{title}'生成详细内容...")
        
        # 为每个章节生成内容
        content_dict = {}
        success_count = 0
        error_count = 0
        
        # 构建领域特定提示
        domain_specific_prompt = ""
        if "量化" in topic or "quant" in topic.lower() or "投资" in topic:
            domain_specific_prompt = """
            请确保内容中包含以下要素：
            1. 提及常见的量化投资策略（如动量策略、均值回归、统计套利等）
            2. 使用专业术语（如Alpha、Beta、夏普比率、最大回撤等）
            3. 讨论数据处理和回测的重要性
            4. 引用真实的市场数据示例进行说明
            5. 分析策略的优势、劣势和适用市场环境
            """
        elif "机器学习" in topic or "machine learning" in topic.lower():
            domain_specific_prompt = """
            请确保内容中包含以下要素：
            1. 使用机器学习专业术语（如特征工程、过拟合、交叉验证等）
            2. 提及相关算法的数学原理和实现方法
            3. 讨论模型评估方法和指标
            4. 说明如何选择合适的算法和参数
            5. 包含实际应用案例或示例
            """
        elif "深度学习" in topic or "deep learning" in topic.lower():
            domain_specific_prompt = """
            请确保内容中包含以下要素：
            1. 使用深度学习专业术语（如反向传播、梯度下降、激活函数等）
            2. 描述常见的神经网络架构及其适用场景
            3. 讨论优化技术和训练策略
            4. 解释深度学习模型的优势和局限性
            5. 包含实际应用案例或最新研究进展
            """
        elif "自然语言处理" in topic or "nlp" in topic.lower():
            domain_specific_prompt = """
            请确保内容中包含以下要素：
            1. 使用NLP专业术语（如词向量、注意力机制、transformer等）
            2. 描述文本处理的关键步骤和技术
            3. 讨论语言模型的发展和应用
            4. 解释NLP任务的评估方法和挑战
            5. 包含具体的应用场景和案例
            """
        
        # 计算页数限制相关指南
        page_limit_guide = ""
        if document_type.lower() == "ppt" and page_limit:
            # 计算大致可用页数
            available_pages = max(3, page_limit - 3)  # 减去标题页、目录页和结束页
            
            # 计算每个章节平均可用页数
            pages_per_section = max(1, available_pages // len(outline))
            
            # 根据页数提供不同的长度指南
            if pages_per_section <= 1:
                content_length = "非常简短"
                paragraphs_guide = "每个章节最多生成1-2个段落"
            elif pages_per_section <= 2:
                content_length = "简短"
                paragraphs_guide = "每个章节生成2-3个段落"
            elif pages_per_section <= 3:
                content_length = "中等"
                paragraphs_guide = "每个章节生成3-4个段落"
            else:
                content_length = "详细"
                paragraphs_guide = "每个章节可以生成4-6个段落"
                
            page_limit_guide = f"""
            内容长度指南（重要）：
            1. 由于PPT页数限制为{page_limit}页，每个章节的内容应当是【{content_length}】的
            2. {paragraphs_guide}
            3. 每个段落应该包含3-5句话
            4. 段落之间用空行分隔，便于PPT排版
            5. 每页PPT最多容纳200-300字，请相应调整内容长度
            """
        elif document_type.lower() == "word" and page_limit:
            # Word文档每页约500字，标题页和目录约占2页
            available_pages = max(1, page_limit - 2)
            words_per_section = available_pages * 500 // len(outline)
            
            page_limit_guide = f"""
            内容长度指南（重要）：
            1. 由于Word文档页数限制为{page_limit}页，请控制每个章节的内容长度
            2. 每个章节的内容应当控制在约{words_per_section}字左右
            3. 确保覆盖所有要点，但要避免冗余
            """
        
        # 首先为所有章节创建默认内容，确保每个章节都有内容
        for section in outline:
            section_title = section["title"]
            section_points = section["content"]
            
            # 创建默认内容，基于大纲要点
            default_content = f"本章节主要介绍{section_title}的核心内容。\n\n"
            for point in section_points:
                default_content += f"- {point}：此部分将详细阐述相关内容。\n"
            
            # 初始设置默认内容
            content_dict[section_title] = default_content
        
        # 为每个章节尝试生成更详细的内容
        for section in outline:
            section_title = section["title"]
            section_points = section["content"]
            
            try:
                # 构建提示
                points_text = "\n".join([f"- {point}" for point in section_points])
                
                # 生成特定章节针对性提示
                section_specific_guide = f"""
                本章节'{section_title}'是关于'{title}'和'{topic}'的重要组成部分。
                请确保内容紧密围绕章节标题'{section_title}'和以下具体要点展开，不要偏离主题：
                {points_text}
                
                每个要点都应得到充分解释，并且内容必须与总主题'{title}'保持一致。
                """
                
                # 为PPT和Word设置不同的内容要求
                if document_type.lower() == "ppt":
                    # PPT的内容要求更加简洁
                    MIN_CONTENT_LENGTH = 300  # 提高PPT内容最低要求到300字符
                    content_format_guide = """
                    PPT特定格式要求:
                    1. 内容精炼，适合双栏布局展示
                    2. 使用要点式表达，每行可包含50-60个字符
                    3. 每个要点用完整的句子表达关键信息
                    4. 使用破折号(-)或短横线开始每个要点
                    5. 重要概念使用单独的行展示
                    6. 段落之间用空行分隔，改善PPT排版
                    7. 内容可以较为详细，但避免过于冗长的句子
                    """
                else:
                    # Word文档内容要求更加详细
                    MIN_CONTENT_LENGTH = 600  # Word内容最低要求600字符
                    content_format_guide = """
                    Word文档格式要求:
                    1. 内容应详细、全面，使用完整段落
                    2. 每个要点展开为2-3个段落
                    3. 可以使用小标题来区分不同部分
                    4. 段落之间用空行分隔，便于排版
                    """
                
                prompt = f"""
                请为以下文档章节生成专业的内容，适用于{document_type.upper()}:
                
                文档标题: {title}
                文档主题: {topic}
                章节标题: {section_title}
                
                章节要点:
                {points_text}
                
                {section_specific_guide}
                
                {domain_specific_prompt}
                
                {page_limit_guide}
                
                {content_format_guide}
                
                内容要求:
                1. 内容必须高度相关，准确解释章节标题"{section_title}"下的每个要点
                2. 必须使用专业、清晰的语言，引用相关概念和术语
                3. 内容应该连贯、有逻辑性，避免重复
                4. 确保内容具有教育价值和信息量
                5. 生成至少{MIN_CONTENT_LENGTH}字符的内容
                6. 不要添加额外的引言或总结，直接开始核心内容
                
                请直接返回生成的内容，不要包含额外的说明或标记。
                """
                
                # 调用DeepSeek API生成内容
                print(f"正在生成'{section_title}'的内容...")
                section_content = await deepseek_client.generate_content(prompt)
                content = section_content.strip()
                
                # 验证内容
                # 如果内容过短，尝试一次重新生成
                if len(content) < MIN_CONTENT_LENGTH:
                    print(f"警告: 章节'{section_title}'内容过短({len(content)}字符)，尝试重新生成")
                    
                    # 增强提示以生成更符合要求的内容
                    if document_type.lower() == "ppt":
                        # PPT重试提示
                        retry_format_guide = """
                        PPT内容格式要求(非常重要):
                        1. 使用双栏布局格式，每行短句
                        2. 每个要点必须简短，最多30-35个字符
                        3. 使用破折号(-)开始每个新要点
                        4. A:B格式表达概念和定义
                        5. 将长句拆分成多个短点
                        6. 重要术语独立成行加粗显示
                        7. 每个要点仅使用1行文本表达
                        8. 使用空行分隔不同要点
                        9. 避免完整段落，使用要点列表
                        """
                    else:
                        # Word重试提示
                        retry_format_guide = """
                        Word内容格式要求(非常重要):
                        1. 使用完整的段落和句子
                        2. 详细解释每个要点
                        3. 使用小标题区分不同部分
                        4. 包含适当的举例和应用场景
                        """
                    
                    retry_prompt = f"""
                    您之前生成的内容长度不足，请重新生成该部分。
                    
                    文档标题: {title}
                    文档主题: {topic}
                    章节标题: {section_title}
                    
                    章节要点:
                    {points_text}
                    
                    {domain_specific_prompt}
                    
                    注意：
                    1. 内容必须详尽具体，至少 {MIN_CONTENT_LENGTH} 字符
                    2. 保持专业性和准确性
                    3. {content_format_guide if document_type.lower() == "ppt" else ""}
                    4. 避免重复已有内容
                    5. 内容应完整覆盖该部分主题
                    
                    请重新生成更丰富、更专业的内容：
                    """
                    
                    try:
                        retry_content = await deepseek_client.generate_content(retry_prompt)
                        retry_content = retry_content.strip()
                        
                        # 只有当重试内容明显更好时，才替换原内容
                        if len(retry_content) >= MIN_CONTENT_LENGTH and len(retry_content) > len(content) * 1.2:
                            print(f"重新生成的内容更好({len(retry_content)}字符)，使用新内容")
                            content = retry_content
                        else:
                            print(f"重新生成的内容未明显改善，保留原内容")
                    except Exception as retry_error:
                        print(f"重试生成内容时出错: {retry_error}")
                
                # 内容后处理：格式优化
                if document_type.lower() == "ppt":
                    # PPT格式优化：确保行长适中，避免过长行
                    formatted_lines = []
                    lines = content.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            formatted_lines.append("")  # 保留空行
                            continue
                            
                        # 处理过长的行
                        if len(line) > 60:  # 降低长度限制为60个字符
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
                    
                    # 重组内容
                    content = '\n'.join(formatted_lines)
                
                # 保存有效内容
                if len(content) >= MIN_CONTENT_LENGTH * 0.5:  # 允许内容量为最低要求的一半
                    content_dict[section_title] = content
                    print(f"成功生成章节'{section_title}'的内容 ({len(content)}字符)")
                    success_count += 1
                else:
                    print(f"警告: 章节'{section_title}'内容生成未达标({len(content)}字符)，使用默认内容")
                    # 默认内容已在之前设置，不需要再次设置
                
            except Exception as section_error:
                print(f"生成章节'{section_title}'内容时出错: {section_error}")
                # 不需要做任何事情，因为默认内容已存在
                error_count += 1
        
        overall_success = error_count == 0
        partial_success = success_count > 0
        
        if overall_success:
            status_message = "所有章节内容生成成功"
        elif partial_success:
            status_message = f"部分章节生成成功 ({success_count}/{len(outline)})"
        else:
            status_message = "所有章节内容生成失败，使用默认内容"
            
        # 确保content_dict的键与outline中的章节标题完全一致
        for section in outline:
            section_title = section["title"]
            if section_title not in content_dict:
                # 如果章节标题没有对应内容，创建默认内容
                section_points = section["content"]
                default_content = f"本章节主要介绍{section_title}的核心内容。\n\n"
                for point in section_points:
                    default_content += f"- {point}：此部分将详细阐述相关内容。\n"
                content_dict[section_title] = default_content
                print(f"为章节'{section_title}'创建默认内容")
            
        return {
            "success": overall_success,
            "partial_success": partial_success,
            "content": content_dict,
            "status": status_message,
            "error": None if overall_success else "部分章节内容生成失败，已使用默认内容替代"
        }
        
    except Exception as e:
        print(f"内容智能体执行出错: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        
        # 创建所有章节的默认内容
        content_dict = {}
        for section in outline:
            section_title = section["title"]
            section_points = section["content"]
            default_content = f"本章节主要介绍{section_title}的核心内容。\n\n"
            for point in section_points:
                default_content += f"- {point}：此部分将详细阐述相关内容。\n"
            content_dict[section_title] = default_content
        
        return {
            "success": False,
            "partial_success": True,  # 虽然生成失败，但提供了默认内容
            "content": content_dict,
            "status": "内容生成过程中发生错误，使用默认内容替代",
            "error": f"生成内容时出错: {str(e)}"
        } 