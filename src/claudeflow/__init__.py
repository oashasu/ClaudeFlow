"""ClaudeFlow Python package exports."""

from claudeflow.runtime import (
    CliDriver,
    CliSession,
    RuntimeManager,
    SessionIndex,
    UnknownTaskError,
    WorkerTaskSpec,
    WriteLockConflictError,
)
from claudeflow.workflow import (
    Checkpoint,
    CheckpointManager,
    Phase,
    Scheduler,
    StateMachine,
    Task,
    TaskManager,
    TaskStatus,
)
from claudeflow.governance import (
    GateStatus,
    GovernancePhase,
    GovernancePoller,
    GovernanceStateMachine,
    GovernanceWorkspace,
    IllegalTransitionError,
    PipelineStateError,
    PipelineStateStore,
    TaskPackageError,
    TaskPackageLoader,
)
from claudeflow.cli import CliApp
from claudeflow.thinking_filter import ThinkingFilter
from claudeflow.session_parser import SessionParser

__all__ = [
    # Runtime core
    "CliDriver",
    "CliSession",
    "RuntimeManager",
    "WorkerTaskSpec",
    "SessionIndex",
    "WriteLockConflictError",
    "UnknownTaskError",
    # Workflow
    "CheckpointManager",
    "Checkpoint",
    "TaskManager",
    "Task",
    "TaskStatus",
    "Phase",
    "StateMachine",
    "Scheduler",
    # Governance (Phase A)
    "GovernanceWorkspace",
    "PipelineStateStore",
    "PipelineStateError",
    "TaskPackageLoader",
    "TaskPackageError",
    "GovernancePhase",
    "GateStatus",
    "GovernanceStateMachine",
    "IllegalTransitionError",
    "GovernancePoller",
    # CLI
    "CliApp",
    # Utilities (runtime-poc retained)
    "ThinkingFilter",
    "SessionParser",
]

__version__ = "3.1.0"
