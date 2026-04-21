#!/usr/bin/env python3
"""
DramaSearchExa — MCP Exa AI 搜索增强模块
为 drama_search.py 添加高质量英文搜索支持

用法:
  # 作为 drama_search.py 的增强源
  python scripts/drama_search_exa.py --search "anti-corruption drama" --type english

文档：https://exa.ai/docs
MCP 集成：通过 agent-reach 的 mcporter 调用
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# ─────────────────────────────────────────────
class ExaSearchAdapter:
    """Exa AI 搜索适配器（MCP 集成）"""

    def __init__(self):
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        """
        检查 MCP / mcporter 是否可用
        """
        try:
            # 尝试导入 mcporter 或相关 MCP 工具
            import subprocess
            result = subprocess.run(
                ["which", "mcporter"],
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def search_exa(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        调用 Exa AI 搜索（通过 MCP）
        
        Exa 擅长：
        - 高质量英文内容
        - 学术论文、新闻、技术文档
        - 自然语言查询支持
        """
        if not self.available:
            print("⚠️  MCP/mcporter 不可用，跳过 Exa 搜索")
            print("   安装方式：https://github.com/Panniantong/Agent-Reach")
            return []

        try:
            import subprocess
            
            # 通过 mcporter 调用 Exa API
            # 格式：mcporter call 'exa.web_search_exa(query: "...", numResults: 5)'
            mcporter_call = f'exa.web_search_exa(query: "{query}", numResults: {num_results})'
            
            result = subprocess.run(
                ["mcporter", "call", mcporter_call],
                capture_output=True,
                text=True,
                timeout=15,
            )
            
            if result.returncode == 0:
                # 解析结果（JSON 格式）
                import json
                try:
                    data = json.loads(result.stdout)
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "source": "Exa AI",
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("text", "")[:200],
                            "published": item.get("publishedDate", ""),
                            "score": item.get("score", 0),
                        })
                    return results
                except json.JSONDecodeError:
                    print("⚠️  Exa 结果解析失败")
                    return []
            else:
                print(f"⚠️  Exa API 返回错误：{result.stderr[:100]}")
                return []
                
        except Exception as e:
            print(f"⚠️  Exa 搜索异常：{str(e)}")
            return []

    def get_code_context(self, query: str, tokens: int = 3000) -> str:
        """
        Exa 的代码上下文搜索功能（针对编剧技术文档）
        """
        if not self.available:
            return ""

        try:
            import subprocess
            
            mcporter_call = f'exa.get_code_context_exa(query: "{query}", tokensNum: {tokens})'
            result = subprocess.run(
                ["mcporter", "call", mcporter_call],
                capture_output=True,
                text=True,
                timeout=15,
            )
            
            if result.returncode == 0:
                return result.stdout
            return ""
        except Exception:
            return ""

    def search_with_fallback(
        self,
        query: str,
        fallback_func=None,
    ) -> List[Dict]:
        """
        Exa 主搜索，失败时回退到其他源
        """
        results = self.search_exa(query)
        if not results and fallback_func:
            print("⚠️  Exa 搜索无结果，使用备用源...")
            return fallback_func(query)
        return results


# ─────────────────────────────────────────────
def demo_exa_integration():
    """演示 Exa 集成"""
    print("\n🔍 Exa AI 搜索集成演示\n")

    adapter = ExaSearchAdapter()

    if adapter.available:
        print("✅ MCP/mcporter 可用\n")
        print("📝 示例调用：\n")
        print('  mcporter call \'exa.web_search_exa(query: "anti-corruption drama theory", numResults: 5)\'')
        print("\n✅ Exa 集成已激活！")
    else:
        print("❌ MCP/mcporter 未安装\n")
        print("📝 安装步骤：\n")
        print("  1. 克隆 Agent-Reach：")
        print("     git clone https://github.com/Panniantong/Agent-Reach.git")
        print("\n  2. 安装依赖：")
        print("     pip install mcporter")
        print("\n  3. 配置 MCP 服务器")
        print("\n  4. 验证安装：")
        print("     mcporter list_servers")
        print("\n📖 详见：https://github.com/Panniantong/Agent-Reach\n")


# ─────────────────────────────────────────────
def main():
    if "--demo" in sys.argv:
        demo_exa_integration()
    elif "--check" in sys.argv:
        adapter = ExaSearchAdapter()
        if adapter.available:
            print("✅ Exa 搜索模块已就绪")
        else:
            print("⚠️  Exa 搜索模块需要配置")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
