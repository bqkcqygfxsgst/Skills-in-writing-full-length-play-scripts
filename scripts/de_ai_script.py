#!/usr/bin/env python3
"""
去AI味处理脚本 — 剧本文本去模板化
基于de-AI-writing技能的简化版本
"""

import re
from pathlib import Path

class DeAIProcessor:
    def __init__(self, text):
        self.text = text
        self.changes_log = []
    
    def remove_ai_markers(self):
        """删除AI标记词"""
        # 删除常见的AI路标词
        patterns = [
            (r'而是', ''),  # 禁用"而是"
            (r'我们先来看', ''),
            (r'接下来我们', ''),
            (r'下面我们', ''),
            (r'作为\w+', ''),
            (r'希望这能帮助', ''),
        ]
        
        for pattern, replacement in patterns:
            new_text = re.sub(pattern, replacement, self.text)
            if new_text != self.text:
                self.changes_log.append(f"删除模板词: {pattern}")
                self.text = new_text
    
    def enhance_dialogue(self):
        """增强对话的自然性"""
        # 将某些过于文艺或模板化的表述改为更直接的
        replacements = [
            (r'整个|完全|彻底', ''),
            (r'仿佛|好像|似乎', ''),
            (r'深深的|深层的', '深'),
            (r'无限', ''),
        ]
        
        for old, new in replacements:
            new_text = re.sub(old, new, self.text)
            if new_text != self.text:
                self.changes_log.append(f"表述优化: {old} → {new}")
                self.text = new_text
    
    def improve_pacing(self):
        """改善节奏感"""
        # 将容易产生"学术腔"的词汇替换为更直接的表达
        academic_terms = {
            r'剖析': '直视',
            r'梳理': '整理',
            r'构建': '搭',
            r'赋能': '赋予',
            r'驱动': '推动',
            r'聚焦': '看向',
        }
        
        for old, new in academic_terms.items():
            new_text = re.sub(old, new, self.text)
            if new_text != self.text:
                self.changes_log.append(f"术语替换: {old} → {new}")
                self.text = new_text
    
    def enhance_authenticity(self):
        """增强真实感"""
        # 特别针对剧本中的舞台指示和对话
        
        # 使舞台指示更具体
        self.text = re.sub(r'\(深吸一口气\)', '(吸一口气)', self.text)
        
        # 使对话更自然（删除过度的犹豫词）
        self.text = re.sub(r'(停顿了\s*)+', '(停顿)', self.text)
        
    def process(self):
        """执行所有处理"""
        self.remove_ai_markers()
        self.enhance_dialogue()
        self.improve_pacing()
        self.enhance_authenticity()
        return self.text, self.changes_log


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python de_ai_script.py <输入文件> [输出文件]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.parent / f"{input_path.stem}_DeAI{input_path.suffix}"
    
    # 读取文本
    original_text = input_path.read_text(encoding='utf-8')
    
    # 处理
    processor = DeAIProcessor(original_text)
    processed_text, changes = processor.process()
    
    # 保存
    output_path.write_text(processed_text, encoding='utf-8')
    
    # 输出报告
    print("\n" + "="*60)
    print("✨ 去AI味处理完成")
    print("="*60)
    print(f"\n📄 输入文件: {input_path}")
    print(f"📤 输出文件: {output_path}")
    print(f"\n📝 进行了 {len(changes)} 项修改:")
    for change in changes[:10]:  # 显示前10项
        print(f"  • {change}")
    if len(changes) > 10:
        print(f"  ... 及其他 {len(changes)-10} 项")
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
