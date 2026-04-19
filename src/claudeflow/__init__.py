"""ClaudeFlow - AI驱动的敏捷工作流系统

V2架构：12个核心模块协同工作
"""

from claudeflow.checkpoint import CheckpointManager, Checkpoint
from claudeflow.task_manager import TaskManager, Task
from claudeflow.state_machine import TaskStatus, Phase, StateMachine
from claudeflow.scheduler import Scheduler
from claudeflow.employee_pool import EmployeePool, Employee, EmployeeStatus, EmployeeRole
from claudeflow.knowledge_retrieval import KnowledgeRetriever, KnowledgeEntry
from claudeflow.cli import CliApp
from claudeflow.alert_handler import AlertHandler
from claudeflow.progress_reporter import ProgressReporter
from claudeflow.session_parser import SessionParser
from claudeflow.thinking_filter import ThinkingFilter
from claudeflow.websocket_client import WebSocketClient

__all__ = [
    # Checkpoint
    "CheckpointManager",
    "Checkpoint",
    # Task
    "TaskManager",
    "Task",
    # State Machine
    "TaskStatus",
    "Phase",
    "StateMachine",
    # Scheduler
    "Scheduler",
    # Employee Pool
    "EmployeePool",
    "Employee",
    "EmployeeStatus",
    "EmployeeRole",
    # Knowledge Retrieval
    "KnowledgeRetriever",
    "KnowledgeEntry",
    # CLI
    "CliApp",
    # Utilities
    "AlertHandler",
    "ProgressReporter",
    "SessionParser",
    "ThinkingFilter",
    "WebSocketClient",
]

__version__ = "2.0.0"