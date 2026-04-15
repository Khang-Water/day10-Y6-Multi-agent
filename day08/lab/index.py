"""
index.py - Sprint 1: Build RAG Index
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List
from config import (
    DOCS_DIR,
    CHROMA_DB_DIR,
    CHUNK_SIZE_TOKENS as CHUNK_SIZE,
    CHUNK_OVERLAP_TOKENS as CHUNK_OVERLAP,
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
)

try:
    from dotenv import load_dotenv
except Exception:
    # Keep scripts runnable even when python-dotenv is not installed.
    def load_dotenv() -> bool:
        return False

# Reuse clients/models so we do not recreate them for every call.
_OPENAI_EMBED_CLIENT = None
_ST_EMBED_MODEL = None


# =============================================================================
# STEP 1: PREPROCESS
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Extract metadata from header, then clean main text.
    """
    lines = raw_text.splitlines()
    metadata = {
        "source": filepath,
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines: List[str] = []
    header_done = False

    # Accept lines like "Key: Value" in header.
    meta_pattern = re.compile(r"^\s*([A-Za-z ]+)\s*:\s*(.+?)\s*$")

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not header_done:
            # TODO: Parse metadata tu cac dong "Key: Value"
            match = meta_pattern.match(stripped)
            if match:
                key = match.group(1).strip().lower()
                value = match.group(2).strip()
                if key == "source":
                    metadata["source"] = value
                elif key == "department":
                    metadata["department"] = value
                elif key == "effective date":
                    metadata["effective_date"] = value
                elif key == "access":
                    metadata["access"] = value
                continue

            if stripped.startswith("==="):
                header_done = True
                content_lines.append(stripped)
                continue

            # Skip title/empty lines while still in header.
            if stripped == "" or stripped.isupper():
                continue

            # If text already starts here, stop header mode.
            header_done = True
            content_lines.append(stripped)
            continue

        content_lines.append(line)

    cleaned_text = "\n".join(content_lines)

    # TODO: Them buoc normalize text neu can
    # Keep this normalization lightweight and predictable.
    cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
    cleaned_text = re.sub(r"[ \t]*\n[ \t]*", "\n", cleaned_text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    cleaned_text = cleaned_text.strip()

    return {"text": cleaned_text, "metadata": metadata}


# =============================================================================
# STEP 2: CHUNK
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Split document by section heading first, then by size.
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks: List[Dict[str, Any]] = []

    # TODO: Implement chunking theo section heading
    # Split by heading pattern "=== ... ===" and keep headings in result.
    parts = re.split(r"(===.*?===)", text)

    current_section = "General"
    current_section_text = ""

    for part in parts:
        if not part:
            continue

        if re.match(r"===.*?===", part.strip()):
            if current_section_text.strip():
                chunks.extend(
                    _split_by_size(
                        current_section_text.strip(),
                        base_metadata=base_metadata,
                        section=current_section,
                    )
                )
            current_section = part.strip("= ").strip()
            current_section_text = ""
            continue

        current_section_text += part

    if current_section_text.strip():
        chunks.extend(
            _split_by_size(
                current_section_text.strip(),
                base_metadata=base_metadata,
                section=current_section,
            )
        )

    return chunks


def _find_natural_cut(text: str, max_chars: int) -> int:
    """
    Find a natural cut before max_chars when possible.
    """
    if len(text) <= max_chars:
        return len(text)

    window = text[:max_chars]
    # Prefer newline/sentence boundaries over hard cut.
    candidates = [window.rfind("\n"), window.rfind(". "), window.rfind("; "), window.rfind(", ")]
    best = max(candidates)
    if best >= int(max_chars * 0.6):
        return best + 1
    return max_chars


def _split_by_size(
    text: str,
    base_metadata: Dict[str, Any],
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """
    Split long section into chunk-sized blocks with overlap.
    """
    if len(text) <= chunk_chars:
        return [{"text": text, "metadata": {**base_metadata, "section": section}}]

    # TODO: Implement split theo paragraph voi overlap
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    raw_chunks: List[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= chunk_chars:
            current = candidate
            continue

        if current:
            raw_chunks.append(current)
            current = para
            continue

        # Paragraph itself is too long, so split by natural boundary.
        temp = para
        while len(temp) > chunk_chars:
            cut = _find_natural_cut(temp, chunk_chars)
            raw_chunks.append(temp[:cut].strip())
            temp = temp[cut:].lstrip()
        if temp:
            current = temp

    if current:
        raw_chunks.append(current)

    chunks: List[Dict[str, Any]] = []
    for idx, base_chunk in enumerate(raw_chunks):
        # TODO: Tim ranh gioi tu nhien gan nhat (dau xuong dong, dau cham)
        # Add overlap from previous chunk so retriever sees local context continuity.
        if idx == 0:
            chunk_text = base_chunk
        else:
            overlap = raw_chunks[idx - 1][-overlap_chars:].strip()
            chunk_text = f"{overlap}\n{base_chunk}" if overlap else base_chunk
            if len(chunk_text) > (chunk_chars + overlap_chars):
                chunk_text = chunk_text[: chunk_chars + overlap_chars].strip()

        chunks.append({"text": chunk_text, "metadata": {**base_metadata, "section": section}})

    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """
    Build embedding vector for input text.
    """
    global _OPENAI_EMBED_CLIENT, _ST_EMBED_MODEL

    clean_text = (text or "").strip() or " "

    # TODO Sprint 1:
    # Option A - OpenAI embeddings
    if OPENAI_API_KEY:
        if _OPENAI_EMBED_CLIENT is None:
            from openai import OpenAI

            _OPENAI_EMBED_CLIENT = OpenAI(api_key=OPENAI_API_KEY, base_url="https://models.inference.ai.azure.com/")

        response = _OPENAI_EMBED_CLIENT.embeddings.create(
            input=clean_text,
            model=OPENAI_EMBEDDING_MODEL,
        )
        return response.data[0].embedding

    # Option B - local sentence-transformers fallback
    if _ST_EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer

        _ST_EMBED_MODEL = SentenceTransformer(LOCAL_EMBEDDING_MODEL)

    return _ST_EMBED_MODEL.encode(clean_text).tolist()


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Full pipeline: read docs -> preprocess -> chunk -> embed -> upsert.
    """
    import chromadb

    print(f"Dang build index tu: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # TODO: Khoi tao ChromaDB
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0
    doc_files = list(docs_dir.glob("*.txt"))
    if not doc_files:
        print(f"Khong tim thay file .txt trong {docs_dir}")
        return

    for filepath in doc_files:
        print(f"  Processing: {filepath.name}")
        raw_text = filepath.read_text(encoding="utf-8")

        # TODO: Goi preprocess_document
        doc = preprocess_document(raw_text, str(filepath))
        # TODO: Goi chunk_document
        chunks = chunk_document(doc)

        # TODO: Embed va luu tung chunk vao ChromaDB
        # Keep this loop straightforward to make debugging easy.
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath.stem}_{i}"
            embedding = get_embedding(chunk["text"])
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
            )

        total_chunks += len(chunks)
        print(f"    Indexed {len(chunks)} chunks")

    print(f"\nHoan thanh! Tong so chunks: {total_chunks}")
    print("Embedding + ChromaDB upsert hoan tat.")


# =============================================================================
# STEP 4: INSPECT
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    """
    Print first n chunks to inspect quality.
    """
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])

        print(f"\n=== Top {n} chunks trong index ===\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i + 1}]")
            print(f"  Source: {meta.get('source', 'N/A')}")
            print(f"  Section: {meta.get('section', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Text preview: {doc[:120]}...")
            print()
    except Exception as exc:
        print(f"Loi khi doc index: {exc}")
        print("Hay chay build_index() truoc.")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Check metadata distribution over all chunks.
    """
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])

        print(f"\nTong chunks: {len(results['metadatas'])}")

        # TODO: Phan tich metadata
        departments: Dict[str, int] = {}
        missing_date = 0
        for meta in results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1
            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print("Phan bo theo department:")
        for dept, count in sorted(departments.items(), key=lambda item: item[0]):
            print(f"  {dept}: {count} chunks")
        print(f"Chunks thieu effective_date: {missing_date}")

    except Exception as exc:
        print(f"Loi: {exc}. Hay chay build_index() truoc.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    doc_files = list(DOCS_DIR.glob("*.txt"))
    print(f"\nTim thay {len(doc_files)} tai lieu:")
    for file in doc_files:
        print(f"  - {file.name}")

    print("\n--- Test preprocess + chunking ---")
    if doc_files:
        sample_path = doc_files[0]
        raw = sample_path.read_text(encoding="utf-8")
        doc = preprocess_document(raw, str(sample_path))
        chunks = chunk_document(doc)
        print(f"\nFile: {sample_path.name}")
        print(f"  Metadata: {doc['metadata']}")
        print(f"  So chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  [Chunk {i + 1}] Section: {chunk['metadata']['section']}")
            print(f"  Text: {chunk['text'][:150]}...")

    print("\n--- Build Full Index ---")
    # Uncomment neu ban muon build index ngay:
    build_index()

    # Uncomment sau khi build index:
    list_chunks()
    inspect_metadata_coverage()

    print("\nSprint 1 setup hoan thanh!")
    print("Goi y tiep theo:")
    print("  1. Bo sung API key neu muon dung OpenAI embedding")
    print("  2. Uncomment build_index() de tao vector store")
    print("  3. Dung list_chunks() va inspect_metadata_coverage() de kiem tra du lieu")
