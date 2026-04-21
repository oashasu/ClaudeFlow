"""验收层实现

三层分级校验：
- L1 强制量化层：覆盖率≥80%、编译无报错，一票否决阻断流程
- L2 半量化层：命名规范检测，返回违规清单（非阻断）
- L3 纯人工层：手动触发接口，仅归档不自动化
"""

import re
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime
import os


@dataclass
class ViolationRecord:
    """违规记录"""
    rule: str
    line: int
    message: str
    severity: str = "warning"


@dataclass
class AcceptanceResult:
    """验收结果"""
    passed: bool
    coverage: Optional[int] = None
    compile_passed: Optional[bool] = None
    message: str = ""
    violations: List[ViolationRecord] = field(default_factory=list)
    summary: Optional[str] = None
    l1_result: Optional['AcceptanceResult'] = None
    l2_result: Optional['AcceptanceResult'] = None
    l3_result: Optional['AcceptanceResult'] = None


@dataclass
class L3ReviewRequest:
    """L3人工审查请求"""
    confirmation_id: str
    task_id: str
    timestamp: str
    status: str = "pending"


class AcceptanceError(Exception):
    """验收失败异常（L1阻断用）"""
    pass


def parse_coverage_output(output: str) -> Optional[int]:
    """解析pytest --cov输出，提取TOTAL覆盖率

    Args:
        output: pytest --cov --cov-report=term 的完整输出

    Returns:
        覆盖率百分比（整数），无覆盖率信息返回None
    """
    # 匹配 TOTAL 行的覆盖率
    # 格式：TOTAL    20    4    80%
    pattern = r'TOTAL\s+\d+\s+\d+\s+(\d+)%'
    match = re.search(pattern, output)

    if match:
        return int(match.group(1))

    return None


