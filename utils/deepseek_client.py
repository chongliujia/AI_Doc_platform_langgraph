import os
import json
import asyncio
import httpx
from typing import Dict, Any, Optional, List, Union
import time
import random
from dotenv import load_dotenv
import requests
import logging

# 加载环境变量
load_dotenv()

# 添加langchain相关导入
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            print("警告: 未找到DEEPSEEK_API_KEY环境变量")
        
        self.base_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.max_retries = int(os.getenv("API_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("API_RETRY_DELAY", "2.0"))
        
        # 客户端配置
        self.timeout = float(os.getenv("API_TIMEOUT", "60.0"))
        self.client_params = {
            "timeout": httpx.Timeout(self.timeout),
            "follow_redirects": True
        }
    
    async def generate_content(self, prompt: str, max_tokens: int = 2000) -> str:
        """生成内容
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成token数量
            
        Returns:
            生成的文本内容
        """
        if not self.api_key:
            print("无API密钥，使用离线备用生成器")
            return self._offline_generate(prompt)
            
        # 准备API请求数据
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一位专业的写作助手，擅长生成专业、清晰、连贯的内容。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.5
        }
        
        # 尝试调用API，带有重试机制
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, json=data, headers=headers, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return content
                    else:
                        print(f"API请求失败，状态码: {response.status_code}, 响应: {response.text}")
                        
                        # 检查是否需要重试
                        if response.status_code in [429, 500, 502, 503, 504] and attempt < self.max_retries - 1:
                            # 指数退避重试
                            retry_delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                            print(f"将在 {retry_delay:.2f} 秒后重试 ({attempt+1}/{self.max_retries})")
                            await asyncio.sleep(retry_delay)
                            continue
                        
                        # 如果重试次数用尽或不需要重试，使用离线生成
                        print("API请求失败，使用离线备用生成器")
                        return self._offline_generate(prompt)
                
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                print(f"网络错误 ({type(e).__name__}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # 指数退避重试
                    retry_delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"将在 {retry_delay:.2f} 秒后重试 ({attempt+1}/{self.max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"网络连接失败，重试次数已用尽，使用离线备用生成器")
                    return self._offline_generate(prompt)
                    
            except Exception as e:
                print(f"API调用时发生未知错误: {str(e)}")
                return self._offline_generate(prompt)
                
        # 如果所有重试都失败
        return self._offline_generate(prompt)
    
    def _offline_generate(self, prompt: str) -> str:
        """离线内容生成器（当API不可用时的备用方案）
        
        Args:
            prompt: 提示词
            
        Returns:
            基于提示词生成的基本内容
        """
        print("使用离线生成器创建基本内容")
        
        # 提取关键信息
        prompt_lines = prompt.strip().split('\n')
        
        # 尝试提取文档标题、章节等信息
        document_title = ""
        document_topic = ""
        section_title = ""
        points = []
        
        for line in prompt_lines:
            line = line.strip()
            if "文档标题:" in line:
                document_title = line.split("文档标题:")[1].strip()
            elif "文档主题:" in line:
                document_topic = line.split("文档主题:")[1].strip()
            elif "章节标题:" in line:
                section_title = line.split("章节标题:")[1].strip()
            elif line.startswith("- "):
                points.append(line[2:])
        
        if not section_title:
            section_title = "主题概述"
            
        # 生成基本内容
        content = f"{section_title}\n\n"
        
        # 为每个要点生成一个段落
        for point in points:
            content += f"{point}是{document_topic or '本主题'}的重要组成部分。"
            content += f"在{document_title or '本文档'}中，我们将详细探讨这一方面的内容。"
            content += f"通过理解{point}，我们能够更全面地把握{document_topic or '这一领域'}的核心要素。\n\n"
        
        # 如果没有要点，生成通用内容
        if not points:
            content += f"本章节将详细介绍{document_topic or '相关主题'}的{section_title}。"
            content += f"作为{document_title or '本文档'}的重要组成部分，"
            content += f"{section_title}对于理解整体内容至关重要。\n\n"
            content += f"我们将从多个角度分析{document_topic or '本主题'}的关键特点，"
            content += f"探讨其在实际应用中的意义和价值。\n\n"
            content += f"通过全面系统的分析，读者将能够更深入地理解{document_topic or '相关领域'}的核心概念和重要性。"
        
        # 添加结束段落
        content += f"\n总之，{section_title}是{document_topic or '本主题'}中不可或缺的一部分，"
        content += f"对于全面理解{document_title or '整体内容'}具有重要的指导意义。"
        
        return content

# 添加基于LangChain的AI接口类
class LangChainClient:
    """基于LangChain的AI接口，可以替代DeepSeekClient"""
    
    def __init__(self):
        # 获取必要的环境变量
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model_name = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
        # 记录是否使用有效的API密钥
        self.has_valid_key = bool(self.api_key)
        
        if not self.has_valid_key:
            logger.warning("未设置OPENAI_API_KEY环境变量，API调用将失败")
        
        # 创建LangChain LLM客户端
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.7,
            api_key=self.api_key
        )
        
        logger.info(f"LangChain客户端初始化，使用模型: {self.model_name}")
    
    async def generate_content(self, prompt: str) -> str:
        """使用LangChain生成文本内容"""
        try:
            if not self.has_valid_key:
                return "API密钥未配置，无法调用LLM API"
            
            # 创建消息
            messages = [HumanMessage(content=prompt)]
            
            # 调用LLM
            response = await self.llm.ainvoke(messages)
            
            # 提取生成的文本
            return response.content
            
        except Exception as e:
            logger.error(f"LangChain API调用失败: {e}")
            raise Exception(f"LangChain API调用失败: {e}")
    
    async def generate_with_history(self, messages: List[Dict[str, str]]) -> str:
        """使用LangChain生成带有对话历史的文本内容"""
        try:
            if not self.has_valid_key:
                return "API密钥未配置，无法调用LLM API"
            
            # 转换消息格式为LangChain格式
            langchain_messages: List[BaseMessage] = []
            for msg in messages:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            # 调用LLM
            response = await self.llm.ainvoke(langchain_messages)
            
            # 提取生成的文本
            return response.content
            
        except Exception as e:
            logger.error(f"LangChain API带历史记录调用失败: {e}")
            raise Exception(f"LangChain API带历史记录调用失败: {e}")
    
    async def get_structured_output(self, prompt: str, output_schema: Dict[str, Any]) -> Dict[str, Any]:
        """使用LangChain生成结构化JSON输出"""
        try:
            from langchain_core.output_parsers import JsonOutputParser
            from langchain_core.prompts import ChatPromptTemplate
            
            # 创建解析器
            parser = JsonOutputParser(pydantic_object=output_schema)
            
            # 创建提示模板
            template = ChatPromptTemplate.from_messages([
                ("human", "{input}\n\n请以JSON格式输出，遵循以下结构:\n{format_instructions}")
            ])
            
            # 创建链
            chain = template | self.llm | parser
            
            # 调用链
            result = await chain.ainvoke({
                "input": prompt,
                "format_instructions": parser.get_format_instructions()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"LangChain结构化输出调用失败: {e}")
            raise Exception(f"LangChain结构化输出调用失败: {e}") 