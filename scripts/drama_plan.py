#!/usr/bin/env python3
"""
DramaPlan — 话剧场景规划系统
基于大纲，为指定场次生成详细规划表

用法:
  python scripts/drama_plan.py --drama "剧名" --scene 1          # 规划第一场
  python scripts/drama_plan.py --drama "剧名" --scene 1 --verbose # 详细输出
  python scripts/drama_plan.py --demo                            # 演示模式
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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
class DramaPlan:
    """话剧场景规划核心类"""

    def __init__(self):
        self.llm_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 读取大纲 ──────────────────────
    def _load_outline(self, drama_name: str) -> Dict:
        """
        从 output 目录读取大纲文件
        """
        outline_file = OUTPUT_DIR / f"{drama_name}_全案大纲.md"
        if not outline_file.exists():
            return {}

        content = outline_file.read_text(encoding="utf-8")
        return {
            "content": content,
            "drama_name": drama_name,
        }

    # ── 解析场景信息 ──────────────────────
    def _extract_scene_beats(self, outline: Dict, scene_num: int) -> List[Dict]:
        """
        从大纲中提取指定场次的节拍信息
        """
        content = outline.get("content", "")
        
        # 简单的正则匹配：查找 Beat N: 的模式
        beat_pattern = r'- \*\*Beat (\d+)\*\*：(.+?)(?=\n|$)'
        matches = re.findall(beat_pattern, content)
        
        beats = []
        for beat_num, beat_desc in matches:
            beats.append({
                "num": int(beat_num),
                "description": beat_desc.strip(),
            })
        
        return beats[:scene_num + 5]  # 返回内容周边的节拍

    # ── 生成人物任务矩阵 ──────────────────────
    def _generate_character_matrix(
        self,
        drama_name: str,
        outline: Dict,
        scene_num: int,
    ) -> Dict[str, Dict]:
        """
        LLM 生成该场景的人物任务矩阵
        """
        outline_excerpt = outline.get("content", "")[:2000]  # 短摘要
        
        prompt = f"""
你是一位资深舞台导演。基于以下大纲摘要，为这场戏生成**人物任务矩阵**。

【大纲信息】
{outline_excerpt}

【任务】
为这场戏的**每个主要人物**定义：

1. **最高任务**（Objective）
   - 这个人物在本场戏中最想达成什么？
   - 不是表面目标，是深层的欲望驱动

2. **表面障碍**（External Obstacle）
   - 谁或什么东西阻挡了这个人物的目标？

3. **内心障碍**（Internal Obstacle）
   - 人物自身的恐惧、信念或心理困境

4. **戏剧行为**（Action）
   - 为了克服障碍，人物会采取什么行动？
   - 用动词表述：说服、隐瞒、挑战、妥协等

5. **节拍权力归属**（Power Distribution）
   - 本场开场时谁掌握权力？
   - 权力如何转移？
   - 本场结尾谁获得权力？

【输出格式】
用 Markdown 表格格式输出，清晰展示矩阵关系。

示例：
| 人物 | 最高任务 | 表面障碍 | 内心障碍 | 戏剧行为 |
|---|---|---|---|---|
| A | 要回报酬 | B 不愿支付 | 自己也有罪恶感 | 威胁 |
| B | 保护秘密 | A 掌握证据 | 内疚与恐惧 | 逃避 |

"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return {"matrix": resp.choices[0].message.content}
        except Exception as e:
            print(f"⚠️  LLM 调用失败：{str(e)}")
            return {"matrix": "（LLM 生成失败，请手动补充）"}

    # ── 生成权力路径 ──────────────────────
    def _generate_power_path(
        self,
        drama_name: str,
        outline: Dict,
    ) -> str:
        """
        LLM 生成该场景的权力流转路径
        """
        prompt = f"""
你是一位掌握权力分析的编剧。请为这场戏生成**权力流转路径分析**。

【场景设定】
戏名：{drama_name}

【分析任务】
1. **开场权力分布**：在这场戏开始时，谁拥有什么权力？
   - 信息权（谁知道什么秘密）
   - 话语权（谁有说话的权利）
   - 行动权（谁能决定行动）
   - 情感权（谁能操纵他人情绪）

2. **权力转折点**（至少 2-3 个）：
   - 哪一刻权力发生了转移？
   - 是什么行为/言语引发的转移？
   - 谁获得了权力，谁失去了权力？

3. **结场权力分布**：
   - 本场结尾的权力格局如何变化？
   - 这个变化如何推进整个故事？

【输出格式】
用时间轴格式展示，清晰易读。

"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return "（权力路径分析失败）"

    # ── 生成节拍规划表 ──────────────────────
    def _generate_beat_sheet(
        self,
        character_matrix: Dict,
        beats: List[Dict],
    ) -> str:
        """
        根据人物矩阵和大纲节拍生成场景节拍表
        """
        beat_content = ""
        for beat in beats[:6]:  # 限制在 6 个节拍
            beat_content += f"- **Beat {beat['num']}**：{beat['description']}\n"

        prompt = f"""