class L1Validator:
    """L1强制量化层验证器

    功能：
    - 覆盖率校验（≥80%）
    - 编译无报错校验
    - 不通过阻断流程
    """

    def __init__(self, coverage_threshold: int = 80, code_path: str = "."):
        self.coverage_threshold = coverage_threshold
        self.code_path = code_path

    def check_coverage(self) -> AcceptanceResult:
        """检查覆盖率"""
        passed, coverage, message = self.run_coverage_check()
        return AcceptanceResult(
            passed=passed,
            coverage=coverage,
            message=message
        )

    def run_coverage_check(self) -> Tuple[bool, Optional[int], str]:
        """执行覆盖率检查

        Returns:
            (是否通过, 覆盖率, 消息)
        """
        try:
            result = subprocess.run(
                ["pytest", "--cov", "--cov-report=term", "-q"],
                cwd=self.code_path,
                capture_output=True,
                text=True,
                timeout=120
            )

            output = result.stdout + result.stderr
            coverage = parse_coverage_output(output)

            if coverage is None:
                return (False, None, "无法解析覆盖率输出")

            passed = coverage >= self.coverage_threshold
            message = f"覆盖率 {coverage}%（阈值 {self.coverage_threshold}%）"

            return (passed, coverage, message)

        except subprocess.TimeoutExpired:
            return (False, None, "覆盖率检查超时")
        except Exception as e:
            return (False, None, f"覆盖率检查异常: {str(e)}")

    def check_compile(self) -> AcceptanceResult:
        """检查编译"""
        passed, message = self.run_compile_check()
        return AcceptanceResult(
            passed=passed,
            compile_passed=passed,
            message=message
        )

    def run_compile_check(self) -> Tuple[bool, str]:
        """执行编译检查（pytest执行作为编译校验）

        Returns:
            (是否通过, 消息)
        """
        try:
            result = subprocess.run(
                ["pytest", "--collect-only", "-q"],
                cwd=self.code_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return (True, "编译检查通过")
            else:
                return (False, result.stderr or "编译检查失败")

        except subprocess.TimeoutExpired:
            return (False, "编译检查超时")
        except Exception as e:
            return (False, f"编译检查异常: {str(e)}")

    def validate(self) -> AcceptanceResult:
        """完整L1校验

        流程：
        1. 覆盖率检查（阻断）
        2. 编译检查（阻断）

        Returns:
            AcceptanceResult，任一失败即阻断
        """
        # 先检查覆盖率
        coverage_result = self.check_coverage()
        if not coverage_result.passed:
            coverage_result.compile_passed = False
            return coverage_result

        # 再检查编译
        compile_result = self.check_compile()
        if not compile_result.passed:
            # 编译失败，合并结果
            return AcceptanceResult(
                passed=False,
                coverage=coverage_result.coverage,
                compile_passed=False,
                message=compile_result.message
            )

        # 全部通过
        return AcceptanceResult(
            passed=True,
            coverage=coverage_result.coverage,
            compile_passed=True,
            message="L1强制量化层通过",
            summary=f"覆盖率 {coverage_result.coverage}%, 编译通过"
        )


class L2Validator:
    """L2半量化层命名规范检测器

    功能：
    - 驼峰命名检测（函数）
    - 蛇形命名检测（变量）
    - 类前缀检测
    - 返回违规清单（非阻断）
    """

    def __init__(self, required_prefix: Optional[str] = None):
        self.required_prefix = required_prefix

    def check_naming(self, code: str) -> List[ViolationRecord]:
        """检查命名规范

        Args:
            code: Python源代码字符串

        Returns:
            违规清单（非阻断）
        """
        violations = []
        lines = code.split('\n')

        for i, line in enumerate(lines, start=1):
            # 检查函数命名（应使用snake_case，驼峰命名违规）
            func_match = re.match(r'def\s+(\w+)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)
                # 检测驼峰命名作为违规
                if self._is_camel_case(func_name):
                    violations.append(ViolationRecord(
                        rule="camel_case",
                        line=i,
                        message=f"函数 '{func_name}' 使用驼峰命名，应改为snake_case"
                    ))

            # 检查类前缀
            class_match = re.match(r'class\s+(\w+)', line)
            if class_match and self.required_prefix:
                class_name = class_match.group(1)
                if not class_name.startswith(self.required_prefix):
                    violations.append(ViolationRecord(
                        rule="class_prefix",
                        line=i,
                        message=f"类 '{class_name}' 缺少前缀 '{self.required_prefix}'"
                    ))

        return violations

    def _is_camel_case(self, name: str) -> bool:
        """检查是否是驼峰命名

        驼峰命名特征：
        - 包含大小写混合（如 getUserInfo）
        - 不包含下划线
        """
        # 私有函数（以_开头）跳过
        if name.startswith('_'):
            return False

        # 检测camelCase：包含大小写混合且无下划线
        has_uppercase = any(c.isupper() for c in name)
        has_lowercase = any(c.islower() for c in name)
        has_underscore = '_' in name

        return has_uppercase and has_lowercase and not has_underscore

    def validate(self, code_path: str) -> AcceptanceResult:
        """执行L2校验

        Args:
            code_path: 代码路径

        Returns:
            AcceptanceResult（非阻断）
        """
        violations = []

        # 遍历代码目录检查
        for root, dirs, files in os.walk(code_path):
            # 排除隐藏目录和虚拟环境
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.venv']

            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r') as f:
                            code = f.read()
                            file_violations = self.check_naming(code)
                            violations.extend(file_violations)
                    except Exception:
                        pass

        # L2非阻断，总是返回passed=True
        return AcceptanceResult(
            passed=True,
            violations=violations,
            message=f"检测完成，发现 {len(violations)} 个命名规范问题",
            summary=f"命名规范检测：{len(violations)} 个违规（非阻断）"
        )


class L3Validator:
    """L3纯人工层入口

    功能：
    - 手动触发接口
    - 仅归档不自动化
    - 返回人工确认ID
    """

    def __init__(self, archive_dir: Optional[str] = None):
        self.archive_dir = archive_dir or "archives/l3_reviews"
        self._pending_requests: dict = {}

    def request_manual_review(self, task_id: str) -> L3ReviewRequest:
        """请求人工审查

        Args:
            task_id: 任务ID

        Returns:
            L3ReviewRequest，包含确认ID
        """
        confirmation_id = f"L3-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()

        request = L3ReviewRequest(
            confirmation_id=confirmation_id,
            task_id=task_id,
            timestamp=timestamp,
            status="pending"
        )

        # 归档记录
        self._archive_review_request(request)

        return request

    def archive_review_request(self, request: L3ReviewRequest) -> None:
        """归档审查请求"""
        self._archive_review_request(request)

    def _archive_review_request(self, request: L3ReviewRequest) -> None:
        """内部归档实现"""
        self._pending_requests[request.confirmation_id] = request

        # 如果有归档目录，写入文件
        if self.archive_dir:
            os.makedirs(self.archive_dir, exist_ok=True)
            archive_file = os.path.join(
                self.archive_dir,
                f"{request.confirmation_id}.json"
            )
            import json
            with open(archive_file, 'w') as f:
                json.dump({
                    "confirmation_id": request.confirmation_id,
                    "task_id": request.task_id,
                    "timestamp": request.timestamp,
                    "status": request.status
                }, f)

    def validate(self, task_id: str) -> AcceptanceResult:
        """L3校验（仅归档）"""
        request = self.request_manual_review(task_id)

        return AcceptanceResult(
            passed=True,  # L3不阻断
            message=f"人工审查请求已归档",
            summary=f"确认ID: {request.confirmation_id}",
            l3_result=request
        )


class AcceptanceManager:
    """验收管理器

    协调L1/L2/L3三层校验
    """

    def __init__(
        self,
        coverage_threshold: int = 80,
        code_path: str = ".",
        class_prefix: Optional[str] = None,
        archive_dir: Optional[str] = None
    ):
        self.l1_validator = L1Validator(
            coverage_threshold=coverage_threshold,
            code_path=code_path
        )
        self.l2_validator = L2Validator(required_prefix=class_prefix)
        self.l3_validator = L3Validator(archive_dir=archive_dir)

    def run_validation(
        self,
        code_path: str,
        run_l1: bool = True,
        run_l2: bool = True,
        run_l3: bool = False,
        task_id: Optional[str] = None
    ) -> AcceptanceResult:
        """执行验收

        Args:
            code_path: 代码路径
            run_l1: 是否执行L1
            run_l2: 是否执行L2
            run_l3: 是否执行L3
            task_id: 任务ID（L3需要）

        Returns:
            AcceptanceResult
        """
        l1_result = None
        l2_result = None
        l3_result = None

        # L1强制执行
        if run_l1:
            self.l1_validator.code_path = code_path
            l1_result = self.l1_validator.validate()

            # L1失败阻断流程
            if not l1_result.passed:
                return AcceptanceResult(
                    passed=False,
                    coverage=l1_result.coverage,
                    compile_passed=l1_result.compile_passed,
                    message=l1_result.message,
                    summary=f"L1校验失败: {l1_result.message}",
                    l1_result=l1_result
                )

        # L2半量化执行（L1通过后）
        if run_l2:
            l2_result = self.l2_validator.validate(code_path)

        # L3人工入口（可选）
        if run_l3 and task_id:
            l3_result = self.l3_validator.validate(task_id)

        # 生成综合报告
        summary_parts = []
        if l1_result and l1_result.passed:
            summary_parts.append(f"L1通过: 覆盖率 {l1_result.coverage}%")
        if l2_result:
            summary_parts.append(f"L2检测: {len(l2_result.violations)} 个违规")
        if l3_result:
            summary_parts.append(f"L3归档: {l3_result.summary}")

        return AcceptanceResult(
            passed=True,
            coverage=l1_result.coverage if l1_result else None,
            compile_passed=l1_result.compile_passed if l1_result else None,
            violations=l2_result.violations if l2_result else [],
            message="验收完成",
            summary=" | ".join(summary_parts),
            l1_result=l1_result,
            l2_result=l2_result,
            l3_result=l3_result
        )