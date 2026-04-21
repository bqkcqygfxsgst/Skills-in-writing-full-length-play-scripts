#!/usr/bin/env python3
"""
DramaWorkflow — 完整工作流演示
展示从 /start → /outline → /plan → /write 的端到端工作流

用法:
  python scripts/drama_workflow.py --demo              # 完整演示
  python scripts/drama_workflow.py --demo --steps 2   # 只演示前 2 步
  python scripts/drama_workflow.py --interactive       # 交互式工作流
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict

_repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(_repo_root / "scripts"))

# ─────────────────────────────────────────────
class DramaWorkflow:
    """完整工作流驱动"""

    def __init__(self):
        self.steps = [
            {
                "name": "/start",
                "description": "初始化项目：搜集素材，生成素材库",
                "command": "python3",
                "args": ["scripts/drama_search.py", "--demo"],
                "output": "output/反腐剧示例_素材库.md",
            },
            {
                "name": "/outline",
                "description": "生成大纲：结构规划，节拍设计",
                "command": "python3",
                "args": ["scripts/drama_outline.py", "--demo"],
                "output": "output/主旋律示例_全案大纲.md",
            },
            {
                "name": "/plan",
                "description": "场景规划：人物任务，权力路径（演示 - 留作下一步）",
                "command": "echo",
                "args": ["[/plan 步骤演示]"],
                "output": None,
            },
            {
                "name": "/write",
                "description": "具体写作：节拍扩写，场景对话（演示 - 留作下一步）",
                "command": "echo",
                "args": ["[/write 步骤演示]"],
                "output": None,
            },
        ]

    def run_step(self, step: Dict, verbose: bool = True) -> bool:
        """执行单个工作流步骤"""
        print(f"\n{'='*70}")
        print(f"  步骤 {step['name']}")
        print(f"  {step['description']}")
        print(f"{'='*70}\n")

        try:
            cmd = [step["command"]] + step["args"]
            result = subprocess.run(
                cmd,
                cwd=str(_repo_root),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.stdout:
                print(result.stdout)
            if result.stderr and "warning" not in result.stderr.lower():
                print(result.stderr)

            if result.returncode == 0 or "✅" in result.stdout:
                print(f"\n✅ {step['name']} 步骤完成！")
                if step["output"]:
                    output_path = _repo_root / step["output"]
                    if output_path.exists():
                        size = output_path.stat().st_size / 1024
                        print(f"   输出文件大小：{size:.1f} KB")
                return True
            else:
                print(f"\n⚠️  {step['name']} 步骤执行有误，继续演示...")
                return False
        except Exception as e:
            print(f"❌ 步骤执行失败：{str(e)}")
            return False

    def run_demo(self, max_steps: int = None) -> None:
        """运行完整演示"""
        print(f"\n{'='*70}")
        print(f"  🎬 Drama Genius v2.0 — 完整工作流演示")
        print(f"{'='*70}\n")

        print("📋 工作流步骤：\n")
        steps_to_run = self.steps[:max_steps] if max_steps else self.steps
        for i, step in enumerate(steps_to_run, 1):
            marker = "✓" if i <= 2 else "→"
            print(f"  {marker} {step['name']}: {step['description'][:40]}...")

        print(f"\n开始执行...\n")
        time.sleep(1)

        results = []
        for i, step in enumerate(steps_to_run, 1):
            results.append(self.run_step(step))
            if i < len(steps_to_run):
                print("\n按 Enter 继续下一步...", end="")
                try:
                    input()
                except:
                    time.sleep(1)

        # 总结
        self.print_summary(results, steps_to_run)

    def print_summary(self, results: List[bool], steps: List[Dict]) -> None:
        """打印工作流总结"""
        print(f"\n{'='*70}")
        print(f"  📊 工作流执行总结")
        print(f"{'='*70}\n")

        for i, (step, success) in enumerate(zip(steps, results), 1):
            status = "✅ 完成" if success else "⚠️  跳过"
            print(f"  {i}. [{status}] {step['name']}")
            if step["output"]:
                output_path = _repo_root / step["output"]
                if output_path.exists():
                    print(f"     → {step['output']}")

        print(f"\n{'─'*70}")
        print("\n🎯 下一步建议：\n")

        if all(results[:2]):
            print("  ✅ 完整的素材库 + 大纲已生成！")
            print("\n  可以继续：")
            print("    1. 查看输出文件，确认结构")
            print("    2. 调整和优化大纲内容")
            print("    3. 执行 '/plan [场次]' 进行场景规划")
            print("    4. 执行 '/write [场次]' 开始具体写作\n")

        print(f"{'─'*70}\n")

    def run_interactive(self) -> None:
        """交互式工作流"""
        print(f"\n🎭 Drama Genius v2.0 — 交互式工作流\n")

        # 获取用户输入
        print("请输入剧目信息：\n")
        drama_name = input("剧名 (default: 主旋律示例): ").strip() or "主旋律示例"
        main_theme = input("主要主题 (default: 弘扬社会主义核心价值观): ").strip() or "弘扬社会主义核心价值观"
        structure = input("幕数 (default: 4): ").strip()

        try:
            structure = int(structure) if structure else 4
        except ValueError:
            structure = 4

        print(f"\n✅ 确认信息：")
        print(f"   剧名：{drama_name}")
        print(f"   主题：{main_theme}")
        print(f"   幕数：{structure} 幕\n")

        # 搜索
        print("▸ 步骤 1：执行搜索...")
        subprocess.run(
            ["python3", "scripts/drama_search.py", "--search", drama_name, "--name", drama_name],
            cwd=str(_repo_root),
        )

        # 大纲
        print("\n▸ 步骤 2：生成大纲...")
        subprocess.run(
            [
                "python3",
                "scripts/drama_outline.py",
                "--drama",
                drama_name,
                "--theme",
                main_theme,
                "--structure",
                str(structure),
            ],
            cwd=str(_repo_root),
        )

        print("\n✅ 工作流完成！")


# ─────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    workflow = DramaWorkflow()

    if "--demo" in sys.argv:
        max_steps = None
        if "--steps" in sys.argv:
            try:
                idx = sys.argv.index("--steps")
                max_steps = int(sys.argv[idx + 1])
            except (ValueError, IndexError):
                pass
        workflow.run_demo(max_steps=max_steps)

    elif "--interactive" in sys.argv:
        workflow.run_interactive()

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