你是一位专业的舞台导演。请基于以下人物任务矩阵和节拍框架，生成**详细的场景节拍规划表**。

【人物任务矩阵】
{character_matrix.get('matrix', '')}

【节拍框架】
{beat_content}

【规划内容】
为每个节拍补充以下细节：

1. **节拍号与名称**
   - 一句话总结这个节拍的戏剧事件

2. **舞台布景指示**
   - 这个节拍发生在舞台的哪个区域？
   - 需要什么道具？
   - 灯光/音乐的提示

3. **人物行动分解**（Action Breakdown）
   - 哪些人物在这个节拍中出现？
   - 每个人物的具体行动（用动词表述）
   - 该行动暴露了什么心理？

4. **台词方向**（Dialogue Direction）
   - 这个节拍中的台词基调是什么？（激烈/温柔/讽刺等）
   - 是否有肢体冲突、对视、沉默？

5. **冲突点**
   - 这个节拍中的对立是什么？
   - 谁战胜了谁，还是陷入僵局？

【输出格式】
用标题和列表清晰组织，可操作性强。

"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return "（节拍规划表生成失败）"

    # ── 生成因果钩子 ──────────────────────
    def _generate_causality_hook(self, drama_name: str) -> str:
        """
        生成本场结尾的"未竟事件"，成为下场的开场驱动
        """
        prompt = f"""
你是编剧。请为这场戏的结尾生成**因果钩子**——一个"未竟事件"，必须在下一场戏中被解决。

【因果钩子要求】
1. **未竟事件部分**：
   - 在本场结尾留下什么悬念？
   - 什么问题没有得到解答？
   - 什么冲突激化了却没有解决？

2. **不可撤回的行动**：
   - 本场发生了什么"不可逆"的行为？
   - （如：签署文件、说出秘密、做出承诺）
   - 这个行动如何强制下一场必须继续？

3. **下场开场的驱动力**：
   - 下一场开场时，人物被迫面对什么新局面？
   - 这个新局面是如何由本场的行动引发的？

【输出格式】
分三部分清晰表述。

"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return "（因果钩子生成失败）"

    # ── 冲突密度检查 ──────────────────────
    def _check_conflict_density(self, beat_sheet: str) -> str:
        """
        检查节拍是否满足冲突密度标准
        """
        prompt = f"""
你是编剧导师。请对以下节拍规划进行**冲突密度审查**。

【节拍内容】
{beat_sheet[:1500]}

【审查标准】
每 500 字内必须至少包含以下之一：
1. 权力归属的转移（谁从被动变为主动，或反转）
2. 价值观或利益的正面碰撞
3. 支点道具的争夺或破坏

【检查内容】
1. 是否满足冲突密度标准？
2. 如果不满足，哪些节拍偏弱？
3. 建议如何增强冲突？

【输出】
简洁的检查报告。

"""
        try:
            resp = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return "（冲突密度检查失败）"

    # ── 保存规划表 ──────────────────────
    def save_plan(
        self,
        drama_name: str,
        scene_num: int,
        character_matrix: Dict,
        power_path: str,
        beat_sheet: str,
        causality_hook: str,
        conflict_check: str,
    ) -> str:
        """
        保存场景规划表为 Markdown 文件
        """
        filename = OUTPUT_DIR / f"{drama_name}_场景{scene_num}_规划表.md"

        md_content = f"""# {drama_name} — 第 {scene_num} 场规划表

**规划时间**：{datetime.now().isoformat()}

---

## 一、人物任务矩阵

该场景中每个人物的目标、障碍与行动：

{character_matrix.get('matrix', '（未生成）')}

---

## 二、权力流转路径

