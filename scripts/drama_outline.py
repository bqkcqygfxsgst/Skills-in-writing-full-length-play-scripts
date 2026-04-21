#!/usr/bin/env python3
"""
DramaOutline — 话剧大纲生成系统
基于素材库输入，使用 RAG 理论指导和 LLM 创作，生成完整的多幕大纲

用法:
  python scripts/drama_outline.py --drama "剧名"                # 标准用法
  python scripts/drama_outline.py --drama "剧名" --structure 4  # 指定幕数
  python scripts/drama_outline.py --demo                        # 演示模式
  python scripts/drama_outline.py --demo --structure 3          # 三幕演示
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

# === 加载环境变量 ===
_repo_root = Path(__file__).parent.parent
load_dotenv(_repo_root / ".env")

# === 配置常量 ===
OUTPUT_DIR = _repo_root / "output"
MEMORY_FILE = _repo_root / "MEMORY.md"
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")


# ─────────────────────────────────────────────
class DramaOutline:
    """话剧大纲生成核心类"""

    def __init__(self):
        self.llm_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 读取素材库 ──────────────────────
    def _load_memory(self, drama_name: str) -> Dict:
        """
        从 MEMORY.md 读取项目信息
        或寻找 output/[剧名]_素材库.md 中的信息
        """
        memory_data = {
            "drama_name": drama_name,
            "main_theme": "",
            "secondary_themes": [],
            "conflicts": [],
            "characters": {},
            "stage_moments": [],
        }

        # 尝试从 output 目录找素材库
        materials_file = OUTPUT_DIR / f"{drama_name}_素材库.md"
        if materials_file.exists():
            content = materials_file.read_text(encoding="utf-8")
            # 简单解析 Markdown，提取冲突点和人物
            if "## 二、冲突点分析" in content:
                start = content.index("## 二、冲突点分析") + len("## 二、冲突点分析")
                end = content.index("## 三、人物心理档案") if "## 三、人物心理档案" in content else len(content)
                conflict_section = content[start:end]
                # 提取冲突点
                import re
                conflicts = re.findall(r'\*\*\d+\.\s*(.+?)\*\*', conflict_section)
                memory_data["conflicts"] = conflicts

            if "## 三、人物心理档案" in content:
                start = content.index("## 三、人物心理档案") + len("## 三、人物心理档案")
                end = content.index("## 四、可舞台化动作瞬间") if "## 四、可舞台化动作瞬间" in content else len(content)
                char_section = content[start:end]
                # 提取人物和心理动机
                import re
                chars = re.findall(r'\-\s*\*\*(.+?)\*\*：(.+?)(?:\n|$)', char_section)
                for name, motive in chars:
                    memory_data["characters"][name] = {"motive": motive}

            if "## 四、可舞台化动作瞬间" in content:
                start = content.index("## 四、可舞台化动作瞬间") + len("## 四、可舞台化动作瞬间")
                moment_section = content[start:]
                import re
                moments = re.findall(r'\*\*\d+\.\s*(.+?)\*\*', moment_section)
                memory_data["stage_moments"] = moments

        return memory_data

    # ── RAG 获取理论指导 ──────────────────────
    def _get_rag_guidance(self, theme: str, structure: int) -> str:
        """
        调用 RAG 系统获取戏剧理论指导
        """
        try:
            import subprocess
            query = f"{theme} {structure}幕结构 人物弧光 节拍规划 主题承载"
            result = subprocess.run(
                ["python3", str(_repo_root / "scripts" / "drama_rag.py"), "--query", query],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(_repo_root),
            )
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"⚠️  RAG 查询返回错误，使用默认理论")
                return ""
        except Exception as e:
            print(f"⚠️  RAG 调用失败：{str(e)}")
            return ""

    # ── 生成大纲结构 ──────────────────────
    def _generate_structure(
        self,
        drama_name: str,
        main_theme: str,
        secondary_themes: List[str],
        conflicts: List[str],
        characters: Dict,
        structure: int = 3,
        rag_guidance: str = "",
    ) -> str:
        """
        使用 LLM 生成完整大纲
        """
        char_list = "\n".join([f"- {name}：{data.get('motive', '未定')}" for name, data in characters.items()])
        conflicts_list = "\n".join([f"- {c}" for c in conflicts[:3]])
        theme_list = "\n".join([f"- {t}" for t in secondary_themes])

        prompt = f"""
你是一位资深剧作家。基于以下信息，为一部{structure}幕话剧创作**完整的创作大纲**。

【剧目基本信息】
- 剧名：{drama_name}
- 主要主题：{main_theme}
- 次要主题：
{theme_list}

