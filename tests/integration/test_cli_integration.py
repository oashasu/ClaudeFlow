"""集成测试 - CLI完整命令流程

测试 CLI + TaskManager + Scheduler 协作
"""

import pytest
import tempfile
import os


class TestCliIntegration:
    """CLI集成测试"""

    def test_cli_create_list_show_flow(self):
        """测试：CLI创建-列出-查看流程"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建任务
            create_result = cli.run([
                "task", "create",
                "--name", "CLI集成测试",
                "--domain", "AT_支付域",
                "--priority", "高"
            ])

            assert create_result.success == True
            task_id = create_result.task_id

            # 列出任务
            list_result = cli.run(["task", "list"])

            assert list_result.success == True
            assert "CLI集成测试" in list_result.output

            # 查看任务详情
            show_result = cli.run(["task", "show", "--id", task_id])

            assert show_result.success == True
            assert "CLI集成测试" in show_result.output
            assert "AT_支付域" in show_result.output
            assert "高" in show_result.output

    def test_cli_status_all_flow(self):
        """测试：CLI全局状态查询"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建多个任务
            cli.run(["task", "create", "--name", "任务1", "--domain", "AT_支付域"])
            cli.run(["task", "create", "--name", "任务2", "--domain", "DA_订单域"])
            cli.run(["task", "create", "--name", "任务3", "--domain", "RA_报表域"])

            # 查询全局状态
            status_result = cli.run(["status", "--all"])

            assert status_result.success == True
            assert "任务总数: 3" in status_result.output
            assert "待执行: 3" in status_result.output

    def test_cli_status_task_flow(self):
        """测试：CLI指定任务状态查询"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建任务
            create_result = cli.run([
                "task", "create",
                "--name", "状态查询测试",
                "--domain", "AT_支付域"
            ])
            task_id = create_result.task_id

            # 查询任务状态
            status_result = cli.run(["status", "--task", task_id])

            assert status_result.success == True
            assert "任务状态" in status_result.output
            assert "整体状态: pending" in status_result.output

    def test_cli_error_handling(self):
        """测试：CLI错误处理"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 缺少参数
            result = cli.run(["task", "create", "--domain", "AT_支付域"])

            assert result.success == False
            assert "name" in result.error.lower()

            # 查看不存在任务
            result = cli.run(["task", "show", "--id", "nonexistent"])

            assert result.success == False
            assert "不存在" in result.error

    def test_cli_task_with_description(self):
        """测试：CLI创建带描述的任务"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建带描述的任务
            result = cli.run([
                "task", "create",
                "--name", "带描述任务",
                "--domain", "AT_支付域",
                "--description", "这是一个详细描述"
            ])

            assert result.success == True

            # 查看任务确认描述
            show_result = cli.run(["task", "show", "--id", result.task_id])

            assert show_result.success == True
            assert "详细描述" in show_result.output

    def test_cli_list_with_status_filter(self):
        """测试：CLI按状态过滤列表"""
        from claudeflow.cli import CliApp
        from claudeflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建任务
            cli.run(["task", "create", "--name", "任务A", "--domain", "AT_支付域"])
            task2 = cli.run(["task", "create", "--name", "任务B", "--domain", "DA_订单域"])

            # 使用CLI内部的TaskManager更新状态
            cli.task_manager.update_task(task2.task_id, status=TaskStatus.COMPLETED)

            # 按状态过滤
            result = cli.run(["task", "list", "--status", "pending"])

            assert result.success == True
            assert "任务A" in result.output
            assert "任务B" not in result.output


class TestCliResultFormat:
    """CLI结果格式集成测试"""

    def test_cli_output_format(self):
        """测试：CLI输出格式"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建任务
            result = cli.run([
                "task", "create",
                "--name", "格式测试",
                "--domain", "AT_支付域"
            ])

            assert result.success == True
            assert "任务创建成功" in result.output
            assert "任务ID:" in result.output
            assert "名称:" in result.output
            assert "领域:" in result.output

    def test_cli_empty_list_output(self):
        """测试：CLI空列表输出"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 无任务时列出
            result = cli.run(["task", "list"])

            assert result.success == True
            assert "无任务" in result.output


class TestCliFullWorkflow:
    """CLI完整工作流集成测试"""

    def test_cli_complete_task_workflow(self):
        """测试：CLI完整任务工作流"""
        from claudeflow.cli import CliApp
        from claudeflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 1. 创建任务
            create_result = cli.run([
                "task", "create",
                "--name", "完整流程任务",
                "--domain", "AT_支付域",
                "--priority", "高",
                "--description", "测试完整工作流"
            ])

            assert create_result.success == True
            task_id = create_result.task_id

            # 2. 查看初始状态
            status_result = cli.run(["status", "--task", task_id])
            assert "整体状态: pending" in status_result.output

            # 3. 使用CLI内部的Scheduler分配和推进
            cli.scheduler.assign_employee(task_id, "dev_001")

            # 4. 查看执行中状态
            status_result = cli.run(["status", "--task", task_id])
            assert "整体状态: running" in status_result.output

            # 5. 完成任务
            cli.scheduler.complete_task(task_id)

            # 6. 查看完成状态
            status_result = cli.run(["status", "--task", task_id])
            assert "整体状态: completed" in status_result.output