"""会话ID获取工具

用于获取Claude Code CLI当前会话的sessionId

方案：读取 ~/.claude/projects/ 目录下最新修改的 .jsonl 文件名
文件名格式：{sessionId}.jsonl（UUID格式）
"""

import os
from pathlib import Path
from typing import Optional


def get_current_session_id(project_dir: Optional[str] = None) -> Optional[str]:
    """
    获取当前Claude Code会话ID

    Args:
        project_dir: 项目目录，默认当前工作目录

    Returns:
        str: sessionId（UUID格式），若无法获取则返回None
    """
    if project_dir is None:
        project_dir = os.getcwd()

    # Claude会话存储路径
    claude_projects = Path.home() / ".claude" / "projects"

    # 项目对应的会话目录名格式：-{path_with_dash}
    # 例如：/Users/claw/sandbox → -Users-claw-sandbox
    # 需要去掉开头的/，然后替换剩余的/为-
    normalized_path = project_dir.lstrip("/").replace("/", "-")
    dir_name = f"-{normalized_path}"
    project_session_dir = claude_projects / dir_name

    if not project_session_dir.exists():
        # 尝试更宽松的匹配（部分路径）
        for d in claude_projects.iterdir():
            if d.is_dir() and dir_name in d.name:
                project_session_dir = d
                break

        if not project_session_dir.exists():
            return None

    # 获取最新修改的jsonl文件
    jsonl_files = list(project_session_dir.glob("*.jsonl"))

    if not jsonl_files:
        return None

    # 按修改时间排序，取最新的
    latest_file = max(jsonl_files, key=lambda f: f.stat().st_mtime)

    # 文件名去掉.jsonl就是sessionId
    return latest_file.stem


def format_session_id_for_resume(session_id: str) -> str:
    """
    格式化sessionId用于 --resume 参数

    Args:
        session_id: 原始sessionId

    Returns:
        str: 可用于 claude --resume 的sessionId
    """
    return session_id


def get_resume_command(session_id: str) -> str:
    """
    生成恢复会话的命令

    Args:
        session_id: 会话ID

    Returns:
        str: claude --resume 命令
    """
    return f"claude --resume {session_id}"


# 测试代码
if __name__ == "__main__":
    session_id = get_current_session_id()
    if session_id:
        print(f"当前会话ID: {session_id}")
        print(f"恢复命令: {get_resume_command(session_id)}")
    else:
        print("无法获取当前会话ID")