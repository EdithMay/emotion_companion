# backend/app/agents/companion_agent.py

import re
import json
from datetime import date, timedelta
from sqlalchemy.orm import Session

from ..services.llm_service import get_llm
from ..services.memory_service import (
    save_message,
    get_recent_messages,
    get_latest_summary,
    check_and_compress
)
from ..services.image_service import save_message_image
from ..services.rag_service import get_rag_service
from ..models.db_models import MoodEntry, PersonaConfig, Conversation
from ..models.schemas import MessageOut, ChatResponse

# ═══════════════════════════════════════════════════════════════
# 工具描述：注入 system prompt，让 Agent 知道有这个能力
# ═══════════════════════════════════════════════════════════════
MEMORY_TOOL_DESC = """
你拥有一个记忆检索工具，可以在真正需要时主动调用：

工具名：search_memory
用途：检索用户过往的对话记录和心情日记中与当前话题相关的内容
调用格式（必须严格遵守，包括方括号和冒号）：
  [TOOL_CALL:search_memory:query=你要检索的关键词或短语]

【调用判断标准】
应该调用的情况：
  · 用户明确说"我之前说过""你还记得吗""上次那件事"
  · 用户提到一个具体的人、事件，你感觉之前听过但不确定细节
  · 用户的情绪让你想起了他之前分享过的类似经历，需要确认

不应该调用的情况：
  · 日常寒暄、今天天气、随口抱怨等轻量话题
  · 用户在分享当下发生的新事情，并不涉及历史
  · 上一轮刚刚检索过，不要重复检索
  · 你对当前话题已经有足够的上下文来回复

【使用原则】
  · 每轮对话最多调用一次
  · 拿到结果后，记忆只是背景参考，自然融入回复即可
  · 不要逐条复述检索结果，也不要每次都说"我记得你之前..."
  · 如果检索结果与当前话题关联不强，忽略它，直接回复
"""


# ═══════════════════════════════════════════════════════════════
# CompanionAgent
# ═══════════════════════════════════════════════════════════════

