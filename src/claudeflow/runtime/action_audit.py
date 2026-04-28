"""Action Audit - Runtime 动作审计记录模块

T302: 实现干预/完成/失败动作的结构化审计记录存储与查询。
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from pathlib import Path


class ActionAuditRecord(BaseModel):
    """动作审计记录结构"""

    action_id: str = Field(..., description="审计记录唯一 ID")
    action_type: str = Field(..., description="动作类型: intervene/complete/fail")
    target_task_id: str = Field(..., description="目标任务 ID")
    target_session_id: Optional[str] = Field(None, description="目标会话 ID")
    success: bool = Field(..., description="执行是否成功")
    message: str = Field(..., description="执行结果消息")
    operator: str = Field(default="console", description="操作者标识")
    timestamp: str = Field(..., description="执行时间 ISO 格式")
    metadata: dict = Field(default_factory=dict, description="额外元数据")

    # intervene 专属字段
    prompt: Optional[str] = Field(None, description="干预内容")

    # complete 专属字段
    summary: Optional[str] = Field(None, description="完成摘要")
    changed_files: Optional[list[str]] = Field(None, description="变更文件列表")
    test_status: Optional[str] = Field(None, description="测试状态")
    test_count: Optional[int] = Field(None, description="测试数量")

    # fail 专属字段
    reason: Optional[str] = Field(None, description="失败原因")


class ActionAuditStore:
    """审计记录存储

    使用 JSON 文件存储，支持按 governance_root 组织。
    """

    def __init__(self, governance_root: Optional[str] = None):
        if governance_root:
            self.audit_dir = Path(governance_root) / "action-audit"
        else:
            self.audit_dir = Path(os.environ.get("CLAUDEFLOW_AUDIT_DIR", ".audit/action-audit"))
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.audit_dir / "records.json"

    def _load_records(self) -> list[dict]:
        if not self.audit_file.exists():
            return []
        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_records(self, records: list[dict]) -> None:
        with open(self.audit_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    def write_record(self, record: ActionAuditRecord) -> str:
        """写入审计记录，返回 action_id"""
        records = self._load_records()
        records.append(record.model_dump())
        self._save_records(records)
        return record.action_id

    def list_records(
        self,
        action_type: Optional[str] = None,
        target_task_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[ActionAuditRecord]:
        """查询审计记录列表"""
        records = self._load_records()

        # 过滤
        if action_type:
            records = [r for r in records if r.get("action_type") == action_type]
        if target_task_id:
            records = [r for r in records if r.get("target_task_id") == target_task_id]

        # 按时间倒序
        records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

        # 限制数量
        records = records[:limit]

        return [ActionAuditRecord(**r) for r in records]

    def get_record(self, action_id: str) -> Optional[ActionAuditRecord]:
        """查询单个审计记录"""
        records = self._load_records()
        for r in records:
            if r.get("action_id") == action_id:
                return ActionAuditRecord(**r)
        return None

    def clear_records(self) -> None:
        """清空所有审计记录（仅用于测试）"""
        self._save_records([])


def create_audit_record(
    action_type: str,
    target_task_id: str,
    target_session_id: Optional[str] = None,
    success: bool = True,
    message: str = "",
    operator: str = "console",
    prompt: Optional[str] = None,
    summary: Optional[str] = None,
    changed_files: Optional[list[str]] = None,
    test_status: Optional[str] = None,
    test_count: Optional[int] = None,
    reason: Optional[str] = None,
    **extra_metadata,
) -> ActionAuditRecord:
    """创建审计记录的工厂函数"""
    record_id = f"audit-{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().isoformat()

    # 收集 metadata
    metadata = extra_metadata.copy()
    if prompt:
        metadata["prompt"] = prompt
    if summary:
        metadata["summary"] = summary
    if changed_files:
        metadata["changed_files"] = changed_files
    if test_status:
        metadata["test_status"] = test_status
    if test_count is not None:
        metadata["test_count"] = test_count
    if reason:
        metadata["reason"] = reason

    return ActionAuditRecord(
        action_id=record_id,
        action_type=action_type,
        target_task_id=target_task_id,
        target_session_id=target_session_id,
        success=success,
        message=message,
        operator=operator,
        timestamp=timestamp,
        metadata=metadata,
        prompt=prompt,
        summary=summary,
        changed_files=changed_files,
        test_status=test_status,
        test_count=test_count,
        reason=reason,
    )