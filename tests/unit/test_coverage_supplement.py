"""CLI覆盖率补充测试

测试 main() 入口和异常处理分支
"""

import pytest
import tempfile
import os


class TestCliMain:
    """CLI main()入口测试"""

    def test_cli_main_success(self):
        """测试：main()成功执行"""
        from claudeflow.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            # 设置环境变量
            os.environ["CLAUDFLOW_TASKS_DIR"] = tmpdir

            # 模拟sys.argv
            import sys
            old_argv = sys.argv
            sys.argv = ["claudflow", "task", "list"]

            try:
                # main()在成功时不应抛出异常
                main()
            finally:
                sys.argv = old_argv
                del os.environ["CLAUDFLOW_TASKS_DIR"]

    def test_cli_main_with_error(self, capsys):
        """测试：main()错误处理"""
        from claudeflow.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["CLAUDFLOW_TASKS_DIR"] = tmpdir

            import sys
            old_argv = sys.argv
            sys.argv = ["claudflow", "task", "show", "--id", "nonexistent"]

            try:
                # 应该抛出SystemExit
                with pytest.raises(SystemExit):
                    main()
            finally:
                sys.argv = old_argv
                del os.environ["CLAUDFLOW_TASKS_DIR"]


class TestCliArgparseError:
    """CLI argparse错误测试"""

    def test_cli_argparse_invalid_command(self):
        """测试：无效命令参数解析失败"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 无效命令会触发SystemExit，被捕获后返回错误
            # argparse在没有command时会有默认行为
            result = cli.run([])  # 无参数

            # 应该有输出（显示help或错误）
            assert result is not None


class TestCheckpointErrorBranches:
    """Checkpoint异常分支测试"""

    def test_checkpoint_invalid_json_file(self):
        """测试：无效JSON文件处理"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            # 创建一个无效的JSON文件
            invalid_file = os.path.join(checkpoint_dir, "invalid.json")
            with open(invalid_file, 'w') as f:
                f.write("{invalid json content}")

            # 列出快照时应该忽略无效文件
            checkpoints = cm.list_checkpoints()
            assert checkpoints == []

    def test_checkpoint_missing_fields_json(self):
        """测试：缺失字段的JSON文件处理"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            # 创建一个缺失必需字段的JSON文件
            invalid_file = os.path.join(checkpoint_dir, "missing_fields.json")
            with open(invalid_file, 'w') as f:
                f.write("{\"checkpoint_id\": \"cp_001\"}")  # 缺失其他字段

            # 列出快照时应该忽略无效文件
            checkpoints = cm.list_checkpoints()
            assert checkpoints == []


class TestTaskManagerDuplicateName:
    """TaskManager重复名称测试"""

    def test_task_manager_duplicate_name_branch(self):
        """测试：任务目录名重复分支"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            # 创建同名任务触发重复分支
            task1 = tm.create_task(name="重复任务", domain="AT_支付域")
            task2 = tm.create_task(name="重复任务", domain="AT_支付域")

            # 验证第二个任务ID不同
            assert task1.id != task2.id
            # 验证目录名加了后缀
            assert task1.task_dir_name != task2.task_dir_name