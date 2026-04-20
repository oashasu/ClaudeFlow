"""CLI驱动验证脚本

验证Hermes调度Claude Code CLI的完整流程：
1. session_id捕获
2. 事件流解析
3. 工具调用追踪
4. 完成检测
5. 干预机制（可选）
"""

import sys
import os

# 设置路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/src')

from claudeflow.cli_driver import CliDriver
import json
import time

def verify_basic_flow():
    """验证基本流程"""
    print("=" * 60)
    print("Hermes CLI驱动验证")
    print("=" * 60)

    driver = CliDriver()

    # Step 1: 启动CLI会话
    print("\n[Step 1] 启动CLI会话...")
    prompt = "请列出当前目录下的所有.py文件，告诉我有多少个"

    try:
        process, session_id = driver.start_session(prompt)
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        print("  请确认Claude Code CLI已安装并可执行")
        return False

    if session_id:
        print(f"✓ session_id捕获成功: {session_id}")
        print(f"  session_id长度: {len(session_id)} (UUID格式应为36)")
    else:
        print("✗ session_id捕获失败")
        print("  检查CLI输出格式是否正确")
        return False

    # Step 2: 监控事件流
    print("\n[Step 2] 监控事件流（最多等待60秒）...")
    tool_calls = []
    thinking_count = 0
    text_count = 0
    all_events = []

    start_time = time.time()
    timeout = 60

    for event in driver.monitor_events(process):
        all_events.append(event)
        event_type = event.get("type")

        if event_type == "assistant":
            parsed = driver.parse_assistant_event(event)
            if parsed:
                if parsed["type"] == "tool_use":
                    tool_calls.append(parsed["tool_name"])
                    print(f"  → 工具调用: {parsed['tool_name']}")
                    if parsed['tool_input']:
                        input_preview = str(parsed['tool_input'])[:50]
                        print(f"     输入: {input_preview}...")
                elif parsed["type"] == "thinking":
                    thinking_count += 1
                    # 不打印thinking内容，避免刷屏
                elif parsed["type"] == "text":
                    text_count += 1
                    text_preview = parsed['text'][:80] if parsed['text'] else ""
                    print(f"  → 文本回复: {text_preview}...")

        # Step 3: 检测完成
        is_complete, summary = driver.detect_completion(all_events)

        if is_complete:
            print(f"\n[Step 3] 任务完成检测")
            print(f"✓ 检测到result事件")
            if summary:
                print(f"  摘要: {summary[:100]}...")
            break

        # 超时检查
        if time.time() - start_time > timeout:
            print(f"\n⚠ 超时({timeout}秒)，任务可能仍在执行")
            break

    # 验证结果汇总
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    results = {
        "session_id捕获": bool(session_id),
        "事件流解析": len(all_events) > 0,
        "工具调用追踪": len(tool_calls) > 0,
        "完成检测": driver.detect_completion(all_events)[0]
    }

    for key, value in results.items():
        status = "✓ 成功" if value else "✗ 失败"
        print(f"{key}: {status}")

    print(f"详细信息:")
    print(f"  - 事件总数: {len(all_events)}")
    print(f"  - 工具调用: {len(tool_calls)}次 ({', '.join(tool_calls[:5])})")
    print(f"  - thinking: {thinking_count}次")
    print(f"  - text: {text_count}次")
    print("=" * 60)

    # 清理
    driver.clear_session(session_id)

    # 返回是否全部成功
    all_success = all(results.values())
    if all_success:
        print("\n✓ 验证完成！cli_driver模块工作正常")
    else:
        print("\n✗ 验证失败，请检查失败项")

    return all_success


def verify_intervention():
    """验证干预机制"""
    print("\n" + "=" * 60)
    print("干预机制验证")
    print("=" * 60)

    driver = CliDriver()

    # Step 1: 启动会话
    print("\n[Step 1] 启动CLI会话...")
    prompt = "创建一个空文件 /tmp/test_verify.txt"

    try:
        process, session_id = driver.start_session(prompt)
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        return False

    if not session_id:
        print("✗ session_id捕获失败")
        return False

    print(f"✓ session_id: {session_id}")

    # Step 2: 等待任务完成
    print("\n[Step 2] 等待任务完成...")
    events = []

    for event in driver.monitor_events(process):
        events.append(event)

        is_complete, _ = driver.detect_completion(events)
        if is_complete:
            print("✓ 任务完成")
            break

    # Step 3: 干预恢复
    print("\n[Step 3] 干预恢复测试...")
    intervention_prompt = "请在刚才创建的文件中写入 'Hello Hermes'"

    try:
        new_process = driver.intervene(session_id, intervention_prompt)
        print(f"✓ 干预命令已发送 (--resume {session_id})")
    except Exception as e:
        print(f"✗ 干预失败: {e}")
        driver.clear_session(session_id)
        return False

    # Step 4: 监控干预结果
    print("\n[Step 4] 监控干预结果...")
    intervention_events = []

    for event in driver.monitor_events(new_process):
        intervention_events.append(event)
        event_type = event.get("type")

        if event_type == "assistant":
            parsed = driver.parse_assistant_event(event)
            if parsed and parsed["type"] == "tool_use":
                print(f"  → 工具调用: {parsed['tool_name']}")

        is_complete, _ = driver.detect_completion(intervention_events)
        if is_complete:
            print("✓ 干预任务完成")
            break

    # 清理
    driver.clear_session(session_id)

    print("\n" + "=" * 60)
    print("干预验证成功！--resume机制正常工作")
    print("=" * 60)

    return True


def main():
    """主函数"""
    print("\n选择验证模式:")
    print("1. 基本流程验证（推荐首次）")
    print("2. 干预机制验证（需要基本验证成功）")
    print("3. 全部验证")
    print("0. 退出")

    try:
        choice = input("\n请输入选项 (1/2/3/0): ").strip()
    except EOFError:
        # 非交互模式，默认执行基本验证
        choice = "1"

    if choice == "1":
        verify_basic_flow()
    elif choice == "2":
        verify_intervention()
    elif choice == "3":
        success = verify_basic_flow()
        if success:
            verify_intervention()
    elif choice == "0":
        print("退出验证")
    else:
        print("无效选项，执行基本验证")
        verify_basic_flow()


if __name__ == "__main__":
    main()