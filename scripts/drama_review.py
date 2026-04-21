#!/usr/bin/env python3
"""
剧本虚拟导演审阅系统 — 基于drama-specs规范的质检
"""

import re
from pathlib import Path

class VirtualDirectorReview:
    def __init__(self, script_path):
        self.script_path = Path(script_path)
        self.script_content = self.script_path.read_text(encoding='utf-8')
        self.issues = []
        self.suggestions = []
        
    def check_on_the_nose(self):
        """检查广播剧化台词（直接说出内心感受）"""
        on_the_nose_patterns = [
            r'(我现在|我感到|我觉得|我很|我是)(非常|很)(害怕|愤怒|伤心|委屈|失望)',
            r'(这让我|这使我|我因此)(感到很)',
            r'(我的内心|我心里)(想着|在想)',
        ]
        
        for pattern in on_the_nose_patterns:
            matches = re.finditer(pattern, self.script_content)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(self.script_content), match.end() + 50)
                context = self.script_content[start:end]
                self.issues.append({
                    'type': '广播剧化台词',
                    'severity': 'high',
                    'context': context.replace('\n', ' ')[:60],
                    'suggestion': '将内心感受转化为身体动作或隐性对话'
                })
    
    def check_conflict_density(self):
        """检查500字内冲突密度"""
        # 简单计算：分段检查
        sections = self.script_content.split('\n\n')
        for i, section in enumerate(sections):
            word_count = len(section)
            if word_count > 500:
                conflict_markers = len(re.findall(r'(但|然而|反驳|对抗|冲突|打断|拒绝)', section))
                if conflict_markers < 3:
                    self.issues.append({
                        'type': '冲突密度不足',
                        'severity': 'medium',
                        'section': i,
                        'word_count': word_count,
                        'suggestion': f'这段{word_count}字中冲突太少，建议增加权力转移或价值观碰撞'
                    })
    
    def check_scene_headers(self):
        """检查场景头频率"""
        scene_headers = re.findall(r'\[时间：(.+?)\]', self.script_content)
        if len(scene_headers) > 3:
            self.suggestions.append({
                'type': '场景头频率',
                'severity': 'medium',
                'current': len(scene_headers),
                'suggestion': '场景头过多（{}个），考虑合并同一空间内的连贯叙事'.format(len(scene_headers))
            })
    
    def check_action_indicators(self):
        """检查动作指示的心理外化"""
        # 检查是否有足够的动作指示 (xxx) 格式
        action_count = len(re.findall(r'\([^)]*\)', self.script_content))
        dialogue_count = len(re.findall(r'^[^\[\(]*:', self.script_content, re.MULTILINE))
        
        if dialogue_count > 0:
            ratio = action_count / dialogue_count
            if ratio < 0.4:
                self.issues.append({
                    'type': '动作指示不足',
                    'severity': 'medium',
                    'ratio': ratio,
                    'suggestion': '动作指示与台词比例较低，应该增加更多心理外化的动作'
                })
    
    def check_cause_and_effect(self):
        """检查幕尾的因果钩子"""
        if '【第' in self.script_content:
            acts = re.findall(r'【第(.+?)幕.*?终】', self.script_content)
            if len(acts) > 1:
                for i in range(len(acts) - 1):
                    self.suggestions.append({
                        'type': '因果钩子',
                        'severity': 'info',
                        'current_act': acts[i],
                        'check': f'确认第{acts[i]}幕结尾是否为第{acts[i+1]}幕的驱动力'
                    })
    
    def generate_report(self):
        """生成审阅报告"""
        print("\n" + "="*60)
        print("🎭 虚拟导演质检报告 - 《零工困局》")
        print("="*60 + "\n")
        
        # 执行所有检查
        self.check_on_the_nose()
        self.check_conflict_density()
        self.check_scene_headers()
        self.check_action_indicators()
        self.check_cause_and_effect()
        
        # 显示问题
        if self.issues:
            print("❌ 发现问题：\n")
            for idx, issue in enumerate(self.issues[:5], 1):  # 只显示前5个
                print(f"{idx}. 【{issue['type']}】严重程度：{issue['severity']}")
                print(f"   → 问题: {issue.get('context', issue.get('suggestion', ''))}")
                print(f"   → 建议: {issue.get('suggestion', issue.get('suggestion', ''))}\n")
        
        # 显示建议
        if self.suggestions:
            print("\n💡 改进建议：\n")
            for idx, sug in enumerate(self.suggestions, 1):
                print(f"{idx}. 【{sug['type']}】")
                print(f"   → {sug.get('suggestion', sug.get('check', ''))}\n")
        
        print("="*60)
        print(f"✅ 审阅完成。共发现 {len(self.issues)} 个问题，{len(self.suggestions)} 条建议\n")
        
        return {
            'issues_count': len(self.issues),
            'suggestions_count': len(self.suggestions),
            'issues': self.issues,
            'suggestions': self.suggestions
        }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python review.py <脚本文件路径>")
        sys.exit(1)
    
    script_path = sys.argv[1]
    review = VirtualDirectorReview(script_path)
    review.generate_report()