本场戏的权力格局如何演变：

{power_path}

---

## 三、节拍规划表

每个节拍的具体执行细节：

{beat_sheet}

---

## 四、冲突密度检查

本场是否满足冲突密度标准：

{conflict_check}

---

## 五、因果钩子与下场驱动

本场结尾的未竟事件与下一场的连接点：

{causality_hook}

---

## 六、舞台执行清单

- [ ] 人物任务矩阵已定义
- [ ] 权力路径已明确
- [ ] 每个节拍的行动已分解
- [ ] 冲突密度已验证
- [ ] 因果钩子已设置
- [ ] 准备进入 `/write` 步骤

"""

        filename.write_text(md_content, encoding="utf-8")
        return str(filename)

    # ── 主入口 ──────────────────────
    def generate_plan(self, drama_name: str, scene_num: int = 1) -> Dict:
        """
        完整的场景规划流程
        """
        print(f"\n📋 开始规划场景：「{drama_name}」第 {scene_num} 场\n")

        # 1. 加载大纲
        print("  ▸ 加载大纲文件...")
        outline = self._load_outline(drama_name)
        if not outline:
            return {"success": False, "error": "未找到大纲文件"}
        print("    ✓ 大纲已加载")

        # 2. 提取节拍信息
        print("  ▸ 解析节拍信息...")
        beats = self._extract_scene_beats(outline, scene_num)
        print(f"    ✓ 提取 {len(beats)} 个节拍")

        # 3. 生成人物任务矩阵
        print("  ▸ 生成人物任务矩阵...")
        character_matrix = self._generate_character_matrix(drama_name, outline, scene_num)
        print("    ✓ 矩阵已生成")

        # 4. 生成权力路径
        print("  ▸ 分析权力流转...")
        power_path = self._generate_power_path(drama_name, outline)
        print("    ✓ 权力路径已分析")

        # 5. 生成节拍规划表
        print("  ▸ 生成节拍规划表...")
        beat_sheet = self._generate_beat_sheet(character_matrix, beats)
        print("    ✓ 规划表已生成")

        # 6. 检查冲突密度
        print("  ▸ 检查冲突密度...")
        conflict_check = self._check_conflict_density(beat_sheet)
        print("    ✓ 密度检查完成")

        # 7. 生成因果钩子
        print("  ▸ 设置因果钩子...")
        causality_hook = self._generate_causality_hook(drama_name)
        print("    ✓ 因果钩子已设置")

        # 8. 保存规划表
        print("  ▸ 保存规划表...")
        filepath = self.save_plan(
            drama_name,
            scene_num,
            character_matrix,
            power_path,
            beat_sheet,
            causality_hook,
            conflict_check,
        )
        print(f"    ✓ 规划表已保存\n")

        return {
            "success": True,
            "drama_name": drama_name,
            "scene_num": scene_num,
            "filepath": filepath,
        }


# ─────────────────────────────────────────────
def demo_plan():
    """演示模式"""
    print(f"\n🎬 演示模式 — 场景规划示例\n")

    demo_content = """
## 一、人物任务矩阵

| 人物 | 最高任务 | 表面障碍 | 内心障碍 | 戏剧行为 |
|---|---|---|---|---|
| 李明 | 说服陈芳删除证据 | 陈芳掌握把柄 | 自知理亏且恐惧曝光 | 威胁 + 劝阻 |
| 陈芳 | 推进举报流程 | 李明的职权压制 | 害怕职业生涯被毁 | 坚持 + 申诉 |
| 王局长 | 化解舆论危机 | 证据链完整 | 害怕自己帮李明也被牵连 | 试探 + 疏远 |

---

## 二、权力流转路径

**开场权力分布**：
- 李明：掌握话语权（身为上级）+ 隐性的决策权（靠关系）
- 陈芳：掌握信息权（有证据）,但话语权最弱

**权力转折点 1**（Beat 3）：
- 陈芳当众递交证据副本 → 陈芳获得法律保护（信息权转为证人权）
- 李明失去单独掩盖的机会

**权力转折点 2**（Beat 5）：
- 王局长电话中表态："这件事我管不了" → 李明失去第二道防线
- 权力从隐性转为公开对抗

**结场权力分布**：
- 陈芳：获得话语权（有法律支持）
- 李明：权力瓦解（只剩最后的威胁选项）

---

## 三、节拍规划表

