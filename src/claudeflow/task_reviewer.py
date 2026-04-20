"""任务复盘模块 - 任务级别经验提炼（Haiku Agent）

V2新增模块：
- 任务完成后的整体复盘
- 汇总所有阶段总结和复盘
- 提取可复用的经验教训
- 存入知识库索引
"""

import json
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .haiku_client import HaikuClient


class TaskReviewer:
    """任务级别复盘"""

    def __init__(self, haiku_client: Optional[HaikuClient] = None, output_dir: Optional[str] = None):
        """
        初始化复盘器

        Args:
            haiku_client: Haiku客户端
            output_dir: 输出目录（默认knowledge/）
        """
        self.haiku_client = haiku_client or HaikuClient()
        self.output_dir = output_dir or "knowledge"

    async def review(self, task_id: str, phase_summaries: List[Dict[str, Any]], phase_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        任务级别复盘

        Args:
            task_id: 任务ID
            phase_summaries: 所有阶段总结列表
            phase_reviews: 所有阶段复盘列表

        Returns:
            Dict: 任务复盘结果
        """
        # 构建复盘prompt
        prompt = self._build_prompt(task_id, phase_summaries, phase_reviews)

        # 异步调用Haiku
        review_result = await self.haiku_client.call(prompt)

        # 构建完整复盘结构
        full_review = {
            "review_type": "task_review",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "review": review_result,
            "phases_summary": self._summarize_phases(phase_reviews)
        }

        # 存入文件
        self._save_review(task_id, full_review)

        # 更新知识库索引
        self._update_knowledge_index(task_id, full_review)

        return full_review

    def review_async(self, task_id: str, phase_summaries: List[Dict[str, Any]], phase_reviews: List[Dict[str, Any]]) -> asyncio.Task:
        """
        创建异步复盘任务（不阻塞）

        Args:
            task_id: 任务ID
            phase_summaries: 所有阶段总结列表
            phase_reviews: 所有阶段复盘列表

        Returns:
            asyncio.Task: 异步任务
        """
        return asyncio.create_task(self.review(task_id, phase_summaries, phase_reviews))

    def _build_prompt(self, task_id: str, phase_summaries: List[Dict[str, Any]], phase_reviews: List[Dict[str, Any]]) -> str:
        """构建任务复盘prompt"""
        # 汇总阶段信息
        phases_text = ""
        for i, summary in enumerate(phase_summaries):
            phase_name = summary.get('phase', f'Phase{i+1}')
            phases_text += f"\n### {phase_name}阶段\n"
            phases_text += f"总结：{json.dumps(summary.get('summary', {}), ensure_ascii=False)}\n"

            # 查找对应复盘
            matching_review = None
            for review in phase_reviews:
                if review.get('phase') == phase_name:
                    matching_review = review
                    break

            if matching_review:
                phases_text += f"复盘评分：{matching_review.get('review', {}).get('quality_score', 0)}\n"

        prompt = f"""
任务{task_id}已完成，以下是各阶段执行情况：
{phases_text}

请进行任务级别复盘，输出JSON格式：
```json
{{
  "overall_quality": 8,  // 1-10分，整体质量评分
  "key_lessons": [
    "经验1：具体可复用的经验",
    "经验2：..."
  ],  // 最多3条，要有可复用价值
  "knowledge_extracted": [
    "知识点1：可归档到知识库的内容",
    "知识点2：..."
  ],  // 最多2条
  "recommendations": [
    "建议：下次同类任务的改进建议"
  ]  // 最多1条
}}
```

要求：
1. 整体评分基于各阶段平均分和最终成果
2. 经验要具体、可复用，不要泛泛而谈
3. 知识点要明确可归档的内容类型
4. 总输出控制在200字以内
"""
        return prompt

    def _summarize_phases(self, phase_reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """汇总阶段评分"""
        result = []
        for review in phase_reviews:
            phase_name = review.get('phase', 'Unknown')
            quality = review.get('review', {}).get('quality_score', 0)
            result.append({
                "phase": phase_name,
                "quality": quality
            })
        return result

    def _save_review(self, task_id: str, review: Dict[str, Any]) -> None:
        """保存任务复盘"""
        # 保存到tasks目录
        review_dir = Path("tasks") / task_id / "reviews"
        review_dir.mkdir(parents=True, exist_ok=True)

        filepath = review_dir / "task_review.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(review, f, ensure_ascii=False, indent=2)

    def _update_knowledge_index(self, task_id: str, review: Dict[str, Any]) -> None:
        """更新知识库索引"""
        # 确保知识库目录存在
        knowledge_dir = Path(self.output_dir)
        knowledge_dir.mkdir(parents=True, exist_ok=True)

        # 累加经验到lessons_learned目录
        lessons_dir = knowledge_dir / "lessons_learned"
        lessons_dir.mkdir(parents=True, exist_ok=True)

        key_lessons = review.get('review', {}).get('key_lessons', [])
        for i, lesson in enumerate(key_lessons):
            lesson_file = lessons_dir / f"lesson_{task_id}_{i+1}.json"
            lesson_data = {
                "task_id": task_id,
                "lesson": lesson,
                "timestamp": review.get('timestamp'),
                "source": "task_review"
            }
            with open(lesson_file, 'w', encoding='utf-8') as f:
                json.dump(lesson_data, f, ensure_ascii=False, indent=2)

        # 更新全局索引
        index_file = knowledge_dir / "reviews_index.json"
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"reviews": [], "total_lessons": 0}

        # 添加新记录
        index_entry = {
            "task_id": task_id,
            "review_path": f"tasks/{task_id}/reviews/task_review.json",
            "overall_quality": review.get('review', {}).get('overall_quality', 0),
            "lessons": key_lessons,
            "timestamp": review.get('timestamp')
        }
        index["reviews"].append(index_entry)
        index["total_lessons"] += len(key_lessons)

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def get_review(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务复盘

        Args:
            task_id: 任务ID

        Returns:
            Dict: 复盘结果，不存在返回None
        """
        filepath = Path("tasks") / task_id / "reviews" / "task_review.json"

        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)

        return None

    def get_all_reviews(self) -> List[Dict[str, Any]]:
        """
        获取所有任务复盘索引

        Returns:
            List: 复盘索引列表
        """
        index_file = Path(self.output_dir) / "reviews_index.json"

        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
                return index.get("reviews", [])

        return []