【核心冲突点】
{conflicts_list}

【主要人物及心理动机】
{char_list}

【戏剧理论指导】
{rag_guidance[:1000] if rag_guidance else "使用标准三幕/四幕结构。"}

【创作要求】
你的大纲必须包含：

0. **故事简介**（必須）
   - 用 1-2 句话清晰说明这个剧讲的是什么故事（核心人物、核心冲突、故事结果）
   - 格式：「[人物] 在 [环境/情境] 中面临 [核心冲突]，最终 [故事进展方向]」
   - 示例：「一个基层官员在升迁诱惑与廉政压力之间摇摆，最终通过一个下属的坚持而重新审视自己的价值观」

1. **剧目概览**
   - 创作初衲：为何要写这个故事？
   - 主题服务逻辑：主要主题如何通过次要主题完成拆解

2. **结构路线图**（{structure}幕）— ⚠️ **话剧舞台版，非电影版**
   
   **核心约束**：这是话剧，不是电影。每一幕是演员连贯表演的单元。
   
   每幕需要包含：
   - 幕名（具有戏剧张力的指示词，如"失衡与抉择"）
   - 幕目标（戏剧任务是什么）
   - **物理空间**：该幕发生在几个不同的地点
     - ✅ 推荐：1个空间（最佳—演员无需走场）
     - ✅ 允许：2个空间（转换必须是戏剧内容，转换时间≤1分钟）
     - ❌ 禁止：3个或以上空间（这是电影思维）
   
   - **关键节拍（6-8个）**：
     - 所有节拍都发生在上述1-2个物理空间内
     - 每个节拍用 Beat N: [人物] [具体发生的冲突或转折] 格式描述
     - **节拍是创作参考，不是舞台分割点**
     - 节拍之间应该有因果连锁，不是简单的事件罗列
   
   - **幕高潮**：该幕的最高冲突点
   
   - **场景转换说明**（如果幕内有>1个空间）：转换过程是否是戏剧内容的一部分？如何自然过渡？

3. **人物欲望曲线**
   每个人物需要说明：
   - 开场欲望：故事开始时想要什么
   - 表面障碍：显而易见的阻力
   - 内心障碍：更深层的心理困境
   - 最终变化：故事结尾此人物的蜕变

4. **主次主题对位图**
   清晰说明每幕/关键场景承载哪个次要主题，如何推进主要主题

5. **舞台视觉与语感设定**
   - 总体色调/氛围：整部戏的美学风格
   - 核心意象：贯穿全剧的视觉符号（如工厂寂静、摄像头注视等）

【输出格式】
用 Markdown 格式输出大纲，完整、具体、可操作。每个节拍都要说明人物行动和冲突推进。

"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"❌ LLM 调用失败：{str(e)}")
            return ""

    # ── 保存大纲 ──────────────────────
    def save_outline(
        self,
        drama_name: str,
        main_theme: str,
        secondray_themes: List[str],
        outline_content: str,
    ) -> str:
        """
        保存大纲至 Markdown 文件
        """
        filename = OUTPUT_DIR / f"{drama_name}_全案大纲.md"

        md_content = f"""# {drama_name} — 全案大纲

**生成时间**：{datetime.now().isoformat()}  
**主要主题**：{main_theme}

---

## 📖 故事简介

> 本部分由下方大纲的"故事简介"章节生成，请在下面的完整大纲中查看具体表述

---

{outline_content}

---

## 附录：工作流进度

- [x] `/start`：素材库已生成
- [x] `/outline`：大纲已确认
- [ ] `/plan`：场景规划
- [ ] `/write`：具体写作
- [ ] `/review`：虚拟导演审阅
- [ ] `/de-ai`：去AI味抛光

"""

        filename.write_text(md_content, encoding="utf-8")
        return str(filename)

    # ── 主入口 ──────────────────────
    def generate(self, drama_name: str, main_theme: str = "", structure: int = 3) -> Dict:
        """
        完整的大纲生成流程
        """
        print(f"\n📖 开始生成大纲：「{drama_name}」（{structure}幕剧）\n")

        # 1. 加载素材
        print("  ▸ 加载素材库...")
        memory = self._load_memory(drama_name)
        if not main_theme:
            main_theme = "弘扬优秀的社会主义核心价值观"
        memory["main_theme"] = main_theme

        print(f"    ✓ 加载成功")
        print(f"      - 冲突点：{len(memory['conflicts'])} 个")
        print(f"      - 人物：{len(memory['characters'])} 个")

        # 2. RAG 理论指导
        print("\n  ▸ 调用 RAG 获取理论指导...")
        rag_guidance = self._get_rag_guidance(main_theme, structure)
        if rag_guidance:
            print(f"    ✓ 获取理论指导成功（{len(rag_guidance)} 字）")
        else:
            print("    ℹ 使用默认理论框架")

        # 3. 生成大纲
        print("\n  ▸ 使用 LLM 生成大纲...")
        outline_content = self._generate_structure(
            drama_name,
            main_theme,
            memory.get("secondary_themes", ["价值观斗争", "人性与制度的冲突"]),
            memory.get("conflicts", ["基层官员与制度压力的对抗"]),
            memory.get("characters", {}),
            structure=structure,
            rag_guidance=rag_guidance,
        )

        if not outline_content:
            return {"success": False, "error": "LLM 生成失败"}

        print(f"    ✓ 大纲生成成功（{len(outline_content)} 字）")

        # 4. 保存
        print("\n  ▸ 保存大纲文件...")
        filepath = self.save_outline(drama_name, main_theme, [], outline_content)
        print(f"    ✓ 大纲已保存：{filepath}\n")

        return {
            "success": True,
            "drama_name": drama_name,
            "filepath": filepath,
            "structure": structure,
            "outline_length": len(outline_content),
        }


