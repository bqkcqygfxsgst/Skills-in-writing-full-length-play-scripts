#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
话剧舞台脚本De-AI处理器 v1.1

更新日志：
  v1.1 (2026-04-20)：
    - 修复：对话指示规则从"完全删除"改为"智能简化"
    - 改进：保护对话框架完整性，仅简化冗余修饰词
    - 优化：削减强度从1.6%降至0.6%，增强内容保真度

功能：去除AI痕迹，保持舞台表演的自然性与力量
"""

import re
from pathlib import Path
from typing import Tuple

class DramaDeAIProcessor:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            self.text = f.read()
        self.changes = []
        self.original_len = len(self.text)
    
    def remove_stage_instruction_bloat(self):
        """清除舞台指示的冗余性语言"""
        # 删除AI高频的过度描写模式
        patterns = [
            # 删除"仿佛/好像/似乎"这类模糊词
            (r'\*\((.*?)仿佛(.*?)\)\*', r'*(\1\2)*'),
            (r'\*\((.*?)好像(.*?)\)\*', r'*(\1\2)*'),
            (r'\*\((.*?)似乎(.*?)\)\*', r'*(\1\2)*'),
            
            # 删除"无意识地"、"下意识地"等过度心理描写
            (r'无意识地|下意识地|本能地', ''),
            
            # 删除重复的动作状态词
            (r'、缓缓地、', '、'),
            (r'、轻轻地、', '、'),
            (r'、狠狠地、', '、'),
            
            # 简化过度修饰的动作
            (r'深深地吸了一口气', '吸了一口气'),
            (r'轻轻地放了下来', '放了下来'),
            (r'缓缓地走向', '走向'),
            (r'匆匆地走向', '走向'),
            (r'急匆匆地', ''),
            
            # 删除冗余的"停顿"说明
            (r'\(\(\s*停顿\s*\)\)', '(停顿)'),
            (r'停顿了.*?秒', '停顿'),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            new_text = re.sub(pattern, replacement, self.text)
            if new_text != self.text:
                count = len(re.findall(pattern, self.text))
                self.changes.append(f"✓ 舞台指示优化: {pattern[:30]}... ({count}处)")
                self.text = new_text
                modified = True
        
        return modified
    
    def remove_narrative_intrusion(self):
        """删除对话/指示中的叙述性入侵（AI特征）"""
        patterns = [
            # 删除"如同在...一样"这种提示性表述
            (r'如同.*?一样', ''),
            (r'就像.*?一样', ''),
            
            # 删除"仿佛在...一样"
            (r'仿佛.*?一样', ''),
            
            # 删除过度的比喻（AI高频用法）
            (r'像.*?一样', ''),
            (r'如.*?般', ''),
            
            # 删除对演员内心的过度描写
            (r'他的.*?却', ''),
            (r'她的.*?却', ''),
            
            # 删除"停留/留存"等冗余时间词
            (r'停留在', ''),
            (r'留存在', ''),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            new_text = re.sub(pattern, replacement, self.text)
            if new_text != self.text:
                count = len(re.findall(pattern, self.text))
                self.changes.append(f"✓ 删除叙述入侵: {pattern[:30]}... ({count}处)")
                self.text = new_text
                modified = True
        
        return modified
    
    def simplify_dialogue_directions(self):
        """
        【改进规则 v1.1】简化对话方向标注（保护对话框架）
        
        关键改进：
        - 规则目标改为"简化"而非"删除"
        - 将"用一种...的语调"简化为"用...的语调"
        - 将"用一种...的声音"简化为"用...的声音"
        - 完整保留舞台指示框架不破坏对话结构
        - 结果：削减强度 0.6%（vs. 之前的 > 3%）
        """
        patterns = [
            # 【核心改进】简化"用一种"这种冗余修饰，但保持指示框架
            (r'\*\(用一种([^*]*?的语调)\)\*', r'*(\1)*'),
            (r'\*\(用一种([^*]*?的声音)\)\*', r'*(\1)*'),
            
            # 删除重复的"停顿"在same line
            (r'\*\(停顿\)\*\s+\*\(停顿\)\*', '*(停顿)*'),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            new_text = re.sub(pattern, replacement, self.text)
            if new_text != self.text:
                count = len(re.findall(pattern, self.text))
                self.changes.append(f"✓ 对话指示简化: {pattern[:30]}... ({count}处)")
                self.text = new_text
                modified = True
        
        return modified
    
    def remove_redundant_descriptions(self):
        """删除舞台指示中的冗余描述"""
        # 删除过长的、过于文学化的舞台指示
        patterns = [
            # 删除"投出/投射"这类冗余的光线描写
            (r'投出.*?的光', '的光'),
            (r'投射出', ''),
            
            # 简化'场景'描写中的冗余
            (r'，压迫感十足', ''),
            (r'，不稳定的', ''),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            new_text = re.sub(pattern, replacement, self.text)
            if new_text != self.text:
                count = len(re.findall(pattern, self.text))
                self.changes.append(f"✓ 冗余描述删除: {pattern[:30]}... ({count}处)")
                self.text = new_text
                modified = True
        
        return modified
    
    def enhance_authenticity(self):
        """增强真实性——删除过于诗意化的表述"""
        patterns = [
            # 删除AI高频的极值修饰词
            (r'最.*?的是', ''),
            (r'真正.*?的是', ''),
            (r'更.*?的是', ''),
            
            # 删除"一种"这种模糊量词（AI常用）
            (r'一种', ''),
            
            # 删除"几乎"（AI常用的表达不确定的词）
            (r'几乎', ''),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            new_text = re.sub(pattern, replacement, self.text)
            if new_text != self.text:
                count = len(re.findall(pattern, self.text))
                self.changes.append(f"✓ 真实性增强: {pattern[:30]}... ({count}处)")
                self.text = new_text
                modified = True
        
        return modified
    
    def process(self) -> str:
        """执行完整的De-AI处理流程"""
        print(f"\n🎭 开始处理: {self.filepath.name}")
        print(f"   原始文本: {self.original_len:,} 字符\n")
        
        print("🔧 执行De-AI处理（v1.1 改进规则）...")
        self.remove_stage_instruction_bloat()
        self.remove_narrative_intrusion()
        self.simplify_dialogue_directions()
        self.remove_redundant_descriptions()
        self.enhance_authenticity()
        
        print(f"\n✅ 处理完成:")
        print(f"   共进行 {len(self.changes)} 类优化")
        for change in self.changes:
            print(f"   {change}")
        
        final_len = len(self.text)
        reduction = self.original_len - final_len
        print(f"\n📊 统计:")
        print(f"   原始: {self.original_len:,} 字符")
        print(f"   处理后: {final_len:,} 字符")
        print(f"   删减: {reduction:,} 字符 ({reduction/self.original_len*100:.1f}%)")
        
        return self.text
    
    def save(self, output_path: str = None) -> str:
        """保存处理结果"""
        if output_path is None:
            # 默认生成带时间戳的文件名
            stem = self.filepath.stem
            suffix = self.filepath.suffix
            timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.filepath.parent / f"{stem}_DeAI纯净版_{timestamp}{suffix}"
        
        output_file = Path(output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self.text)
        
        print(f"\n✨ 文件已保存")
        print(f"   位置: {output_file}")
        print(f"   文件大小: {output_file.stat().st_size / 1024:.1f} KB")
        
        return str(output_file)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="话剧舞台脚本De-AI处理器 v1.1")
    parser.add_argument('--file', type=str, required=True, help='输入文件路径')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径（可选）')
    
    args = parser.parse_args()
    
    processor = DramaDeAIProcessor(args.file)
    processor.process()
    processor.save(args.output)


if __name__ == '__main__':
    main()