### Beat 1: 办公室对话开场
**舞台布景**：李明办公室，夕阳透过窗户投进暗黄光线
**人物出场**：李明、陈芳
**行动分解**：
- 李明：整理公文，抬头看陈芳，眼神中混着探测和冷漠
- 陈芳：站立（不坐），双手拿着文件夹，略显紧张

**台词方向**：李明温和但有压力，陈芳恭敬但坚定
**冲突**：权力不对等的对话框架建立

### Beat 2: 李明试图"沟通"
**行动**：李明绕过办公桌走向陈芳
**舞台指示**：陈芳往后退了一步
**台词方向**：李明从威胁转为劝诱 ("想想你的未来")
**冲突**：李明的权力压制遭遇陈芳的沉默抵抗

### Beat 3: 陈芳提交证据（高潮 1）
**舞台指示**：陈芳突然打开文件夹，递出证据副本
**李明反应**：身体瞬间僵硬，表情变冷
**台词**："我已经存档了多份。"
**冲突**：权力完全逆转，李明陷入被动

### Beat 4: 李明的最后试探
**舞台指示**：李明走回办公桌后，用话机
**行为**：拨通王局长的电话，背对着陈芳说话
**台词方向**：假装轻松 ("就是想确认一下流程")
**冲突**：李明试图从上级那里找到突破口

### Beat 5: 王局长的冷漠拒绝
**舞台指示**：李明放下话机，表情黯淡
**李明转向陈芳**：眼神中的最后一丝希望消去
**台词**："你赢了。"（或转身直接离场）
**冲突**：李明彻底失去所有防线，权力结构坍塌

### Beat 6: 陈芳的独白/离场
**舞台指示**：陈芳看着空荡的办公室，走向门口
**台词方向**：陈芳的台词既是胜利的呼吸，也是理想主义的代价 (如果有)
**冲突**：权力转移的后果显现

---

## 四、冲突密度检查

✅ **满足标准**

- **权力转移**：Beat 3 处发生了明确的权力反转
- **价值观碰撞**：廉洁（陈芳）vs. 现实妥协（李明）的对立
- **行为不可逆**：陈芳提交证据是不可撤回的行动

建议：如果舞台时间允许，可在 Beat 4-5 间添加更多的对话冲突。

---

## 五、因果钩子

**未竟事件**：
- 王局长表示"管不了"背后的原因是什么？
- 李明是否会采取更激进的报复行为？

**不可撤回的行动**：
- 陈芳已递交举报 → 流程已启动，无法停止

**下场开场驱动**：
下一场必须面对："调查已启动，李明将如何应对？陈芳的举报会带来什么后果？"

---

## 六、舞台执行清单

- [x] 人物任务矩阵已定义
- [x] 权力路径已明确
- [x] 每个节拍的行动已分解
- [x] 冲突密度已验证
- [x] 因果钩子已设置
- [ ] 准备进入 `/write` 步骤
"""

    filename = OUTPUT_DIR / "示例_场景1_规划表.md"
    md_content = f"""# 示例项目 — 第 1 场规划表

**规划时间**：{datetime.now().isoformat()}

{demo_content}
"""
    filename.write_text(md_content, encoding="utf-8")

    print(f"✅ 演示规划表已生成：{filename}")
    print("\n📝 规划表包含：")
    print("   • 人物任务矩阵（目标 + 障碍 + 行为）")
    print("   • 权力流转路径（开场 → 转折 → 结场）")
    print("   • 节拍规划表（舞台布景 + 行动 + 台词方向）")
    print("   • 冲突密度检查")
    print("   • 因果钩子与下场连接")
    print()


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
        demo_plan()
        return

    if not drama_name:
        print("❌ 请提供剧名，例如：--drama '权力对峙'")
        print("   或使用演示模式：--demo")
        sys.exit(1)

    # 执行规划
    planner = DramaPlan()
    result = planner.generate_plan(drama_name, scene_num)

    if result.get("success"):
        print(f"✅ 场景规划完成！")
        print(f"\n📖 下一步：")
        print(f"   1. 查看规划表确认结构")
        print(f"   2. 根据规划表进行调整优化")
        print(f"   3. 发送 `/write {scene_num}` 开始具体写作\n")
    else:
        print(f"❌ 规划失败：{result.get('error')}\n")


if __name__ == "__main__":
    main()