# ─────────────────────────────────────────────
def demo_outline():
    """
    演示模式：展示大纲输出格式
    """
    print(f"\n🎬 演示模式 — 话剧大纲示例\n")

    demo_content = """
## 0. 故事简介

一个基层官员李明在升迁诱惑与廉政压力之间摇摆，因一次妥协而逐步陷入腐败泥潭。同时，年轻下属陈芳坚守原则发起举报，最终让李明在被调查中重新审视自己，选择坦白自首并重获救赎。这是一个关于选择、底线与人性拷问的故事。

---

## 1. 剧目概览

- **创作初衷**：通过一个基层官员的选择故事，展现在权力诱惑与廉政压力之间的人性抉择
- **主题服务逻辑**：主要主题"社会主义核心价值观"通过"价值观斗争"（诚实vs虚伪、廉洁vs腐败）完成具体表达

---

## 2. 结构路线图

### 第一幕：失衡与抉择

**幕目标**：建立规定情境。一个基层官员面临升迁诱惑，同时发现身边的腐败网络，开始内心动摇。

**关键节拍**：
- **Beat 1**：李明升迁面试 → 察觉到考官话语中的"潜规则"暗示
- **Beat 2**：下属王浩下班后招待李明 → 暗示"先给好处" → 李明拒绝但心动
- **Beat 3**：李明回家，妻子唠叨升迁失败的后果 → 李明陷入两难
- **Beat 4**：李明接到神秘电话（上级领导）→ "你的前任是怎么做的？"（暗示必须用非正规手段）
- **Beat 5**：李明翻出旧日记 → 看到年轻时的承诺"守住底线" → 一阵怅然
- **Beat 6**：李明决定...先妥协一次（为了家人，他告诉自己）→ 给王浩一个批文

**幕高潮**：李明签署文件时，手指停顿了三秒 → 然后笔尖触纸

---

### 第二幕：深渊与挣扎

**幕目标**：妥协制造后果。李明的一个决定引发连锁反应，他逐渐被卷入越来越深的利益网络，同时清廉的年轻下属陈芳发现端倪。

**关键节拍**：
- **Beat 7**：数日后，李明获得升迁通知 → 感受到权力的甜蜜
- **Beat 8**：陈芳提交一份调查报告 → 发现李明的批文存在问题 → 陈芳前去问李明
- **Beat 9**：李明办公室，陈芳直言"这个批文有问题" → 李明冷漠回应"你太年轻，不懂现实"
- **Beat 10**：陈芳决定上报 → 李明得知 → 李明威胁陈芳"这是你自己的选择"
- **Beat 11**：李明在酒局上，试图用官场游戏规则劝陈芳收回举报 → 陈芳愤然离席
- **Beat 12**：李明失眠，看到了自己变成了昔日厌恶的那类官员

**幕高潮**：纪检部门突然出现，带走了王浩 → 李明接到王浩的讯息"别供出我给你了好处"

---

### 第三幕：崩塌与救赎

**幕目标**：高潮爆发。李明被调查，面临抉择：继续包庇还是坦白？他最终做出了什么决定？

**关键节拍**：
- **Beat 13**：审讯室，调查人员亮出证据 → 李明意识到一切都被记录了
- **Beat 14**：陈芳出现在听证会上，提交证据 → 李明看到了曾经的自己
- **Beat 15**：李明与陈芳的对话 → "我不是为了报复你，是为了这份工作本身"
- **Beat 16**：李明主动交代全部细节 → "从第一次妥协开始，一切都下滑了"
- **Beat 17**：法庭判决 → 李明获得从轻处理（因主动坦白）
- **Beat 18**：李明走出法庭，看到昔日的年轻理想 → 反思与救赎的开始

**幕高潮**：李明在监禁前，给陈芳留下一封信："谢谢你，让我回到了我自己"

---

## 3. 人物欲望曲线

### 李明 (主角)
- **开场欲望**：升迁、改善家庭生活条件、获得尊重
- **表面障碍**：升迁考试竞争激烈、背景不如人
- **内心障碍**：理想vs现实、廉洁vs成功的内心冲突
- **最终变化**：从追求权力到追求内心清白，从"成功"的定义转变为"做对的事"

### 陈芳 (对立面 - 理想主义者)
- **开场欲望**：做一个廉洁的官员，守住公共利益
- **表面障碍**：权力网络、上级压力
- **内心障碍**：愤怒vs同情、坚持vs妥协
- **最终变化**：学会理解人性复杂性，但坚守原则

---

## 4. 主次主题对位图

| 场景 | 承载次要主题 | 推进主要主题方式 |
|------|-----------|-----------------|
| 第一幕1-3场 | 价值观：廉洁vs成功 | 展现现实对理想的冲击 |
| 第一幕4-6场 | 人性：自欺欺人 | 个人如何合理化妥协 |
| 第二幕高潮 | 制度vs个人 | 一个人的选择如何影响社会 |
| 第三幕 | 救赎与反思 | 回归社会主义核心价值观的真意 |

---

## 5. 舞台视觉与语感设定

- **色调/氛围**：从开场的冷蓝色官僚压抑感 → 中段的灰黑色诱惑昏迷 → 结尾的白色救赎清晰
- **核心意象**：
  - "笔"：权力、决定、签署（开场李明犹豫的笔，高潮的审讯笔录）
  - "镜子"：自我认知（李明在镜子前看到自己的变化）
  - "信"：初心（旧日记、最后的信件）
"""

    # 保存演示
    filename = OUTPUT_DIR / "主旋律示例_全案大纲.md"
    md_content = f"""# 主旋律示例 — 全案大纲

**生成时间**：{datetime.now().isoformat()}  
**主要主题**：弘扬优秀的社会主义核心价值观

---

{demo_content}

---

## 附录：工作流进度

- [x] `/start`：素材库已生成
- [x] `/outline`：大纲已确认
- [ ] `/plan`：场景规划
- [ ] `/write`：具体写作
- [ ] `/review`：虚拟导演审阅
- [ ] `/de-ai`：去AI味抛光
"""
    filename.write_text(md_content, encoding="utf-8")

    print(f"✅ 演示大纲已生成：{filename}")
    print("\n📝 大纲结构包含：")
    print("   • 故事简介（核心情节、人物、核心冲突的简要说明）")
    print("   • 剧目概览（创作初衷 + 主题服务逻辑）")
    print("   • 结构路线图（多幕 + 关键节拍）")
    print("   • 人物欲望曲线（开场→最终变化）")
    print("   • 主次主题对位图（哪场承载什么主题）")
    print("   • 舞台视觉与语感设定（色调 + 意象）")
    print()


# ─────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    drama_name = None
    main_theme = None
    structure = 3
    demo_mode = False

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--drama":
            drama_name = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
            i += 2
        elif sys.argv[i] == "--theme":
            main_theme = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
            i += 2
        elif sys.argv[i] == "--structure":
            try:
                structure = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 3
                i += 2
            except ValueError:
                structure = 3
                i += 1
        elif sys.argv[i] == "--demo":
            demo_mode = True
            i += 1
        else:
            i += 1

    if demo_mode:
        demo_outline()
        return

    if not drama_name:
        print("❌ 请提供剧名，例如：--drama '权力对峙'")
        print("   或使用演示模式：--demo")
        sys.exit(1)

    # 执行大纲生成
    outline_gen = DramaOutline()
    result = outline_gen.generate(drama_name, main_theme or "", structure)

    if result.get("success"):
        print(f"✅ 大纲生成完成！")
        print(f"\n📖 下一步：")
        print(f"   1. 查看大纲文件确认结构")
        print(f"   2. 发送 `/plan [场次]` 进入场景规划")
        print(f"   3. 发送 `/write [场次]` 开始具体写作\n")
    else:
        print(f"❌ 大纲生成失败：{result.get('error')}\n")


if __name__ == "__main__":
    main()
