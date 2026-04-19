"""Checkpoint模块 - 状态快照保存/恢复/回退

V1核心功能：状态快照保存、恢复、列表、回退
V2新增功能：LangGraph风格接口、文件损坏告警、format_version
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from claudeflow.alert_handler import AlertHandler


class CheckpointNotFoundError(Exception):
    """快照不存在异常"""
    pass


@dataclass
class Checkpoint:
    """快照数据结构"""

    checkpoint_id: str
    task_id: str
    phase: str
    timestamp: datetime
    task_state: Dict[str, Any]
    execution_context: Dict[str, Any]
    filename: str
    checkpoint_format_version: str = "2.0"  # V2新增

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "phase": self.phase,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "task_state": self.task_state,
            "execution_context": self.execution_context,
            "filename": self.filename,
            "checkpoint_format_version": self.checkpoint_format_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """从字典反序列化"""
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            checkpoint_id=data["checkpoint_id"],
            task_id=data["task_id"],
            phase=data["phase"],
            timestamp=timestamp,
            task_state=data["task_state"],
            execution_context=data["execution_context"],
            filename=data["filename"],
            checkpoint_format_version=data.get("checkpoint_format_version", "1.0")
        )


class CheckpointManager:
    """快照管理器"""

    SUPPORTED_FORMAT_VERSIONS = ["1.0", "2.0"]

    def __init__(self, checkpoint_dir: str, alert_handler: Optional["AlertHandler"] = None):
        """
        初始化快照管理器

        Args:
            checkpoint_dir: 快照存储目录
            alert_handler:告警处理器（V2新增，用于文件损坏告警）
        """
        self.checkpoint_dir = checkpoint_dir
        self.alert_handler = alert_handler

        # 确保目录存在
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

    def _generate_filename(self, checkpoint_id: str, phase: str) -> str:
        """生成快照文件名"""
        # 处理phase可能是int或字符串的情况
        if isinstance(phase, int):
            from claudeflow.state_machine import Phase
            phase = Phase(phase).name.lower()
        else:
            phase = str(phase).lower()

        # 使用 phase 映射到 v5 格式
        phase_map = {
            "requirements": "v1_req",
            "brainstorm": "v2_brain",
            "architecture": "v3_arch",
            "design": "v4_design",
            "development": "v5_dev",
            "testing": "v6_test",
            "review": "v7_rev",
            "acceptance": "v8_accept"
        }
        prefix = phase_map.get(phase, "v5")
        # 包含checkpoint_id确保唯一性
        return f"{prefix}_{phase[:3]}_{checkpoint_id}.json"

    def save(
        self,
        task_id: str,
        phase: str,
        task_state: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Checkpoint:
        """
        保存快照

        Args:
            task_id: 任务ID
            phase: 当前阶段
            task_state: 任务状态
            execution_context: 执行上下文

        Returns:
            Checkpoint: 保存的快照对象
        """
        checkpoint_id = f"cp_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now()
        filename = self._generate_filename(checkpoint_id, phase)

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            phase=phase,
            timestamp=timestamp,
            task_state=task_state,
            execution_context=execution_context,
            filename=filename
        )

        # 写入JSON文件
        filepath = os.path.join(self.checkpoint_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

        return checkpoint

    def restore(
        self,
        checkpoint_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Checkpoint:
        """
        恢复快照

        Args:
            checkpoint_id: 快照ID
            filename: 文件名

        Returns:
            Checkpoint: 恢复的快照对象

        Raises:
            CheckpointNotFoundError: 快照不存在
        """
        if filename:
            filepath = os.path.join(self.checkpoint_dir, filename)
            if not os.path.exists(filepath):
                raise CheckpointNotFoundError(f"快照文件不存在: {filename}")

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return Checkpoint.from_dict(data)
            except json.JSONDecodeError as e:
                # V2新增：发送文件损坏告警
                if self.alert_handler:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(
                            self.alert_handler.send_file_corrupt_alert(
                                file_path=filepath,
                                error_type="JSONDecodeError",
                                module="checkpoint"
                            )
                        )
                    except RuntimeError:
                        pass
                raise CheckpointNotFoundError(f"快照文件损坏: {filename}")

        if checkpoint_id:
            # 搜索所有快照文件查找匹配的checkpoint_id
            for f in os.listdir(self.checkpoint_dir):
                if f.endswith('.json'):
                    filepath = os.path.join(self.checkpoint_dir, f)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as fp:
                            data = json.load(fp)
                            if data.get("checkpoint_id") == checkpoint_id:
                                return Checkpoint.from_dict(data)
                    except json.JSONDecodeError:
                        continue  # 静默忽略损坏文件

            raise CheckpointNotFoundError(f"快照不存在: {checkpoint_id}")

        raise CheckpointNotFoundError("需要指定 checkpoint_id 或 filename")

    def list_checkpoints(self, task_id: Optional[str] = None) -> List[Checkpoint]:
        """
        列出快照

        Args:
            task_id: 任务ID（可选，筛选指定任务的快照）

        Returns:
            List[Checkpoint]: 快照列表，按时间排序
        """
        checkpoints = []

        if not os.path.exists(self.checkpoint_dir):
            return checkpoints

        for f in os.listdir(self.checkpoint_dir):
            if f.endswith('.json'):
                filepath = os.path.join(self.checkpoint_dir, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                        checkpoint = Checkpoint.from_dict(data)

                        # 如果指定了task_id，只返回该任务的快照
                        if task_id and checkpoint.task_id != task_id:
                            continue

                        checkpoints.append(checkpoint)
                except json.JSONDecodeError as e:
                    # V2新增：发送文件损坏告警
                    if self.alert_handler:
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(
                                self.alert_handler.send_file_corrupt_alert(
                                    file_path=filepath,
                                    error_type="JSONDecodeError",
                                    module="checkpoint"
                                )
                            )
                        except RuntimeError:
                            # 没有运行的事件循环，同步调用（测试场景）
                            pass
                    continue  # 静默忽略，不崩溃
                except KeyError:
                    # 忽略缺少必要字段的文件
                    continue

        # 按时间排序
        checkpoints.sort(key=lambda cp: cp.timestamp)

        return checkpoints

    # V2新增：LangGraph风格接口
    def get_tuple(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """
        LangGraph风格接口：获取checkpoint

        Args:
            config: 配置字典，包含task_id和checkpoint_id

        Returns:
            Optional[Checkpoint]: checkpoint或None
        """
        checkpoint_id = config.get("checkpoint_id")
        if checkpoint_id:
            try:
                return self.restore(checkpoint_id=checkpoint_id)
            except CheckpointNotFoundError:
                return None
        return None

    def put(self, config: Dict[str, Any], checkpoint: Checkpoint) -> None:
        """
        LangGraph风格接口：保存checkpoint

        Args:
            config: 配置字典
            checkpoint: checkpoint对象
        """
        filepath = os.path.join(self.checkpoint_dir, checkpoint.filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

    def put_writes(self, config: Dict[str, Any], writes: List[Dict[str, Any]]) -> None:
        """
        LangGraph风格接口：写入checkpoint的writes

        Args:
            config: 配置字典
            writes: 写入列表
        """
        checkpoint_id = config.get("checkpoint_id")
        if not checkpoint_id:
            return

        try:
            checkpoint = self.restore(checkpoint_id=checkpoint_id)
            # 添加writes到execution_context
            checkpoint.execution_context["writes"] = writes
            self.put(config, checkpoint)
        except CheckpointNotFoundError:
            pass

    def rollback(
        self,
        task_id: str,
        target_checkpoint_id: str
    ) -> Checkpoint:
        """
        回退到指定快照

        Args:
            task_id: 任务ID
            target_checkpoint_id: 目标快照ID

        Returns:
            Checkpoint: 恢复的目标快照

        Raises:
            CheckpointNotFoundError: 目标快照不存在
        """
        # 获取目标快照
        target_checkpoint = self.restore(checkpoint_id=target_checkpoint_id)

        if target_checkpoint.task_id != task_id:
            raise CheckpointNotFoundError(f"快照不属于任务: {task_id}")

        # 获取所有该任务的快照
        all_checkpoints = self.list_checkpoints(task_id=task_id)

        # 删除目标快照之后的所有快照
        for checkpoint in all_checkpoints:
            if checkpoint.timestamp > target_checkpoint.timestamp:
                filepath = os.path.join(self.checkpoint_dir, checkpoint.filename)
                if os.path.exists(filepath):
                    os.remove(filepath)

        return target_checkpoint