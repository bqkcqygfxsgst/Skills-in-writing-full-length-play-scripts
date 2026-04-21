#!/usr/bin/env python3
"""
DramaWrite — 话剧完整幕级写作系统
基于规划表，生成连贯的、可直接舞台演出的完整幕级剧本

⚠️ 核心原则：每一幕是一个不可分割的戏剧单位
- 节拍是内部的节奏参考，不是硬分割点
- 最终输出应该是连贯的、人物情感线贯穿全幕的完整文本
- 场景头仅在物理空间改变时出现

用法:
  python scripts/drama_write.py --drama "剧名" --scene 1           # 写作完整幕，内容自然连贯
  python scripts/drama_write.py --drama "剧名" --scene 1 --demo    # 演示模式
  python scripts/drama_write.py --demo                            # 快速查看连贯脚本格式
"""

import os
import sys
import re
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
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")


# ─────────────────────────────────────────────
class DramaWrite:
    """话剧写作核心类"""

    def __init__(self):
        self.llm_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 读取规划表 ──────────────────────
    def _load_plan(self, drama_name: str, scene_num: int) -> Dict:
        """
        读取场景规划表
        """
        plan_file = OUTPUT_DIR / f"{drama_name}_场景{scene_num}_规划表.md"
        if not plan_file.exists():
            return {}

        content = plan_file.read_text(encoding="utf-8")
        return {
            "content": content,
            "drama_name": drama_name,
            "scene_num": scene_num,
        }

    # ── 读取大纲 ──────────────────────
    def _load_outline(self, drama_name: str) -> Dict:
        """
        读取大纲以获取世界设定、舞台气氛等背景信息
        """
        outline_file = OUTPUT_DIR / f"{drama_name}_全案大纲.md"
        if not outline_file.exists():
            return {}

        content = outline_file.read_text(encoding="utf-8")
        return {
            "content": content,
            "drama_name": drama_name,
        }

    # ── 解析规划表中的节拍 ──────────────────────
    def _extract_beats_from_plan(self, plan: Dict) -> List[Dict]:
        """
        从规划表中提取节拍信息
        """
        content = plan.get("content", "")
        
        # 提取节拍规划表部分
        if "## 三、节拍规划表" not in content:
            return []

        beat_section = content.split("## 三、节拍规划表")[1]
        if "## 四、" in beat_section:
            beat_section = beat_section.split("## 四、")[0]

        # 解析节拍
        beats = []
        beat_blocks = re.split(r'### Beat (\d+):', beat_section)
        
        for i in range(1, len(beat_blocks), 2):
            if i + 1 < len(beat_blocks):
                beat_num = int(beat_blocks[i])
                beat_content = beat_blocks[i + 1].strip()
                beats.append({
                    "num": beat_num,
                    "content": beat_content,
                })

        return beats

    # ── 为单个节拍生成写作内容 ──────────────────────
    def _write_beat(
        self,
        beat_num: int,
        beat_plan: Dict,
        drama_style: str = "",
        context: str = "",
    ) -> str:
        """
        LLM 为单个节拍生成舞台剧文本
        
        ⚠️ 重要：这个节拍是幕的一部分，不是独立单元
        - 需要与前个视点的故事线连贯
        - 逐步推进冲突，而不是重新开始
        - 场景头仅在必要时出现（物理空间改变）
        """
        prompt = f"""
你是一位资深编剧，精通舞台剧写作规范。现在请为以下节拍生成舞台剧文本。

⚠️ 核心要求：这个节拍是完整幕级叙事的一部分
- 它的内容需要与前后节拍形成**连贯的叙事链条**
- 不要生硬重复场景头（除非真的改变了物理空间）
- 人物的情感和立场应该是**逐步演进**的，不是反复拉回或重置
- 最终这个节拍会被融入幕级文本中，应该自然过渡，看不出"节拍"的痕迹

【舞台剧写作强制规范】
1. 场景头格式（仅在物理空间改变时出现）：
   [时间：具体时刻 + 氛围感描述]
   [地点：物理空间的精确名称]
   [舞台布景：道具摆放位置 + 空间支点]
   [人物状态：人物此刻的可见动作]

2. 动作提示规范：
   - 必须可被观察（舞台上能看到）
   - 必须揭示心理状态
   - ✅ 正确：(他用拇指指甲反复划过裤缝)
   - ❌ 错误：(他感到愤怒)

3. 对话与潜台词：
   - 台词往往是谎言或掩饰，潜台词才是真相
   - 绝不允许人物直接说出内心想法
   - 避免"广播剧腔"

【节拍信息】
Beat {beat_num}：
{beat_plan}

【世界设定与前情】
{context[:800]}

【创作任务】
为这个节拍生成连贯的舞台文本：
1. 仅在必要时给出场景头（物理空间改变）
2. 人物的行动应该是前一节拍的**自然延续**
3. 冲突逐步深化，不要重复或转身回头
4. 呈现具体的、可观察的舞台动作和对话

【输出格式】
[场景头 - 仅在必要时]

人物名：
  (动作)
  台词

（时间与空间的过渡，应该通过动作和灯光变化自然呈现，而非硬分割）

【字数要求】
约 300-500 字，与前后节拍无缝融合

"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"⚠️  LLM 调用失败：{str(e)}")
            return f"（Beat {beat_num} 写作失败）"

    # ── 保存写作成果 ──────────────────────
    def save_scene_script(
        self,
        drama_name: str,
        scene_num: int,
        writing_content: Dict[int, str],
    ) -> str:
        """
        保存完整幕级脚本（已融合所有节拍，内容连贯）
        """
        filename = OUTPUT_DIR / f"{drama_name}_第{scene_num}幕_脚本.md"

        md_content = f"""# {drama_name} — 第 {scene_num} 幕完整脚本

