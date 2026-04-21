#!/usr/bin/env python3
"""
DramaRAG — 话剧理论知识库检索系统 v2.0
使用通义千问 (DashScope) Embedding API + ChromaDB 本地向量库

用法:
  python scripts/drama_rag.py --ingest          # 建立知识库索引（首次运行）
  python scripts/drama_rag.py --query '关键词'  # 检索相关理论片段
  python scripts/drama_rag.py --status          # 查看索引状态
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict

from openai import OpenAI
import chromadb
from dotenv import load_dotenv

# === 加载环境变量 ===
# 支持从项目根目录加载
_repo_root = Path(__file__).parent.parent
load_dotenv(_repo_root / ".env")

# === 配置常量 ===
KNOWLEDGE_DIR = _repo_root / "knowledge"
DB_DIR        = _repo_root / "db" / "theory"
COLLECTION    = "drama_theory"

DASHSCOPE_API_KEY  = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDING_MODEL    = "text-embedding-v3"

CHUNK_SIZE    = 800   # 单块最大字符数
CHUNK_OVERLAP = 150   # 相邻块重叠字符数
EMBED_BATCH   = 10    # 每批向量化条数（DashScope 上限 10）


# ─────────────────────────────────────────────
class DramaRAG:
    """话剧理论 RAG 核心类"""

    def __init__(self):
        if not DASHSCOPE_API_KEY:
            print("❌ 未找到 DASHSCOPE_API_KEY，请检查项目根目录的 .env 文件。")
            sys.exit(1)

        self.llm_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self.chroma = chromadb.PersistentClient(path=str(DB_DIR))
        self.col = self.chroma.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Embedding ──────────────────────────────
    def _embed(self, texts: List[str]) -> List[List[float]]:
        """调用 DashScope text-embedding-v3，返回向量列表"""
        resp = self.llm_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
            dimensions=1024,
        )
        return [item.embedding for item in resp.data]

    # ── 文本切割 ───────────────────────────────
    def _split_markdown(self, text: str, source: str) -> List[Dict]:
        """
        智能 Markdown 切割：
        1. 优先按二级标题 (##) 切割，保留理论逻辑单元
        2. 若段落超长，按 \n\n 继续切割，并做 overlap 拼接
        """
        chunks: List[Dict] = []
        sections = re.split(r'\n(?=#{1,3}\s)', text)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            title_m = re.match(r'^#{1,3}\s+(.+)', section)
            title   = title_m.group(1).strip() if title_m else "通用理论"

            if len(section) <= CHUNK_SIZE:
                chunks.append({"text": section, "source": source, "title": title})
                continue

            # 超长：按段落再切
            paras = re.split(r'\n\n+', section)
            current = ""
            for para in paras:
                if len(current) + len(para) + 2 <= CHUNK_SIZE:
                    current = (current + "\n\n" + para).strip() if current else para
                else:
                    if current:
                        chunks.append({"text": current, "source": source, "title": title})
                    # overlap 保留上一块最后 CHUNK_OVERLAP 字
                    overlap = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
                    current = (overlap + "\n\n" + para).strip() if overlap else para
            if current:
                chunks.append({"text": current, "source": source, "title": title})

        return chunks

    # ── 建立索引 ───────────────────────────────
    def ingest(self):
        """读取 knowledge/*.md，分块、向量化并存入 ChromaDB"""
        md_files = sorted(KNOWLEDGE_DIR.glob("*.md"))
        if not md_files:
            print(f"❌ {KNOWLEDGE_DIR} 下没有找到 .md 文件，请确认知识库文件已存在。")
            return

        print(f"📚 发现 {len(md_files)} 个知识库文件，开始索引...\n")
        total = 0

        for md_file in md_files:
            size_kb = md_file.stat().st_size // 1024
            print(f"  ▸ {md_file.name}  ({size_kb} KB)")
            text   = md_file.read_text(encoding="utf-8")
            chunks = self._split_markdown(text, md_file.stem)
            if not chunks:
                continue

            # 批量向量化
            for i in range(0, len(chunks), EMBED_BATCH):
                batch    = chunks[i : i + EMBED_BATCH]
                texts    = [c["text"] for c in batch]
                ids      = [f"{md_file.stem}__{i + j}" for j in range(len(batch))]

                # 跳过已存在的 id
                existing = set(self.col.get(ids=ids)["ids"])
                new_idx  = [j for j, id_ in enumerate(ids) if id_ not in existing]
                if not new_idx:
                    print(f"    ↩ 块 {i}~{i+len(batch)} 已在索引中，跳过", end="\r")
                    continue

                nb     = [batch[j] for j in new_idx]
                nt     = [texts[j] for j in new_idx]
                ni     = [ids[j]   for j in new_idx]
                embeds = self._embed(nt)

                self.col.add(
                    documents=nt,
                    embeddings=embeds,
                    metadatas=[{"source": c["source"], "title": c["title"]} for c in nb],
                    ids=ni,
                )
                print(f"    ✓ 已处理 {i + len(batch)}/{len(chunks)} 块", end="\r")

            total += len(chunks)
            print(f"    ✓ {md_file.name}: {len(chunks)} 块已入库          ")

        print(f"\n✅ 索引完成！共 {total} 个理论片段已存入向量库。")
        print(f"   数据库路径: {DB_DIR}\n")

    # ── 检索 ───────────────────────────────────
    def query(self, query_text: str, k: int = 3) -> str:
        """语义检索，返回格式化 Markdown，供 Claude 注入提示"""
        count = self.col.count()
        if count == 0:
            return (
                "⚠️ **向量库为空**，请先运行：\n"
                "```bash\n"
                "python scripts/drama_rag.py --ingest\n"
                "```"
            )

        q_embed = self._embed([query_text])[0]
        results = self.col.query(
            query_embeddings=[q_embed],
            n_results=min(k, count),
            include=["documents", "metadatas", "distances"],
        )

        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]

        lines = [
            f"## 📖 RAG 理论检索 — 查询：「{query_text}」",
            f"*从 {count} 个理论片段中检索，返回相关度最高的 {len(docs)} 条*",
            "",
            "---",
            "",
        ]
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
            sim = round((1 - dist) * 100, 1)
            lines += [
                f"### [{i}] 《{meta['source']}》· {meta['title']}  （相关度: {sim}%）",
                "",
                doc,
                "",
                "---",
                "",
            ]

        return "\n".join(lines)

    # ── 状态检查 ───────────────────────────────
    def status(self):
        """查看当前索引状态"""
        count = self.col.count()
        print(f"\n📊 向量库状态")
        print(f"   路径      : {DB_DIR}")
        print(f"   总片段数  : {count}")

        if count == 0:
            print("   ⚠️  尚未建立索引，请运行 --ingest")
            return

        sample  = self.col.get(limit=count, include=["metadatas"])
        sources: Dict[str, int] = {}
        for meta in sample["metadatas"]:
            src = meta.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        print("   来源分布  :")
        for src, cnt in sorted(sources.items()):
            print(f"     《{src}》: {cnt} 块")
        print()


# ─────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    rag = DramaRAG()
    cmd = sys.argv[1]

    if cmd == "--ingest":
        rag.ingest()

    elif cmd == "--query":
        if len(sys.argv) < 3:
            print("❌ 请提供查询关键词，例如：--query '师徒冲突'")
            sys.exit(1)
        print(rag.query(sys.argv[2]))

    elif cmd == "--status":
        rag.status()

    else:
        print(f"❌ 未知命令：{cmd}")
        print("支持的命令：--ingest | --query '关键词' | --status")
        sys.exit(1)


if __name__ == "__main__":
    main()