class CompanionAgent:
    """
    情绪陪伴 Agent。

    记忆调用策略：
      Agent 自主决定是否调用 search_memory 工具，
      而非系统强制注入 RAG 结果。
      每次对话最多执行一轮工具调用。

    对话流程：
      1. 保存用户消息
      2. 检查记忆压缩
      3. 构建 Prompt（人设 + 工具描述 + 中期摘要 + 近期消息）
      4. 第一次 LLM 调用
      5. 检测是否包含工具调用指令
         ├── 是 → 执行 RAG 检索 → 第二次 LLM 调用（流式输出）
         └── 否 → 直接流式输出第一次回复
      6. 保存 Agent 回复，更新 RAG 索引
    """

    def __init__(self):
        self.llm = get_llm()
        self.rag = get_rag_service()
        print("✅ CompanionAgent 初始化成功（工具调用模式）")

    # ──────────────────────────────────────────────────────────
    # 流式对话主入口
    # ──────────────────────────────────────────────────────────

    def stream_chat(
        self,
        db: Session,
        conversation_id: int,
        user_content: str,
        image_data_url: str | None = None,
    ):
        """
        流式对话，使用 Generator yield SSE 格式数据。

        SSE 数据格式：
          data: [START]                          —— 开始信号
          data: [USER_MSG]{id, created_at}       —— 用户消息元信息
          data: [TOOL_USING]                     —— Agent 正在检索记忆（前端可显示提示）
          data: "<token>"                        —— 普通文本 token（JSON 字符串）
          data: [DONE]{id, created_at}           —— 结束信号，含 agent 消息元信息
          data: [ERROR]<msg>                     —— 错误信号
        """
        yield "data: [START]\n\n"

        # ── 步骤 1：保存用户消息 ─────────────────────────────
        try:
            stored_user_content = self._stored_user_content(user_content, image_data_url)
            user_msg = save_message(db, conversation_id, "user", stored_user_content)
            image_record = self._save_image_if_present(db, conversation_id, user_msg.id, image_data_url)
        except Exception as e:
            yield f"data: [ERROR]保存消息失败: {e}\n\n"
            return

        user_meta = {'id': user_msg.id, 'created_at': str(user_msg.created_at)}
        if image_record:
            user_meta["image_url"] = image_record.public_url
            user_meta["image_created_at"] = str(image_record.created_at)
        yield f"data: [USER_MSG]{json.dumps(user_meta, ensure_ascii=False)}\n\n"

        # ── 步骤 2：检查记忆压缩 ─────────────────────────────
        try:
            compressed = check_and_compress(db, conversation_id)
            if compressed:
                summary_text = get_latest_summary(db, conversation_id)
                if summary_text:
                    self.rag.index(
                        text=summary_text,
                        metadata={
                            "type":            "memory_summary",
                            "date":            date.today().strftime("%Y-%m-%d"),
                            "conversation_id": str(conversation_id)
                        }
                    )
        except Exception as e:
            print(f"  ⚠️  记忆压缩失败（不影响对话）: {e}")

        # ── 步骤 3：构建 Prompt ──────────────────────────────
        messages = self._build_prompt(db, conversation_id, user_content, image_data_url)

        # ── 步骤 4：第一次 LLM 调用（非流式，检测工具调用）──
        print(f"\n💬 [会话{conversation_id}] 第一次 LLM 调用，检测工具意图...")
        first_response = self._invoke_llm_sync(messages)
        print(f"   第一次响应（前100字）: {first_response[:100]}")

        # ── 步骤 5：解析工具调用 ─────────────────────────────
        tool_query = self._parse_tool_call(first_response)
        full_reply = ""

        if tool_query is not None:
            # ── 分支 A：Agent 主动调用了 search_memory ────────
            print(f"  🔧 Agent 主动调用 search_memory，query: {tool_query}")
            yield "data: [TOOL_USING]\n\n"

            tool_result = self._execute_search_memory(tool_query)
            print(f"  📚 检索结果: {tool_result[:80] if tool_result else '无结果'}")

            # 把工具结果追加到消息列表，发起第二次 LLM 调用（流式）
            messages.append({"role": "assistant", "content": first_response})
            messages.append({
                "role": "user",
                "content": (
                    f"[工具返回结果]\n{tool_result}\n\n"
                    "请基于以上记忆背景，结合用户刚才说的话，给出你的回复。\n"
                    "要求：\n"
                    "· 记忆只是背景参考，不要逐条复述\n"
                    "· 回复要自然、温暖，像一个真正认识用户的朋友\n"
                    "· 如果检索结果与当前话题关联不强，可以忽略它"
                )
            })

            print(f"  🚀 第二次 LLM 调用（流式输出）...")
            for event in self._stream_llm(messages):
                if event.startswith("__FULL__"):
                    full_reply = event[8:]
                else:
                    yield event

        else:
            # ── 分支 B：Agent 不需要工具，直接输出回复 ────────
            print(f"  ✅ Agent 无需调用工具，直接输出回复")
            for event in self._stream_text(first_response):
                if event.startswith("__FULL__"):
                    full_reply = event[8:]
                else:
                    yield event

        # ── 步骤 6：保存 Agent 回复 ──────────────────────────
        if full_reply.strip():
            try:
                agent_msg = save_message(db, conversation_id, "assistant", full_reply)

                # 有实质内容的用户消息写入 RAG
                if self._is_meaningful(user_content):
                    self.rag.index(
                        text=user_content,
                        metadata={
                            "type":            "user_message",
                            "date":            date.today().strftime("%Y-%m-%d"),
                            "conversation_id": str(conversation_id)
                        }
                    )

                yield (
                    f"data: [DONE]"
                    f"{json.dumps({'id': agent_msg.id, 'created_at': str(agent_msg.created_at)}, ensure_ascii=False)}"
                    f"\n\n"
                )
            except Exception as e:
                print(f"  ❌ 保存 Agent 回复失败: {e}")
                yield f"data: [ERROR]保存回复失败: {e}\n\n"
        else:
            yield "data: [DONE]{}\n\n"

    # ──────────────────────────────────────────────────────────
    # 非流式对话（保留供测试和 health check 使用）
    # ──────────────────────────────────────────────────────────

    def chat(
        self,
        db: Session,
        conversation_id: int,
        user_content: str,
        image_data_url: str | None = None,
    ) -> ChatResponse:
        """非流式版本，逻辑与 stream_chat 一致，供测试使用。"""
        user_msg   = save_message(db, conversation_id, "user", self._stored_user_content(user_content, image_data_url))
        image_record = self._save_image_if_present(db, conversation_id, user_msg.id, image_data_url)
        compressed = check_and_compress(db, conversation_id)
        if compressed:
            summary_text = get_latest_summary(db, conversation_id)
            if summary_text:
                self.rag.index(
                    text=summary_text,
                    metadata={
                        "type":            "memory_summary",
                        "date":            date.today().strftime("%Y-%m-%d"),
                        "conversation_id": str(conversation_id)
                    }
                )

        messages      = self._build_prompt(db, conversation_id, user_content, image_data_url)
        first_response = self._invoke_llm_sync(messages)
        tool_call    = self._parse_tool_call(first_response)

        if tool_call is not None:
            tool_result = self._execute_tool_call(tool_call)
            messages.append({"role": "assistant", "content": first_response})
            messages.append({
                "role": "user",
                "content": self._tool_followup_prompt(tool_call, tool_result)
            })
            reply_text = self._invoke_llm_sync(messages)
        else:
            reply_text = first_response

        agent_msg = save_message(db, conversation_id, "assistant", reply_text)

        if self._is_meaningful(user_content):
            self.rag.index(
                text=user_content,
                metadata={
                    "type":            "user_message",
                    "date":            date.today().strftime("%Y-%m-%d"),
                    "conversation_id": str(conversation_id)
                }
            )

        return ChatResponse(
            success=True,
            message="回复成功",
            user_message=MessageOut(
                id=user_msg.id,
                conversation_id=user_msg.conversation_id,
                role=user_msg.role,
                content=user_msg.content,
                created_at=user_msg.created_at,
                image_url=image_record.public_url if image_record else None,
                image_created_at=image_record.created_at if image_record else None,
            ),
            reply=MessageOut(
                id=agent_msg.id,
                conversation_id=agent_msg.conversation_id,
                role=agent_msg.role,
                content=agent_msg.content,
                created_at=agent_msg.created_at,
            )
        )

    # ──────────────────────────────────────────────────────────
    # Prompt 构建
    # ──────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        db: Session,
        conversation_id: int,
        user_content: str,
        image_data_url: str | None = None,
    ) -> list[dict]:
        """
        构建三层 Prompt（移除了自动 RAG 注入）：

        Layer 1: system —— 人设 + 工具描述 + 可能的关怀指令
        Layer 2: system —— 中期记忆摘要（本会话压缩，非跨会话检索）
        Layer 3: 近 5 条消息原文 + 当前用户消息
        """
        messages = []

        # ── Layer 1：人设 + 工具描述 + 关怀检测 ─────────────
        persona_prompt = self._get_persona_prompt(db, conversation_id)
        care_injection  = self._check_care_needed(db)

        system_content = persona_prompt + "\n\n" + MEMORY_TOOL_DESC
        if care_injection:
            system_content += f"\n\n{care_injection}"
            print("  💙 关怀指令已注入")

        messages.append({"role": "system", "content": system_content})

        # ── Layer 2：中期记忆摘要（本会话） ──────────────────
        summary = get_latest_summary(db, conversation_id)
        if summary:
            messages.append({
                "role":    "system",
                "content": f"【本会话近期摘要——了解背景用，不必每次提起】\n{summary}"
            })

        # ── Layer 3：近 5 条消息 + 当前消息 ──────────────────
        recent = get_recent_messages(db, conversation_id, limit=5)
        messages.extend(recent)

        # 如果 recent 不包含刚存入的用户消息，手动追加
        current_user_message = self._current_user_message(user_content, image_data_url)
        if image_data_url or not recent or recent[-1]["content"] != user_content:
            messages.append(current_user_message)

        return messages

    def _stored_user_content(self, user_content: str, image_data_url: str | None = None) -> str:
        """Store a lightweight marker instead of base64 image data."""
        content = user_content.strip()
        if image_data_url:
            return f"{content} [图片]" if content else "[图片]"
        return content

    def _current_user_message(self, user_content: str, image_data_url: str | None = None) -> dict:
        """Build OpenAI-compatible text + image content for the current turn."""
        if not image_data_url:
            return {"role": "user", "content": user_content}

        text = user_content.strip() or "请看看这张图片。"
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        }

    def _save_image_if_present(self, db: Session, conversation_id: int, message_id: int, image_data_url: str | None):
        if not image_data_url:
            return None
        return save_message_image(db, conversation_id, message_id, image_data_url)

    # ──────────────────────────────────────────────────────────
    # 工具调用：解析 + 执行
    # ──────────────────────────────────────────────────────────

    def _parse_tool_call(self, llm_response: str) -> dict | None:
        """
        检测 LLM 回复中是否包含工具调用指令。
        返回工具名和 query，没有工具调用则返回 None。

        支持的格式：
          [TOOL_CALL:search_memory:query=关键词]
        """
        pattern = r'\[TOOL_CALL:(search_memory):query=(.+?)\]'
        match   = re.search(pattern, llm_response, re.DOTALL)
        if match:
            return {
                "name": match.group(1).strip(),
                "query": match.group(2).strip(),
            }
        return None

    def _execute_tool_call(self, tool_call: dict) -> str:
        tool_name = tool_call.get("name")
        query = tool_call.get("query", "")
        if tool_name == "search_memory":
            return self._execute_search_memory(query)
        if tool_name == "search_news":
            return self._execute_search_news(query)
        return "工具暂时不可用。"

    def _execute_search_memory(self, query: str) -> str:
        """
        执行 search_memory 工具：
        调用 RAG 检索，返回格式化的历史片段文字。
        """
        try:
            results = self.rag.search(query, top_k=5)
            if not results:
                return "未找到与该话题相关的历史记忆。"
            return self.rag.format_for_prompt(results)
        except Exception as e:
            print(f"  ⚠️  search_memory 执行失败: {e}")
            return "记忆检索暂时不可用。"

    def _execute_search_news(self, query: str) -> str:
        """执行 search_news 工具，返回含真实链接的新闻结果。"""
        try:
            service = get_brave_mcp_service()
            results = service.search_news(query, count=5)
            return service.format_for_prompt(results)
        except Exception as e:
            print(f"  ⚠️  search_news 执行失败: {e}")
            return "新闻搜索暂时不可用，可能是 Brave MCP 服务未启动或网络不可用。"

    def _tool_followup_prompt(self, tool_call: dict, tool_result: str) -> str:
        tool_name = tool_call.get("name")
        if tool_name == "search_news":
            return (
                f"[工具返回结果]\n{tool_result}\n\n"
                "请基于以上新闻搜索结果，结合用户刚才的问题自然回复。\n"
                "要求：\n"
                "· 只能引用工具结果中的新闻事实、来源和链接，不要编造新闻或URL\n"
                "· 尽量附上1-3个工具结果里真实存在的链接\n"
                "· 如果结果不足以回答，要直接说明搜索结果有限\n"
                "· 保持聊天口吻，不要写成长篇新闻报告"
            )
        return (
            f"[工具返回结果]\n{tool_result}\n\n"
            "请基于以上记忆背景，结合用户刚才说的话，给出你的回复。\n"
            "要求：\n"
            "· 记忆只是背景参考，不要逐条复述\n"
            "· 回复要自然、温暖，像一个真正认识用户的朋友\n"
            "· 如果检索结果与当前话题关联不强，可以忽略它"
        )

    # ──────────────────────────────────────────────────────────
    # LLM 调用工具方法
    # ──────────────────────────────────────────────────────────

    def _invoke_llm_sync(self, messages: list[dict]) -> str:
        """同步调用 LLM，返回完整回复文字。"""
        try:
            response = self.llm.invoke(messages)
            if isinstance(response, str):
                return response.strip()
            elif hasattr(response, "content"):
                return response.content.strip()
            return str(response).strip()
        except Exception as e:
            print(f"  ❌ LLM 同步调用失败: {e}")
            return "抱歉，我现在反应有些慢，可以稍后再试试吗？"

    def _stream_llm(self, messages: list[dict]):
        """
        流式调用 LLM。
        yield SSE token 格式的字符串。
        最后 yield "__FULL__<完整文本>" 供调用方获取完整内容。
        """
        full_text = ""
        try:
            for token in self.llm.stream_invoke(messages):
                chunk = (
                    token if isinstance(token, str)
                    else getattr(token, "content", str(token))
                )
                if chunk:
                    full_text += chunk
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            print(f"  ❌ LLM 流式调用失败: {e}")
            # 降级：输出错误提示文字
            fallback = "抱歉，回复时出了点问题，可以再说一遍吗？"
            full_text = fallback
            yield f"data: {json.dumps(fallback, ensure_ascii=False)}\n\n"

        yield f"__FULL__{full_text}"

    def _stream_text(self, text: str):
        """
        把已有文本模拟成流式输出（按中文标点切分）。
        用于第一次 LLM 调用不含工具调用时，直接流式输出结果。
        """
        # 按中文标点和换行切分，保留分隔符
        chunks = re.split(r'(?<=[。！？，、：；\n])', text)
        for chunk in chunks:
            if chunk:
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        yield f"__FULL__{text}"

    # ──────────────────────────────────────────────────────────
    # 人设 & 关怀检测
    # ──────────────────────────────────────────────────────────

    def _get_persona_prompt(self, db: Session, conversation_id: int) -> str:
        """从数据库读取当前会话的人设 system prompt。"""
        try:
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if not conv:
                return self._default_system_prompt()

            persona = db.query(PersonaConfig).filter(
                PersonaConfig.name == (conv.persona or "gentle")
            ).first()
            return persona.system_prompt if persona else self._default_system_prompt()

        except Exception as e:
            print(f"  ⚠️  读取人设失败: {e}")
            return self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        return (
            "你是一个温柔体贴的情绪陪伴助手，名字叫「树洞」。"
            "你善于倾听，不急于给建议，优先表达共情和理解。"
            "用温暖自然的语言回应用户，让他们感到被接纳和支持。"
        )

    def _check_care_needed(self, db: Session) -> str:
        """
        检测是否需要注入关怀指令。
        条件：最近 3 天（昨天、前天、大前天）均有记录，且得分全部 < 4。
        """
        try:
            today  = date.today()
            dates  = [
                (today - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(1, 4)
            ]
            entries = (
                db.query(MoodEntry)
                .filter(MoodEntry.date.in_(dates))
                .all()
            )
            if len(entries) == 3 and all(e.score < 4 for e in entries):
                print(f"  ⚠️  连续 3 天低分，注入关怀指令")
                return (
                    "【特别提示】用户最近连续三天情绪比较低落。"
                    "请在对话开头以自然、温柔的方式主动关心用户的近况，"
                    "语气要像一个真心关心朋友的人，不要让用户感到被分析或监视。"
                )
            return ""
        except Exception as e:
            print(f"  ⚠️  关怀检测失败: {e}")
            return ""

    # ──────────────────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────────────────

    def _is_meaningful(self, text: str) -> bool:
        """判断消息是否有实质内容，过滤语气词，避免噪声写入 RAG。"""
        filler = {
            "嗯","好的","哦","啊","哈哈","是的","好","嗯嗯",
            "谢谢","再见","拜拜","哈","嗯哼","好吧","知道了"
        }
        text = text.strip()
        if text in filler:
            return False
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fa5")
        return chinese_chars > 10


# ═══════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════

_agent_instance = None

def get_companion_agent() -> CompanionAgent:
    """获取 CompanionAgent 单例。"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CompanionAgent()
    return _agent_instance
