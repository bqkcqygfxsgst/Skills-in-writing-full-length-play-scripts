#!/usr/bin/env python3
"""
DramaSearch — 话剧素材搜索系统
支持多源搜索：Bocha API (中文) + Exa AI (英文) + 百度热搜爬虫

用法:
  python scripts/drama_search.py --search "反腐剧"              # 搜索关键词
  python scripts/drama_search.py --search "反腐剧" --type story  # 指定搜索类型
  python scripts/drama_search.py --search "反腐剧" --verbose    # 详细输出
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import urllib.parse

from openai import OpenAI
from dotenv import load_dotenv

# === 加载环境变量 ===
_repo_root = Path(__file__).parent.parent
load_dotenv(_repo_root / ".env")

# === 配置常量 ===
OUTPUT_DIR = _repo_root / "output"
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# 可选：Bocha API（中文搜索）
BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")
BOCHA_API_URL = "https://api.bochaai.com/v1/search"


# ─────────────────────────────────────────────
class DramaSearch:
    """话剧素材搜索核心类"""

    def __init__(self):
        self.llm_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 调用 Bocha API（中文搜索）──────────────────────
    def _search_bocha(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        调用 Bocha 搜索 API 获取中文搜索结果
        Bocha 是一个通用中文搜索 API，支持新闻、网页、微博等
        """
        if not BOCHA_API_KEY:
            print("⚠️  未配置 BOCHA_API_KEY，跳过 Bocha 搜索")
            return []

        try:
            import requests
        except ImportError:
            print("⚠️  未安装 requests，跳过 Bocha 搜索（pip install requests）")
            return []

        headers = {
            "Authorization": f"Bearer {BOCHA_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "count": num_results,
            "search_type": "general",  # 通用搜索
        }

        try:
            resp = requests.post(BOCHA_API_URL, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("results", []):
                    results.append({
                        "source": "Bocha",
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", "")[:200],  # 截断摘要
                        "published": item.get("date", ""),
                    })
                return results
            else:
                print(f"⚠️  Bocha API 返回错误：{resp.status_code}")
                return []
        except Exception as e:
            print(f"⚠️  Bocha 搜索失败：{str(e)}")
            return []

    # ── 调用 Exa AI（英文/技术搜索）──────────────────────
    def _search_exa(self, query: str, num_results: int = 3) -> List[Dict]:
        """
        使用 DashScope 的搜索能力（Exa 兼容）
        用于英文内容搜索
        """
        try:
            # 模拟 Exa API 调用（基于 DashScope 搜索能力）
            # 实际实现需要集成 mcporter 或直接调用 Exa API
            # 这里返回空列表，用户可配置实际搜索源
            return []
        except Exception as e:
            print(f"⚠️  Exa 搜索失败：{str(e)}")
            return []

    # ── 百度热搜爬虫（轻量级）──────────────────────
    def _search_baidu_trends(self, query: str, num_results: int = 3) -> List[Dict]:
        """
        从百度热搜获取热门话题
        注：这是一个轻量级爬虫示例，实际使用需要处理反爬虫
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            print("⚠️  未安装 requests 或 beautifulsoup4，跳过百度爬虫")
            return []

        try:
            # 百度搜索 URL
            url = f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            }
            resp = requests.get(url, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "html.parser")
                results = []
                
                # 提取搜索结果（简单示例）
                for item in soup.select(".result")[:num_results]:
                    title_elem = item.select_one("h3 a")
                    if title_elem:
                        results.append({
                            "source": "Baidu",
                            "title": title_elem.get_text(strip=True),
                            "url": title_elem.get("href", ""),
                            "snippet": item.select_one(".c-abstract") and 
                                      item.select_one(".c-abstract").get_text(strip=True)[:200] or "",
                            "published": "",
                        })
                return results
            return []
        except Exception as e:
            print(f"⚠️  百度搜索失败：{str(e)}")
            return []

    # ── 关键冲突点提取 ──────────────────────
    def _extract_conflicts(self, materials: List[str]) -> List[str]:
        """
        使用 LLM 从素材中提取 3 个核心冲突点
        """
        if not materials:
            return []

        material_text = "\n".join(materials[:3])  # 只使用前 3 条素材
        prompt = f"""
你是一位资深编剧。请从以下真实素材中提取**3个核心戏剧冲突点**，每个冲突点用一句话表达：

素材：
{material_text}

要求：
1. 冲突点必须具有戏剧张力（对立、矛盾、困境）
2. 必须来自素材本身，不要凭空编造
3. 按冲突强度从高到低排序

输出格式（仅返回冲突点，不要前缀）：
1. [冲突点1]
2. [冲突点2]
3. [冲突点3]
"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            text = resp.choices[0].message.content
            # 提取冲突点
            conflicts = []
            for line in text.split("\n"):
                line = line.strip()
                if line and re.match(r"^\d+\.", line):
                    conflict = re.sub(r"^\d+\.\s*", "", line).strip()
                    if conflict:
                        conflicts.append(conflict)
            return conflicts[:3]
        except Exception as e:
            print(f"⚠️  冲突点提取失败：{str(e)}")
            return []

    # ── 人物心理动机提取 ──────────────────────
    def _extract_character_motives(self, materials: List[str]) -> Dict[str, str]:
        """
        从素材中推导出潜在人物的心理动机
        """
        if not materials:
            return {}

        material_text = "\n".join(materials[:3])
        prompt = f"""
你是一位资深编剧。基于以下素材，推导出**3-5个主要人物**及其**核心心理动机**（而非表面动机）：

素材：
{material_text}

要求：
1. 人物必须是该现实事件中的真实角色或角色原型
2. 心理动机指的是人物的内心欲望/恐惧/执念，不是表面行为
3. 格式简洁（每人一句话）

输出格式（仅返回，不加分析）：
- [人物1]：[心理动机]
- [人物2]：[心理动机]
"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
            )
            text = resp.choices[0].message.content
            motives = {}
            for line in text.split("\n"):
                line = line.strip()
                if "：" in line:
                    parts = line.split("：", 1)
                    person = re.sub(r"^[-•]\s*", "", parts[0]).strip()
                    motive = parts[1].strip()
                    if person and motive:
                        motives[person] = motive
            return motives
        except Exception as e:
            print(f"⚠️  人物动机提取失败：{str(e)}")
            return {}

    # ── 可舞台化动作瞬间 ──────────────────────
    def _extract_stage_moments(self, materials: List[str]) -> List[str]:
        """
        从素材中提取 5 个可舞台化的动作瞬间
        """
        if not materials:
            return []

        material_text = "\n".join(materials[:3])
        prompt = f"""
你是一位舞台导演。从以下素材中提取**5个最具舞台张力的动作瞬间**，每个瞬间用一句话描述：

素材：
{material_text}

要求：
1. 动作必须具有视觉冲击力（可被观众看到）
2. 每个动作必须暴露人物的心理状态
3. 不要描述内心感受，只描述可见的动作
4. 格式：[人物] + [具体动作] + [暗示的心理]

输出格式（仅返回动作，不加编号）：
- 
- 
- 
"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            text = resp.choices[0].message.content
            moments = []
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    moment = line.lstrip("-").strip()
                    if moment:
                        moments.append(moment)
            return moments[:5]
        except Exception as e:
            print(f"⚠️  动作瞬间提取失败：{str(e)}")
            return []

    # ── 主搜索函数 ──────────────────────
    def search(self, query: str, verbose: bool = False) -> Dict:
        """
        综合搜索：多源收集 + 智能提取
        """
        print(f"\n🔍 开始搜索：「{query}」\n")

        # 1. 多源搜索
        all_materials = []

        print("  ▸ 启动 Bocha 搜索（中文）...")
        bocha_results = self._search_bocha(query, num_results=5)
        all_materials.extend([r["snippet"] for r in bocha_results if r.get("snippet")])
        if bocha_results:
            print(f"    ✓ 找到 {len(bocha_results)} 条Bocha结果")
            for r in bocha_results[:3]:
                if verbose:
                    print(f"      • {r['title'][:50]}")

        print("  ▸ 启动百度热搜爬虫...")
        baidu_results = self._search_baidu_trends(query, num_results=3)
        all_materials.extend([r["snippet"] for r in baidu_results if r.get("snippet")])
        if baidu_results:
            print(f"    ✓ 找到 {len(baidu_results)} 条百度结果")

        if not all_materials:
            print("❌ 未找到任何搜索结果，请检查网络或API配置")
            return {"success": False, "error": "No materials found"}

        print(f"\n  ✓ 共收集 {len(all_materials)} 条素材\n")

        # 2. 智能提取
        print("  ▸ 提取核心冲突点...")
        conflicts = self._extract_conflicts(all_materials)
        if conflicts:
            print(f"    ✓ 提取 {len(conflicts)} 个冲突点")

        print("  ▸ 提取人物心理动机...")
        motives = self._extract_character_motives(all_materials)
        if motives:
            print(f"    ✓ 识别 {len(motives)} 个人物")

        print("  ▸ 提取可舞台化动作...")
        moments = self._extract_stage_moments(all_materials)
        if moments:
            print(f"    ✓ 提取 {len(moments)} 个动作瞬间\n")

        # 3. 生成结果
        result = {
            "success": True,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "materials": {
                "bocha": bocha_results,
                "baidu": baidu_results,
            },
            "extraction": {
                "conflicts": conflicts,
                "character_motives": motives,
                "stage_moments": moments,
            },
        }

        return result

    # ── 保存结果 ──────────────────────
    def save_result(self, result: Dict, drama_name: str) -> str:
        """
        保存搜索结果为 Markdown 文件
        """
        if not result.get("success"):
            return ""

        filename = OUTPUT_DIR / f"{drama_name}_素材库.md"
        
        md_content = f"""# {drama_name} — 素材库

**搜索时间**：{result['timestamp']}  
**搜索关键词**：{result['query']}

---

## 一、搜索素材来源

### Bocha 搜索结果 ({len(result['materials']['bocha'])} 条)

"""
        for i, item in enumerate(result['materials']['bocha'], 1):
            md_content += f"""
#### [{i}] {item.get('title', '')}

- **来源**：{item.get('source', '')}
- **链接**：[{item.get('url', '')[:80]}...]({item['url']})
- **摘要**：{item.get('snippet', '')}
- **发布时间**：{item.get('published', '')}

"""

        if result['materials']['baidu']:
            md_content += f"""
### 百度搜索结果 ({len(result['materials']['baidu'])} 条)

"""
            for i, item in enumerate(result['materials']['baidu'], 1):
                md_content += f"""
#### [{i}] {item.get('title', '')}

- **来源**：Baidu
- **摘要**：{item.get('snippet', '')}

"""

        # 提取内容
        extraction = result.get('extraction', {})

        md_content += f"""
---

## 二、冲突点分析

编剧提取的**3个核心戏剧冲突点**（按张力从高到低）：

"""
        for i, conflict in enumerate(extraction.get('conflicts', []), 1):
            md_content += f"**{i}. {conflict}**\n\n"

        md_content += f"""
---

## 三、人物心理档案

根据素材推导的人物原型及其**隐性心理动机**：

"""
        for person, motive in extraction.get('character_motives', {}).items():
            md_content += f"- **{person}**：{motive}\n\n"

        md_content += f"""
---

## 四、可舞台化动作瞬间

编剧选定的**5个具有视觉冲击力的动作瞬间**（每个都暴露心理状态）：

"""
        for i, moment in enumerate(extraction.get('stage_moments', []), 1):
            md_content += f"**{i}. {moment}**\n\n"

        md_content += f"""
---

## 五、下一步

- [ ] 确认主要人物数量和关系
- [ ] 选定故事发生的具体时空
- [ ] 确定主要主题（反腐?救赎?权力?）
- [ ] 准备进入 `/outline` 大纲创作阶段

"""

        # 保存文件
        filename.write_text(md_content, encoding="utf-8")
        return str(filename)


# ─────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    # 参数解析
    search_query = None
    drama_name = None
    verbose = False
    demo_mode = False

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--search":
            search_query = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
            i += 2
        elif sys.argv[i] == "--name":
            drama_name = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
            i += 2
        elif sys.argv[i] == "--verbose":
            verbose = True
            i += 1
        elif sys.argv[i] == "--demo":
            demo_mode = True
            search_query = sys.argv[i + 1] if i + 1 < len(sys.argv) else "反腐剧示例"
            i += 2 if i + 1 < len(sys.argv) else 1
        else:
            i += 1

    if not search_query:
        print("❌ 请提供搜索关键词，例如：--search '反腐剧'")
        print("   或使用演示模式：--demo")
        sys.exit(1)

    # 演示模式（用于测试工作流）
    if demo_mode:
        demo_result()
        return

    # 执行搜索
    search = DramaSearch()
    result = search.search(search_query, verbose=verbose)

    if result.get("success"):
        # 保存结果
        if not drama_name:
            drama_name = search_query.replace(" ", "_")
        
        filepath = search.save_result(result, drama_name)
        print(f"✅ 素材文件已保存：{filepath}\n")
    else:
        print(f"❌ 搜索失败：{result.get('error', 'Unknown error')}\n")


def demo_result():
    """
    演示模式：展示输出格式
    """
    print("\n🎬 演示模式 — 反腐剧素材库示例\n")
    
    demo_data = {
        "success": True,
        "query": "反腐剧示例",
        "timestamp": datetime.now().isoformat(),
        "materials": {
            "bocha": [
                {
                    "source": "Bocha",
                    "title": "落马官员周永康案件详解",
                    "url": "https://example.com/zhou-yongkang",
                    "snippet": "周永康身为党和国家领导人，长期从事违纪违法活动，利用职务便利为他人谋取利益...",
                    "published": "2015-01-10",
                },
                {
                    "source": "Bocha",
                    "title": "反腐败斗争中的权力博弈",
                    "url": "https://example.com/anti-corruption",
                    "snippet": "从中央巡视组到地方纪检机关，反腐体系的建立是一场制度与人性的较量...",
                    "published": "2016-03-20",
                },
            ],
            "baidu": [
                {
                    "source": "Baidu",
                    "title": "纪检监察工作中的困境与突破",
                    "url": "https://example.com/jijian",
                    "snippet": "在调查取证过程中，调查人员面临来自多方的压力和阻挠...",
                    "published": "",
                },
            ],
        },
        "extraction": {
            "conflicts": [
                "纪检调查官员与被调查对象之间的权力对抗——一方掌握调查权，一方拥有背后人脉",
                "个人廉政信念与现实利益考量的内心冲突——调查人员是否会被威胁或腐蚀",
                "制度反腐与人情社会的碰撞——法治线性推进与传统人伦关系网络的对立",
            ],
            "character_motives": {
                "纪检调查官员": "力图通过一次完美调查证明自己的清廉与能力，同时对权力圈层的潜规则充满抵触",
                "被调查对象": "试图通过拖延、隐瞒甚至反击来保护既得利益与身后的利益集团",
                "上级领导": "表面支持调查，实则思量着政治成本与派系平衡",
                "家属/亲信": "为被调查人物进行暗地里的营救与对抗，代表了个人情感对制度的冲击",
            },
            "stage_moments": [
                "调查人员进入留置室，被调查对象一言不发，只用眼神扫过对方，然后缓缓坐下——这一瞬间暴露了被调查者的傲慢与内心的恐惧",
                "调查官员的手指在审讯笔记本上停留了许久，笔尖悬空——暗示调查陷入了困顿，证据链存在破口",
                "被调查对象突然要求见律师，从之前的沉默变为主动发声——权力态势的逆转，被调查者开始反击",
                "办案基地的灯火整夜不灭，镜头扫过疲惫的调查人员轮流喝咖啡——制度与人性的消耗战",
                "被调查对象在笔录上签字时，手掌微微颤抖，笔尖戳破纸张——一瞬间的心理防线崩塌",
            ],
        },
    }

    search = DramaSearch()
    filepath = search.save_result(demo_data, "反腐剧示例")

    print(f"✅ 演示素材库已生成：{filepath}")
    print("\n📝 输出格式包含：")
    print("   • 搜索素材来源（Bocha + 百度）")
    print("   • 冲突点分析（3 个核心戏剧冲突）")
    print("   • 人物心理档案（隐性心理动机）")
    print("   • 可舞台化动作瞬间（5 个视觉冲击力动作）")
    print(f"\n💡 下一步：查看 {filepath} 了解详细结构\n")


if __name__ == "__main__":
    main()
