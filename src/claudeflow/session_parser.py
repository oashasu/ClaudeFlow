"""Session解析器 - 解析.jsonl + 工具摘要

V2新增模块：
- 解析Claude Code输出的.jsonl文件
- 提取工具调用信息
- 生成工具摘要
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List


@dataclass
class ToolCall:
    """工具调用数据结构"""

    timestamp: str
    tool_name: str
    tool_input: Dict[str, Any]
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = asdict(self)
        if self.summary is None:
            data["summary"] = extract_action_from_tool(
                self.tool_name, self.tool_input
            )
        return data


def extract_action_from_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """
    从工具调用直接生成动作描述（无Agent调用）

    Args:
        tool_name: 工具名称
        tool_input: 工具输入参数

    Returns:
        str: 动作摘要描述
    """
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        filename = file_path.split("/")[-1] if file_path else "文件"
        return f"正在读取 {filename}"

    elif tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        filename = file_path.split("/")[-1] if file_path else "文件"
        return f"正在修改 {filename}"

    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        filename = file_path.split("/")[-1] if file_path else "文件"
        return f"正在创建 {filename}"

    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if "pytest" in cmd:
            return "正在运行测试"
        elif "git" in cmd:
            return "正在执行Git操作"
        # 截断长命令
        return f"正在执行: {cmd[:30]}"

    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        # 截断长pattern
        return f"正在搜索: {pattern[:30]}"

    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        return f"正在查找文件: {pattern}"

    elif tool_name == "Agent":
        return "正在启动子代理"

    elif tool_name == "Skill":
        return "正在执行技能"

    return f"正在执行 {tool_name}"


class SessionParser:
    """Session解析器 - 解析.jsonl文件"""

    def __init__(self, jsonl_path: str):
        """
        初始化解析器

        Args:
            jsonl_path: .jsonl文件路径
        """
        self.jsonl_path = jsonl_path

    def parse_jsonl(self) -> List[Dict[str, Any]]:
        """
        解析.jsonl文件

        Returns:
            List[Dict]: 消息列表
        """
        messages = []

        if not os.path.exists(self.jsonl_path):
            return messages

        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    # 跳过无效行
                    continue

        return messages

    def extract_tool_calls(self) -> List[ToolCall]:
        """
        提取工具调用列表

        Returns:
            List[ToolCall]: 工具调用列表
        """
        messages = self.parse_jsonl()
        tool_calls = []

        for msg in messages:
            if msg.get("type") == "tool_use":
                tool_call = ToolCall(
                    timestamp=msg.get("timestamp", ""),
                    tool_name=msg.get("tool_name", ""),
                    tool_input=msg.get("tool_input", {})
                )
                tool_call.summary = extract_action_from_tool(
                    tool_call.tool_name, tool_call.tool_input
                )
                tool_calls.append(tool_call)

        return tool_calls

    def extract_all_messages(self) -> List[Dict[str, Any]]:
        """
        提取所有消息

        Returns:
            List[Dict]: 所有消息列表
        """
        return self.parse_jsonl()

    def extract_thinking(self) -> List[str]:
        """
        提取thinking内容

        Returns:
            List[str]: thinking内容列表
        """
        messages = self.parse_jsonl()
        thinking_list = []

        for msg in messages:
            if msg.get("type") == "assistant":
                thinking = msg.get("thinking", "")
                if thinking:
                    thinking_list.append(thinking)

        return thinking_list

    def generate_summary_report(self) -> Dict[str, Any]:
        """
        生成摘要报告

        Returns:
            Dict: 摘要报告
        """
        tool_calls = self.extract_tool_calls()

        # 统计工具类型
        tool_types: Dict[str, int] = {}
        for tc in tool_calls:
            tool_types[tc.tool_name] = tool_types.get(tc.tool_name, 0) + 1

        # 生成摘要列表
        summaries = [tc.summary for tc in tool_calls if tc.summary]

        return {
            "total_tool_calls": len(tool_calls),
            "tool_types": tool_types,
            "summaries": summaries,
            "timestamp": datetime.now().isoformat()
        }