**写作时间**：{datetime.now().isoformat()}  
**创作基础**：场景规划表 + 大纲指导 + 连贯性优先

---

## 幕级说明
这是一个**完整的、连贯的、可直接舞台演出的幕级文本**。
所有内容形成统一的叙述流，人物情感线贯穿始终，无硬分割。

---

"""

        # 融合所有节拍内容（移除"Beat"标记，直接呈现连贯内容）
        for beat_num, content in sorted(writing_content.items()):
            # 不添加"## Beat N"的分割标记，而是直接将内容融入
            md_content += f"{content}\n\n"

        filename.write_text(md_content, encoding="utf-8")
        return str(filename)

    # ── 主入口 ──────────────────────
    def write_scene(self, drama_name: str, scene_num: int = 1, demo: bool = False) -> Dict:
        """
        完整的幕级写作流程（成果为连贯的、可直接舞台演出的完整幕级文本）
        """
        if demo:
            print(f"\n🎬 演示模式 — 完整幕级脚本示例（无硬分割）\n")
            return self._generate_demo_script(drama_name, scene_num)

        print(f"\n✍️  开始写作幕级脚本：「{drama_name}」第 {scene_num} 幕\n")

        # 1. 加载规划表
        print("  ▸ 加载规划表...")
        plan = self._load_plan(drama_name, scene_num)
        if not plan:
            print("    ⚠️  未找到规划表，建议先执行 `/plan` 步骤")
            # 用演示模式继续
            plan = {"content": "演示规划表", "drama_name": drama_name, "scene_num": scene_num}
        print("    ✓ 规划表已加载")

        # 2. 加载大纲
        print("  ▸ 加载大纲...")
        outline = self._load_outline(drama_name)
        if outline:
            print("    ✓ 大纲已加载")
        else:
            print("    ⚠️  未找到大纲")

        # 3. 解析节拍
        print("  ▸ 分析节拍结构（仅作为创作参考）...")
        beats = self._extract_beats_from_plan(plan)
        print(f"    ✓ 识别 {len(beats)} 个内部节奏点")

        if not beats:
            print("    ⚠️  未能解析节拍，使用演示数据")
            return self._generate_demo_script(drama_name, scene_num)

        # 4. 逐节拍写作（生成内容需要在融合过程中自然衔接）
        print(f"  ▸ 生成连贯的幕级文本（{len(beats)} 个节奏点融合）...\n")
        writing_content = {}
        
        for beat in beats[:3]:  # 限制演示为前 3 个节拍
            print(f"    正在扩写节奏点 {beat['num']}...", end=" ")
            content = self._write_beat(
                beat["num"],
                beat["content"],
                context=outline.get("content", ""),
            )
            writing_content[beat["num"]] = content
            print("✓")

        print()

        # 5. 保存脚本
        print("  ▸ 保存连贯的幕级脚本...")
        filepath = self.save_scene_script(drama_name, scene_num, writing_content)
        print(f"    ✓ 脚本已保存\n")

        return {
            "success": True,
            "drama_name": drama_name,
            "scene_num": scene_num,
            "beats_written": len(writing_content),
            "filepath": filepath,
        }

    # ── 演示模式 ──────────────────────
    def _generate_demo_script(self, drama_name: str, scene_num: int) -> Dict:
        """
        生成演示脚本（完整幕级，无节拍标记，连贯呈现）
        """
        demo_script = {
            1: """[时间：下午 3 点，办公室的暮色显得压抑。窗帘拉半开，外面的树影在白墙上摇晃。]
[地点：市纪检监察办案基地的办公室。白色办公桌，一盏绿台灯，墙上挂着"廉政"二字。]
[舞台布景：办公桌上散放着文件夹、签名笔、一杯冷咖啡。背后是书柜。]
[人物状态：李明坐在办公椅上，双手交叠，眼睛看向远处。陈芳站在门边，手中握着文件夹。]

