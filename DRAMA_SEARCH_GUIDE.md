# DramaSearch 使用指南

## 概览

`drama_search.py` 是 **Drama Genius v2.0** 工作流中 `/start` 步骤的核心工具。它支持**多源搜索** + **AI 智能提取**，为剧本创作快速生成素材库。

---

## 工作流集成

### 在 `/start` 步骤中调用

```bash
# 标准用法
python3 scripts/drama_search.py \
  --search "反腐剧" \
  --name "权力的游戏" \
  --verbose

# 演示模式（快速查看输出格式）
python3 scripts/drama_search.py --demo
```

### 输出物

成功搜索后，在 `output/` 目录生成 `[剧名]_素材库.md`，包含：

1. **搜索素材来源** — Bocha API（中文）+ 百度热搜 + Exa AI（英文，可选）
2. **冲突点分析** — 3 个核心戏剧冲突点（LLM 自动提取）
3. **人物心理档案** — N 个人物的隐性心理动机
4. **可舞台化动作** — 5 个具有视觉冲击力的动作瞬间

---

## 快速开始

### 方案 1：使用演示数据（立即体验）

```bash
python3 scripts/drama_search.py --demo
```

✅ 输出：`output/反腐剧示例_素材库.md`

**查看文件**：
```bash
cat output/反腐剧示例_素材库.md
```

---

### 方案 2：使用真实搜索（需要 API 配置）

#### 前置：配置 API Key

编辑 `.env` 文件：

```env
# 必要（已配置）
DASHSCOPE_API_KEY=sk-xxx...

# 可选（中文搜索）
BOCHA_API_KEY=your_bocha_key_here
```

获取 Bocha API Key：https://open.bochaai.com/

#### 执行搜索

```bash
# 基础用法
python3 scripts/drama_search.py --search "反腐剧"

# 指定剧名
python3 scripts/drama_search.py --search "反腐案例" --name "官场风云"

# 详细输出（显示每条搜索结果）
python3 scripts/drama_search.py --search "反腐" --verbose
```

---

## 命令参数

| 参数 | 说明 | 示例 |
|-----|------|------|
| `--search` | 搜索关键词（必需） | `--search "反腐剧"` |
| `--name` | 输出文件的剧名前缀 | `--name "权力对峙"` |
| `--verbose` | 显示详细搜索过程 | `--verbose` |
| `--demo` | 演示模式（示例输出） | `--demo` |

---

## 搜索源说明

### Bocha API（中文搜索）
- **优势**：中文内容搜索最佳、支持新闻/网页/微博等多源
- **配置**：需要 `BOCHA_API_KEY`
- **成本**：付费 API
- **回退**：若 API Key 无效，自动跳过

### 百度热搜爬虫（轻量级中文）
- **优势**：实时热点、无需 API Key
- **配置**：无需配置
- **缺点**：可能因反爬虫被拒
- **回退**：网络问题或解析失败时，自动跳过

### Exa AI（英文搜索）
- **优势**：高质量英文内容搜索
- **配置**：需要集成 MCP（可选）
- **状态**：当前为可选集成点

---

## LLM 智能提取

搜索完成后，自动调用 DashScope（通义千问）进行**语义理解**和**编剧化提取**：

### 提取内容

1. **冲突点分析**
   - 从真实素材中识别戏剧张力最强的 3 个冲突
   - 符合 Egri 编剧法的"对立"原则

2. **人物心理档案**
   - 提取隐性心理动机（而非表面行为）
   - 符合斯坦尼实验剧院的"最高任务"理论

3. **可舞台化动作**
   - 提取具有视觉冲击力的 5 个动作瞬间
   - 符合 drama-specs.md 的"动作提示规范"

---

## 输出文件结构

```
output/
├── 反腐剧示例_素材库.md          ← 演示文件
├── 权力对峙_素材库.md            ← 真实搜索输出
└── ...
```

### 文件内容示例

```markdown
# [剧名] — 素材库

## 一、搜索素材来源

### Bocha 搜索结果 (N 条)
- [1] 标题 → 摘要
- [2] 标题 → 摘要

### 百度搜索结果 (M 条)
- [1] 标题 → 摘要

## 二、冲突点分析

**1. [冲突点 1]**
**2. [冲突点 2]**
**3. [冲突点 3]**

## 三、人物心理档案

- **人物 A**：心理动机
- **人物 B**：心理动机

## 四、可舞台化动作瞬间

**1. [动作描述 + 心理暗示]**
**2. [动作描述 + 心理暗示]**
...
```

---

## 与 DRAMA_GENIUS_SKILL.md 的整合

### `/start` 步骤工作流

```
用户输入 /start + 故事类型（如："反腐剧"）
  ↓
执行搜索脚本
  python3 scripts/drama_search.py --search "反腐剧" --name "XXX"
  ↓
生成素材库（Markdown 文件）
  ↓
展示给用户：3 个冲突点 + 人物档案 + 动作瞬间
  ↓
用户确认 → 初始化 MEMORY.md
  ↓
进入 `/outline` 步骤
```

---

## 常见问题

### Q1: 搜索失败，返回 "No materials found"

**原因**：
- Bocha API Key 无效或网络问题
- 百度爬虫被反爬虫机制阻止

**解决**：
1. 检查 `.env` 中的 `BOCHA_API_KEY` 是否有效
2. 尝试使用 `--demo` 模式验证脚本功能
3. 检查网络连接

### Q2: 如何只使用某个搜索源？

**当前**：脚本会自动尝试所有可用源  
**计划**：未来版本可添加 `--source bocha|baidu|exa` 参数

### Q3: 可以自定义 LLM 提取的内容吗？

**可以**：修改 `_extract_conflicts()`, `_extract_character_motives()`, `_extract_stage_moments()` 中的 `prompt` 参数

### Q4: 如何集成自己的搜索源？

在 `DramaSearch` 类中添加新方法，例如：
```python
def _search_custom_source(self, query: str) -> List[Dict]:
    # 实现你的搜索逻辑
    return results
```

然后在 `search()` 方法中调用。

---

## 下一步

生成素材库后，进入 `/outline` 步骤：

```bash
# 在 /outline 步骤中，RAG 会帮助创作大纲
python3 scripts/drama_rag.py --query "[主题] 三幕结构 人物弧光"
```

---

## 技术栈

- **LLM 调用**：OpenAI SDK + DashScope（通义千问）
- **网页爬虫**：requests + BeautifulSoup4
- **搜索 API**：Bocha API
- **本地存储**：output/ 目录的 Markdown 文件

---

## 许可

本工具为 Drama Genius v2.0 的一部分，遵循项目许可协议。
