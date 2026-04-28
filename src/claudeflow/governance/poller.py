"""T005: GovernancePoller — 治理文件变更轮询与刷新。

职责:
- 轮询关键治理文件
- 比较修改时间检测变更
- 发现变更后重新加载对应对象
- 失败时保留上次有效缓存

契约:
- 发现变更 → 调用 reloader → 缓存重载后的对象
- reload 失败 → 保留旧缓存，reload_result = "failed"
- reload 成功 → 更新缓存为新对象，reload_result = "success"

轮询对象:
- .super-dev/pipeline-state.json
- .super-dev/phases/**/tasks/*.yaml
- .super-dev/phases/**/reviews/*.md
- .super-dev/phases/**/gate-report.md
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChangeRecord:
    """一次变更记录。"""

    file_path: str
    change_type: str  # "modified" | "created" | "deleted"
    reload_result: str  # "success" | "failed" | "skipped"
    error_reason: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type,
            "reload_result": self.reload_result,
            "error_reason": self.error_reason,
            "timestamp": self.timestamp,
        }


@dataclass
class _FileSnapshot:
    """单个文件的快照。"""

    path: Path
    mtime: float = 0.0
    content_hash: str = ""


class GovernancePoller:
    """治理文件轮询器。"""

    DEFAULT_INTERVAL = 3.0

    def __init__(
        self,
        super_dev_root: str | Path,
        interval: float = DEFAULT_INTERVAL,
        on_change: Optional[Callable[[ChangeRecord], None]] = None,
        reloaders: Optional[Dict[str, Callable[[Path], tuple[Any, bool]]]] = None,
    ) -> None:
        self.root = Path(super_dev_root)
        self.interval = max(interval, 0.5)
        self.on_change = on_change
        self._reloaders: Dict[str, Callable[[Path], tuple[Any, bool]]] = reloaders or {}

        self._snapshots: Dict[str, _FileSnapshot] = {}
        self._cache: Dict[str, Any] = {}
        self._change_log: List[ChangeRecord] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def register_reloader(
        self, file_pattern: str, reloader: Callable[[Path], tuple[Any, bool]]
    ) -> None:
        """注册文件重载器。

        file_pattern 匹配文件路径后缀，如 "pipeline-state.json" 或 ".yaml"。
        reloader 接收文件路径，返回 (object, success) 元组：
          - object: 重载后的对象（PipelineState/TaskPackage 等）
          - success: True 表示成功，False 表示失败
        """
        self._reloaders[file_pattern] = reloader

    def get_cache(self, file_path: str) -> Any:
        """获取指定文件的缓存对象。"""
        with self._lock:
            return self._cache.get(file_path)

    def get_watched_files(self) -> List[Path]:
        """计算当前应监控的文件列表。"""
        files: List[Path] = []

        pipeline_state = self.root / "pipeline-state.json"
        if pipeline_state.exists():
            files.append(pipeline_state)

        for pattern in (
            "phases/**/tasks/*.yaml",
            "phases/**/reviews/*.md",
            "phases/**/gate-report.md",
        ):
            files.extend(sorted(self.root.glob(pattern)))

        return files

    def scan_once(self) -> List[ChangeRecord]:
        """执行一次轮询扫描，返回本次检测到的变更列表。

        检测到变更后会调用对应 reloader 进行对象重载，
        reload_result 反映真实的重载结果。
        """
        current_files = self.get_watched_files()
        current_paths = {str(f) for f in current_files}
        changes: List[ChangeRecord] = []

        for file_path in current_files:
            key = str(file_path)
            try:
                stat = file_path.stat()
                mtime = stat.st_mtime
                content_hash = self._hash_file(file_path)
            except OSError:
                continue

            snapshot = self._snapshots.get(key)
            if snapshot is None:
                changes.append(self._record_change(
                    file_path, "created", mtime, content_hash,
                ))
            elif snapshot.mtime != mtime or snapshot.content_hash != content_hash:
                changes.append(self._record_change(
                    file_path, "modified", mtime, content_hash,
                ))

            self._snapshots[key] = _FileSnapshot(
                path=file_path, mtime=mtime, content_hash=content_hash,
            )

        for key in list(self._snapshots.keys()):
            if key not in current_paths:
                changes.append(self._record_delete(key))
                del self._snapshots[key]

        return changes

    def start(self) -> None:
        """在后台线程中启动轮询。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="governance-poller",
        )
        self._thread.start()

    def stop(self) -> None:
        """停止轮询。"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval * 2)
        self._thread = None

    @property
    def change_log(self) -> List[ChangeRecord]:
        with self._lock:
            return list(self._change_log)

    def _poll_loop(self) -> None:
        while self._running:
            try:
                self.scan_once()
            except Exception as exc:
                logger.error("轮询异常: %s", exc)
            time.sleep(self.interval)

    def _find_reloader(self, file_path: Path) -> Optional[Callable[[Path], tuple[Any, bool]]]:
        """根据文件路径查找匹配的 reloader。"""
        name = file_path.name
        if name in self._reloaders:
            return self._reloaders[name]
        for suffix, reloader in self._reloaders.items():
            if name.endswith(suffix) or str(file_path).endswith(suffix):
                return reloader
        return None

    def _reload_file(self, file_path: Path) -> tuple[str, str, Any]:
        """尝试重载文件，返回 (reload_result, error_reason, cached_object)。"""
        reloader = self._find_reloader(file_path)
        if reloader is None:
            return "skipped", "", None
        try:
            obj, success = reloader(file_path)
            if success:
                return "success", "", obj
            return "failed", "reloader returned False", None
        except Exception as exc:
            return "failed", str(exc), None

    def _record_change(
        self,
        file_path: Path,
        change_type: str,
        mtime: float,
        content_hash: str,
    ) -> ChangeRecord:
        now = time.time()
        reload_result, error_reason, cached_obj = "skipped", "", None

        if change_type == "created" or change_type == "modified":
            reload_result, error_reason, cached_obj = self._reload_file(file_path)

            if reload_result == "success" and cached_obj is not None:
                with self._lock:
                    self._cache[str(file_path)] = cached_obj
            elif reload_result == "failed":
                logger.warning(
                    "重载失败，保留旧缓存: %s, 原因: %s",
                    file_path, error_reason,
                )

        record = ChangeRecord(
            file_path=str(file_path),
            change_type=change_type,
            reload_result=reload_result,
            error_reason=error_reason,
            timestamp=now,
        )
        with self._lock:
            self._change_log.append(record)
        if self.on_change:
            try:
                self.on_change(record)
            except Exception:
                pass
        return record

    def _record_delete(self, key: str) -> ChangeRecord:
        now = time.time()
        with self._lock:
            self._cache.pop(key, None)
        record = ChangeRecord(
            file_path=key,
            change_type="deleted",
            reload_result="skipped",
            timestamp=now,
        )
        with self._lock:
            self._change_log.append(record)
        if self.on_change:
            try:
                self.on_change(record)
            except Exception:
                pass
        return record

    @staticmethod
    def _hash_file(path: Path) -> str:
        content = path.read_bytes()
        return hashlib.md5(content).hexdigest()
