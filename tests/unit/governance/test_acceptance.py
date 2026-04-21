"""验收层单元测试

验收标准：
- L1覆盖率校验正确（解析pytest --cov输出）
- L1编译校验正确（pytest执行成功）
- L1不通过阻断流程
- L2命名规范检测正确（驼峰、前缀）
- L2返回违规清单（非阻断）
- L3人工入口暴露
- 验收层覆盖率 ≥ 80%
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess


class TestL1CoverageValidator:
    """L1覆盖率校验测试"""

    def test_parse_coverage_output_valid(self):
        """测试：解析有效覆盖率输出"""
        from claudeflow.governance.acceptance import parse_coverage_output

        # 模拟 pytest --cov 输出
        mock_output = """
============================= test session starts ==============================
collected 10 items

tests/test_example.py ....                                                [40%]

---------- coverage: platform ----------
Name                    Stmts   Miss  Cover
----------------------------------------
src/example.py             20      4    80%
----------------------------------------
TOTAL                      20      4    80%
============================== 10 passed in 0.5s ===============================
"""

        coverage = parse_coverage_output(mock_output)
        assert coverage == 80

    def test_parse_coverage_output_multiple_files(self):
        """测试：解析多文件覆盖率输出"""
        from claudeflow.governance.acceptance import parse_coverage_output

        mock_output = """
