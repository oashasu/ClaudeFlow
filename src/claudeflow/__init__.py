"""ClaudeFlow - AI驱动的敏捷工作流系统

V2架构：15个核心模块协同工作
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
from claudeflow.session_utils import get_current_session_id, format_session_id_for_resume, get_resume_command
from claudeflow.haiku_client import HaikuClient, HaikuConfig
from claudeflow.phase_reviewer import PhaseReviewer
from claudeflow.task_reviewer import TaskReviewer
from claudeflow.cli_driver import CliDriver, CliSession

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
    # Session Utilities
    "get_current_session_id",
    "format_session_id_for_resume",
    "get_resume_command",
    # Reviewer (V2)
    "HaikuClient",
    "HaikuConfig",
    "PhaseReviewer",
    "TaskReviewer",
    # CLI Driver (V2.4.0)
    "CliDriver",
    "CliSession",
]

__version__ = "2.4.0"