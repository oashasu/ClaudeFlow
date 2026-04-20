"""阶段复盘模块 - 异步阶段质量评估（Haiku Agent）

V2新增模块：
- 异步阶段复盘
- Haiku API调用（低成本）
- 输出JSON格式的评估和建议
- 系统级通知（不进对话历史）
"""

import json
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .haiku_client import HaikuClient


class PhaseReviewer:
    """异步阶段复盘"""

    def __init__(self, haiku_client: Optional[HaikuClient] = None, output_dir: Optional[str] = None):
        """
        初始化复盘器

        Args:
            haiku_client: Haiku客户端
            output_dir: 输出目录（默认tasks/{task_id}/reviews/）
        """
        self.haiku_client = haiku_client or HaikuClient()
        self.output_dir = output_dir

    async def review(self, task_id: str, phase: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步阶段复盘（不阻塞主任务）

        Args:
            task_id: 任务ID
            phase: 阶段名称
            summary: 阶段总结内容

        Returns:
            Dict: 复盘结果
        """
        # 构建复盘prompt
        prompt = self._build_prompt(task_id, phase, summary)

        # 异步调用Haiku
        review_result = await self.haiku_client.call(prompt)

        # 构建完整复盘结构
        full_review = {
            "review_type": "phase_review",
            "task_id": task_id,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "review": review_result
        }

        # 存入文件
        self._save_review(task_id, phase, full_review)

        return full_review

    def review_async(self, task_id: str, phase: str, summary: Dict[str, Any]) -> asyncio.Task:
        """
        创建异步复盘任务（不阻塞）

        Args:
            task_id: 任务ID
            phase: 阶段名称
            summary: 阶段总结内容

        Returns:
            asyncio.Task: 异步任务
        """
        return asyncio.create_task(self.review(task_id, phase, summary))

    def _build_prompt(self, task_id: str, phase: str, summary: Dict[str, Any]) -> str:
        """构建复盘prompt"""
        summary_text = json.dumps(summary, ensure_ascii=False, indent=2)

        prompt = f"""
任务{task_id}的{phase}阶段总结：
{summary_text}

请评估本阶段执行质量，输出JSON格式：
```json
{{
  "quality_score": 8,  // 1-10分
  "strengths": ["优点1", "优点2"],  // 最多3条
  "improvements": ["改进建议1"],  // 最多2条
  "lessons_learned": ["经验提炼1"]  // 最多1条
}}
```

要求：
1. 质量评分基于：完整性、效率、代码质量
2. 优点和改进建议要具体
3. 经验提炼要有可复用价值
4. 总输出控制在100字以内
"""
        return prompt

    def _save_review(self, task_id: str, phase: str, review: Dict[str, Any]) -> None:
        """保存复盘结果"""
        # 确定输出目录
        if self.output_dir:
            review_dir = Path(self.output_dir) / task_id / "reviews"
        else:
            review_dir = Path("tasks") / task_id / "reviews"

        # 创建目录
        review_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        filename = f"{phase}_review.json"
        filepath = review_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(review, f, ensure_ascii=False, indent=2)

    def get_review(self, task_id: str, phase: str) -> Optional[Dict[str, Any]]:
        """
        获取阶段复盘

        Args:
            task_id: 任务ID
            phase: 阶段名称

        Returns:
            Dict: 复盘结果，不存在返回None
        """
        if self.output_dir:
            filepath = Path(self.output_dir) / task_id / "reviews" / f"{phase}_review.json"
        else:
            filepath = Path("tasks") / task_id / "reviews" / f"{phase}_review.json"

        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)

        return None

    def notify_system(self, task_id: str, phase: str) -> Dict[str, Any]:
        """
        生成系统级通知（不进对话历史）

        Args:
            task_id: 任务ID
            phase: 阶段名称

        Returns:
            Dict: 系统消息结构
        """
        return {
            "type": "system",
            "content": f"[checkpoint] {task_id}::{phase} 复盘已完成"
        }