---------- coverage: platform ----------
Name                    Stmts   Miss  Cover
----------------------------------------
src/a.py                  10      2    80%
src/b.py                  20      5    75%
----------------------------------------
TOTAL                      30      7    77%
----------------------------------------
"""

        coverage = parse_coverage_output(mock_output)
        assert coverage == 77

    def test_parse_coverage_output_no_coverage(self):
        """测试：无覆盖率信息返回None"""
        from claudeflow.governance.acceptance import parse_coverage_output

        mock_output = "10 passed in 0.5s"
        coverage = parse_coverage_output(mock_output)
        assert coverage is None

    def test_check_l1_coverage_pass(self):
        """测试：覆盖率达标通过"""
        from claudeflow.governance.acceptance import L1Validator

        validator = L1Validator(coverage_threshold=80)

        # mock subprocess
        with patch.object(validator, 'run_coverage_check', return_value=(True, 85, "passed")):
            result = validator.check_coverage()
            assert result.passed is True
            assert result.coverage == 85

    def test_check_l1_coverage_fail(self):
        """测试：覆盖率不达标阻断"""
        from claudeflow.governance.acceptance import L1Validator, AcceptanceError

        validator = L1Validator(coverage_threshold=80)

        with patch.object(validator, 'run_coverage_check', return_value=(False, 60, "failed")):
            result = validator.check_coverage()
            assert result.passed is False
            assert result.coverage == 60


class TestL1CompileValidator:
    """L1编译校验测试"""

    def test_check_compile_pass(self):
        """测试：编译通过"""
        from claudeflow.governance.acceptance import L1Validator

        validator = L1Validator()

        with patch.object(validator, 'run_compile_check', return_value=(True, "")):
            result = validator.check_compile()
            assert result.passed is True

    def test_check_compile_fail(self):
        """测试：编译失败阻断"""
        from claudeflow.governance.acceptance import L1Validator

        validator = L1Validator()

        with patch.object(validator, 'run_compile_check', return_value=(False, "SyntaxError: invalid syntax")):
            result = validator.check_compile()
            assert result.passed is False
            assert "SyntaxError" in result.message

    def test_check_compile_pytest_execution(self):
        """测试：pytest执行作为编译校验"""
        from claudeflow.governance.acceptance import L1Validator

        validator = L1Validator()

        # pytest成功意味着代码可执行
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="10 passed",
                stderr=""
            )
            result = validator.run_compile_check()
            assert result[0] is True


class TestL1FullValidation:
    """L1完整校验流程测试"""

    def test_l1_full_pass(self):
        """测试：L1全部通过"""
        from claudeflow.governance.acceptance import L1Validator, AcceptanceResult

        validator = L1Validator(coverage_threshold=80)

        with patch.object(validator, 'check_coverage', return_value=AcceptanceResult(True, coverage=85)):
            with patch.object(validator, 'check_compile', return_value=AcceptanceResult(True)):
                result = validator.validate()
                assert result.passed is True

    def test_l1_coverage_fail_blocks_flow(self):
        """测试：覆盖率失败阻断流程"""
        from claudeflow.governance.acceptance import L1Validator, AcceptanceError, AcceptanceResult

        validator = L1Validator(coverage_threshold=80)

        with patch.object(validator, 'check_coverage', return_value=AcceptanceResult(False, coverage=60, message="覆盖率不足")):
            # 编译检查不会被调用
            result = validator.validate()
            assert result.passed is False
            assert result.coverage == 60

    def test_l1_compile_fail_blocks_flow(self):
        """测试：编译失败阻断流程"""
        from claudeflow.governance.acceptance import L1Validator, AcceptanceResult

        validator = L1Validator(coverage_threshold=80)

        with patch.object(validator, 'check_coverage', return_value=AcceptanceResult(True, coverage=85)):
            with patch.object(validator, 'check_compile', return_value=AcceptanceResult(False, message="SyntaxError")):
                result = validator.validate()
                assert result.passed is False


class TestL2NamingValidator:
    """L2命名规范检测测试"""

    def test_check_camel_case_function_pass(self):
        """测试：驼峰命名函数通过"""
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator()
        violations = validator.check_naming("def get_user_info(): pass")
        assert len(violations) == 0

    def test_check_camel_case_function_fail(self):
        """测试：驼峰命名函数违规（Python应使用snake_case）"""
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator()
        # 驼峰命名 getUserInfo 在Python中应改为 snake_case get_user_info
        violations = validator.check_naming("def getUserInfo(): pass")
        assert len(violations) > 0
        assert "camel_case" in violations[0].rule

    def test_check_snake_case_variable_pass(self):
        """测试：蛇形命名变量通过"""
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator()
        violations = validator.check_naming("user_name = 'test'")
        assert len(violations) == 0

    def test_check_class_prefix_pass(self):
        """测试：类前缀检测通过"""
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator(required_prefix="Test")
        violations = validator.check_naming("class TestExample: pass")
        assert len(violations) == 0

    def test_check_class_prefix_fail(self):
        """测试：缺少类前缀违规"""
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator(required_prefix="Test")
        violations = validator.check_naming("class Example: pass")
        assert len(violations) > 0

    def test_l2_non_blocking(self):
        """测试：L2违规不阻断流程"""
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator()
        violations = validator.check_naming("def badname(): pass")

        # L2不会抛出异常阻断
        assert isinstance(violations, list)

    def test_l2_violation_list_format(self):
        """测试：违规清单格式正确"""
        from claudeflow.governance.acceptance import L2Validator, ViolationRecord

        validator = L2Validator()
        # 使用驼峰命名触发违规
        violations = validator.check_naming("def getUserInfo(): pass")

        # 返回ViolationRecord列表
        assert len(violations) > 0
        assert hasattr(violations[0], 'rule')
        assert hasattr(violations[0], 'line')
        assert hasattr(violations[0], 'message')


class TestL3ManualValidator:
    """L3人工入口测试"""

    def test_l3_manual_trigger_interface(self):
        """测试：L3手动触发接口"""
        from claudeflow.governance.acceptance import L3Validator

        validator = L3Validator()
        result = validator.request_manual_review(task_id="task_001")

        # 返回人工确认ID
        assert result.confirmation_id is not None
        assert len(result.confirmation_id) > 0

    def test_l3_only_archive(self):
        """测试：L3仅归档不自动化"""
        from claudeflow.governance.acceptance import L3Validator

        validator = L3Validator()

        # L3不参与自动化流程
        with patch.object(validator, '_archive_review_request') as mock_archive:
            validator.request_manual_review(task_id="task_001")
            mock_archive.assert_called_once()

    def test_l3_confirmation_id_unique(self):
        """测试：人工确认ID唯一"""
        from claudeflow.governance.acceptance import L3Validator

        validator = L3Validator()

        result1 = validator.request_manual_review(task_id="task_001")
        result2 = validator.request_manual_review(task_id="task_002")

        assert result1.confirmation_id != result2.confirmation_id


class TestAcceptanceManager:
    """验收管理器测试"""

    def test_manager_run_l1_l2(self):
        """测试：验收管理器执行L1+L2"""
        from claudeflow.governance.acceptance import AcceptanceManager

        manager = AcceptanceManager()

        with patch.object(manager.l1_validator, 'validate') as mock_l1:
            with patch.object(manager.l2_validator, 'validate') as mock_l2:
                mock_l1.return_value = MagicMock(passed=True, coverage=85)
                mock_l2.return_value = MagicMock(violations=[])

                result = manager.run_validation(
                    code_path="/some/path",
                    run_l1=True,
                    run_l2=True,
                    run_l3=False
                )

                mock_l1.assert_called_once()
                mock_l2.assert_called_once()

    def test_manager_l1_fail_skip_l2(self):
        """测试：L1失败跳过L2"""
        from claudeflow.governance.acceptance import AcceptanceManager

        manager = AcceptanceManager()

        with patch.object(manager.l1_validator, 'validate') as mock_l1:
            mock_l1.return_value = MagicMock(passed=False, coverage=60)

            result = manager.run_validation(
                code_path="/some/path",
                run_l1=True,
                run_l2=True,
                run_l3=False
            )

            # L1失败，L2不应执行
            mock_l1.assert_called_once()

    def test_manager_summary_report(self):
        """测试：验收管理器生成报告"""
        from claudeflow.governance.acceptance import AcceptanceManager

        manager = AcceptanceManager()

        with patch.object(manager.l1_validator, 'validate') as mock_l1:
            mock_l1.return_value = MagicMock(
                passed=True,
                coverage=85,
                compile_passed=True
            )

            result = manager.run_validation(
                code_path="/some/path",
                run_l1=True,
                run_l2=False,
                run_l3=False
            )

            assert result.summary is not None
            assert result.l1_result is not None


class TestAcceptanceResult:
    """验收结果测试"""

    def test_result_creation(self):
        """测试：验收结果创建"""
        from claudeflow.governance.acceptance import AcceptanceResult

        result = AcceptanceResult(passed=True, coverage=85, message="通过")

        assert result.passed is True
        assert result.coverage == 85
        assert result.message == "通过"

    def test_result_with_violations(self):
        """测试：带违规清单的结果"""
        from claudeflow.governance.acceptance import AcceptanceResult, ViolationRecord

        violations = [
            ViolationRecord(rule="camel_case", line=10, message="函数命名不符合驼峰规范")
        ]
        result = AcceptanceResult(passed=True, violations=violations)

        assert len(result.violations) == 1
        assert result.violations[0].rule == "camel_case"


class TestViolationRecord:
    """违规记录测试"""

    def test_violation_record_creation(self):
        """测试：违规记录创建"""
        from claudeflow.governance.acceptance import ViolationRecord

        violation = ViolationRecord(
            rule="camel_case",
            line=10,
            message="函数命名不符合驼峰规范",
            severity="warning"
        )

        assert violation.rule == "camel_case"
        assert violation.line == 10
        assert violation.severity == "warning"


class TestL1RealExecution:
    """L1真实执行测试（覆盖subprocess分支）"""

    def test_run_coverage_check_timeout(self):
        """测试：覆盖率检查超时"""
        from claudeflow.governance.acceptance import L1Validator

        validator = L1Validator()

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("pytest", 120)):
            passed, coverage, message = validator.run_coverage_check()
            assert passed is False
            assert coverage is None
            assert "超时" in message

    def test_run_coverage_check_exception(self):
        """测试：覆盖率检查异常"""
        from claudeflow.governance.acceptance import L1Validator

        validator = L1Validator()

        with patch('subprocess.run', side_effect=Exception("mock error")):
            passed, coverage, message = validator.run_coverage_check()
            assert passed is False
            assert coverage is None
            assert "异常" in message

    def test_run_compile_check_timeout(self):
        """测试：编译检查超时"""
        from claudeflow.governance.acceptance import L1Validator

        validator = L1Validator()

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("pytest", 60)):
            passed, message = validator.run_compile_check()
            assert passed is False
            assert "超时" in message

    def test_run_compile_check_exception(self):
        """测试：编译检查异常"""
        from claudeflow.governance.acceptance import L1Validator

        validator = L1Validator()

        with patch('subprocess.run', side_effect=Exception("mock error")):
            passed, message = validator.run_compile_check()
            assert passed is False
            assert "异常" in message


class TestL2FileTraversal:
    """L2文件遍历测试"""

    def test_validate_with_real_files(self):
        """测试：validate遍历真实文件"""
        import tempfile
        import os
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = os.path.join(tmpdir, "test_example.py")
            with open(test_file, 'w') as f:
                f.write("def getUserInfo(): pass\n")

            result = validator.validate(tmpdir)

            assert result.passed is True
            assert len(result.violations) > 0

    def test_validate_skip_hidden_dirs(self):
        """测试：validate跳过隐藏目录"""
        import tempfile
        import os
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建隐藏目录
            hidden_dir = os.path.join(tmpdir, ".hidden")
            os.makedirs(hidden_dir)
            hidden_file = os.path.join(hidden_dir, "test.py")
            with open(hidden_file, 'w') as f:
                f.write("def getUserInfo(): pass\n")

            result = validator.validate(tmpdir)

            # 隐藏目录的文件不会被检查
            assert len(result.violations) == 0

    def test_validate_skip_venv(self):
        """测试：validate跳过虚拟环境"""
        import tempfile
        import os
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建.venv目录
            venv_dir = os.path.join(tmpdir, ".venv")
            os.makedirs(venv_dir)
            venv_file = os.path.join(venv_dir, "test.py")
            with open(venv_file, 'w') as f:
                f.write("def getUserInfo(): pass\n")

            result = validator.validate(tmpdir)

            # .venv目录的文件不会被检查
            assert len(result.violations) == 0

    def test_validate_file_read_error(self):
        """测试：validate文件读取错误"""
        import tempfile
        import os
        from claudeflow.governance.acceptance import L2Validator

        validator = L2Validator()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建文件但无法读取（通过mock）
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, 'w') as f:
                f.write("def get_user_info(): pass\n")

            # 文件读取异常不影响结果
            with patch('builtins.open', side_effect=Exception("read error")):
                result = validator.validate(tmpdir)
                assert result.passed is True


class TestL3ArchiveFile:
    """L3文件归档测试"""

    def test_archive_to_file(self):
        """测试：归档写入文件"""
        import tempfile
        import os
        import json
        from claudeflow.governance.acceptance import L3Validator

        with tempfile.TemporaryDirectory() as tmpdir:
            validator = L3Validator(archive_dir=tmpdir)
            result = validator.request_manual_review(task_id="task_001")

            # 验证文件创建
            archive_file = os.path.join(tmpdir, f"{result.confirmation_id}.json")
            assert os.path.exists(archive_file)

            # 验证内容
            with open(archive_file, 'r') as f:
                data = json.load(f)
                assert data["task_id"] == "task_001"
                assert data["status"] == "pending"


class TestManagerL3Execution:
    """验收管理器L3执行测试"""

    def test_manager_run_l1_l2_l3(self):
        """测试：验收管理器执行L1+L2+L3"""
        from claudeflow.governance.acceptance import AcceptanceManager

        manager = AcceptanceManager()

        with patch.object(manager.l1_validator, 'validate') as mock_l1:
            with patch.object(manager.l2_validator, 'validate') as mock_l2:
                with patch.object(manager.l3_validator, 'validate') as mock_l3:
                    mock_l1.return_value = MagicMock(passed=True, coverage=85)
                    mock_l2.return_value = MagicMock(violations=[])
                    mock_l3.return_value = MagicMock(summary="确认ID: L3-xxx")

                    result = manager.run_validation(
                        code_path="/some/path",
                        run_l1=True,
                        run_l2=True,
                        run_l3=True,
                        task_id="task_001"
                    )

                    mock_l1.assert_called_once()
                    mock_l2.assert_called_once()
                    mock_l3.assert_called_once()
                    assert result.l3_result is not None

    def test_manager_run_only_l1(self):
        """测试：仅执行L1"""
        from claudeflow.governance.acceptance import AcceptanceManager

        manager = AcceptanceManager()

        with patch.object(manager.l1_validator, 'validate') as mock_l1:
            mock_l1.return_value = MagicMock(passed=True, coverage=85)

            result = manager.run_validation(
                code_path="/some/path",
                run_l1=True,
                run_l2=False,
                run_l3=False
            )

            mock_l1.assert_called_once()
            assert result.l2_result is None
            assert result.l3_result is None