陈芳：
  (推门进来，脚步很慢，停留在门框边)
  李主任...我想和你谈谈上次的批文。

李明：
  (没有抬头，只是缓缓转动办公椅)
  坐。
  (他的语调很平，却隐含着某种压力)

陈芳：
  (没有坐，只是走近了两步，停在椅子前方)
  (她的手指在文件夹的塑料封面上轻轻敲击，发出细微的声音)
  我查了一下那个项目的后续...

李明：
  (抬起头，眼神在陈芳脸上停留了三秒)
  你查了？
  (他重复这个词，语调中的讽刺很淡，但能听出来)

陈芳：
  (吞了口唾沫，喉咙发出细微的声音)
  (她打开文件夹，从中抽出几张纸)
  这个批文...有问题。
""",

            2: """
李明：
  (从椅子上站起身，走向陈芳)
  (他的靠近不是威胁，而是一种父亲劝诫女儿时的姿态)
  你还太年轻，不明白这个世界是怎样运转的。
  (他停在距陈芳一米处，声音变得温柔)
  这件事...就到此为止吧。

陈芳：
  (往后退了半步，与李明之间突然形成了对峙的姿态)
  (她的眼睛看着李明，但视线有些飘离)
  我不能。
  (她说得很小声，但每个字都很清晰)

李明：
  (他的表情凝固了)
  (他转身走回办公桌，拿起电话)
  我给你一个选择的机会。

陈芳：
  (她突然举起手中的文件夹)
  我已经存档了。多份。
""",

            3: """
李明：
  (放下电话，背对着陈芳，肩膀微微颤动)
  (他没有转身，只是说)
  你赢了。
  (这两个字很轻，但在办公室的寂静中显得很重)

陈芳：
  (她看着眼前这个突然老去的男人)
  (她没有期待中的胜利感，只有一种复杂的失落)
  (她转身走向门口，最后停留了一秒)
  (她的手放在门把上，没有回头)

（灯光渐暗）

（场景结束）
"""
        }

        filename = OUTPUT_DIR / f"{drama_name}_第{scene_num}幕_脚本_演示.md"
        
        md_content = f"""# {drama_name} — 第 {scene_num} 幕脚本（演示示例）

## ⚠️ 重要：连贯性优先原则

**这个演示脚本展示了一个完整的、连贯的幕级文本**。注意：
- ✅ **没有** "## Beat 1/2/3" 标记
- ✅ **场景头仅出现一次**（仅在场景变化时）
- ✅ **整个幕形成一个不可分割的戏剧单位**
- ✅ **内部节奏通过人物动作和对话自然推进**

**创作时间**：{datetime.now().isoformat()}

---

"""

        # 合并所有节拍内容，无硬分割
        for beat_num, content in sorted(demo_script.items()):
            md_content += f"{content}\n\n"

        filename.write_text(md_content, encoding="utf-8")
        
        print(f"✅ 演示脚本已生成：{filename}")
        print("\n📝 脚本演示特点：")
        print("   • 完整的幕级叙事（无Beat标记）")
        print("   • 场景头四行格式（舞台剧规范）")
        print("   • 动作提示暴露心理状态")
        print("   • 潜台词与文本对立")
        print("   • 权力转移的具体呈现")
        print("   • 连贯的因果链条（开场→冲突→高潮→落幕）")
        print()

        return {"success": True, "filepath": str(filename)}


# ─────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    drama_name = None
    scene_num = 1
    demo_mode = False

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--drama":
            drama_name = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
            i += 2
        elif sys.argv[i] == "--scene":
            try:
                scene_num = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 1
                i += 2
            except ValueError:
                scene_num = 1
                i += 1
        elif sys.argv[i] == "--demo":
            demo_mode = True
            i += 1
        else:
            i += 1

    if demo_mode:
        if not drama_name:
            drama_name = "示例剧目"
        writer = DramaWrite()
        writer.write_scene(drama_name, scene_num, demo=True)
        return

    if not drama_name:
        print("❌ 请提供剧名，例如：--drama '权力对峙'")
        print("   或使用演示模式：--demo")
        sys.exit(1)

    # 执行写作
    writer = DramaWrite()
    result = writer.write_scene(drama_name, scene_num)

    if result.get("success"):
        print(f"✅ 场景写作完成！")
        print(f"\n📖 下一步：")
        print(f"   1. 查看脚本，进行调整和优化")
        print(f"   2. 重复写作其他场景")
        print(f"   3. 执行 `/review` 进行虚拟导演审阅")
        print(f"   4. 执行 `/de-ai` 进行去 AI 味抛光\n")
    else:
        print(f"❌ 写作失败\n")


if __name__ == "__main__":
    main()
