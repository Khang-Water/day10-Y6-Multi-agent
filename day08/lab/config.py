"""
config.py — Tập trung tất cả thông số fine-tune cho RAG Pipeline
Chỉnh sửa các giá trị dưới để cải thiện độ chính xác.

Quy tắc: Chỉ đổi MỘT thông số mỗi lần rồi chạy eval.py để so sánh A/B.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# 🏠 PATHS
# =============================================================================

PROJECT_DIR = Path(__file__).parent
DOCS_DIR = PROJECT_DIR / "data" / "docs"
CHROMA_DB_DIR = PROJECT_DIR / "chroma_db"
RESULTS_DIR = PROJECT_DIR / "results"
TEST_QUESTIONS_PATH = PROJECT_DIR / "data" / "test_questions.json"

# =============================================================================
# 1️⃣ CHUNKING CONFIG (Sprint 1)
# Ảnh hưởng: 30% độ chính xác
# =============================================================================

# Số ký tự tương đương ≈ tokens / 4 (dùng ước lượng)
# Nhỏ hơn → retrieve chính xác, nhưng thiếu context
# Lớn hơn → có đủ context, nhưng nhiễu
CHUNK_SIZE_TOKENS = 400  # Token (~ 1600 ký tự)
CHUNK_OVERLAP_TOKENS = 80  # Token (~ 320 ký tự)

# Cách chuyển sang ký tự (nếu cần)
CHUNK_SIZE_CHARS = CHUNK_SIZE_TOKENS * 4
CHUNK_OVERLAP_CHARS = CHUNK_OVERLAP_TOKENS * 4

# Chunking strategy: "heading-based", "paragraph-based", "hybrid"
CHUNKING_STRATEGY = "hybrid"

# =============================================================================
# 2️⃣ EMBEDDING CONFIG (Ai dùng khi index)
# =============================================================================

# OpenAI (ưu tiên nếu có key)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# Groq (OpenAI-compatible chat endpoint)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Gemini / Google
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Local (fallback)
LOCAL_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
# =============================================================================
# 3️⃣ RETRIEVAL CONFIG (Sprint 2-3)
# Ảnh hưởng: 40% độ chính xác
# =============================================================================

# Số chunk lấy từ vector store (search rộng)
TOP_K_SEARCH_BASE = 10  # ← Tăng lên 15-20 để lấy nhiều hơn
TOP_K_SEARCH_VARI = 15  # ← Tăng lên 15-20 để lấy nhiều hơn


# Số chunk giữ lại sau rerank (final)
TOP_K_SELECT_BASE = 3  # ← Tăng lên 5-7 để đưa nhiều context vào prompt (nhưng tốn token)
TOP_K_SELECT_VARI = 5  # ← Tăng lên 5-7 để đưa nhiều context vào prompt (nhưng tốn token)


# Retrieval mode: "dense" (semantic), "sparse" (keyword), "hybrid" (kết hợp)
RETRIEVAL_MODE_BASE = "dense"  # ← Thử "hybrid" để cải thiện (nhất là alias query)
RETRIEVAL_MODE_VARI = "hybrid"  # ← Thử "hybrid" để cải thiện (nhất là alias query)

# RRF (Reciprocal Rank Fusion) constant - dùng khi hybrid
RRF_K = 60

# Trọng số: dense vs sparse
DENSE_WEIGHT = 0.5  # ← Semantic
SPARSE_WEIGHT = 0.5  # ← Keyword

# Ngưỡng tin cậy: nếu dưới này → abstain (không trả lời)
# Nhỏ hơn → ít abstain, nhưng hay bịa
# Lớn hơn → conservative, hay nói "không đủ dữ liệu"
MIN_CONFIDENCE = 0.18  # ← Giảm xuống 0.10-0.15 nếu muốn ít abstain

# =============================================================================
# 4️⃣ RERANK CONFIG (Sprint 3)
# Ảnh hưởng: 15% độ chính xác
# =============================================================================

# Có dùng cross-encoder rerank không?
USE_RERANK_BASE = False  # ← Thử True nếu dense retrieve có noise nhiều
USE_RERANK_VARI = False  # ← Thử True nếu dense retrieve có noise nhiều

# Model rerank (chỉ dùng khi USE_RERANK=True)
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # English
# RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # Đa ngôn ngữ (bao gồm Việt)

# =============================================================================
# 5️⃣ LLM CONFIG (Sprint 2)
# Ảnh hưởng: 10% độ chính xác
# =============================================================================

# Provider: đọc từ .env → LLM_PROVIDER=openai | gemini | groq
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# Model LLM — tự động chọn theo LLM_PROVIDER
if LLM_PROVIDER == "gemini":
    LLM_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
elif LLM_PROVIDER == "groq":
    LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
else:
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Temperature: 0 = deterministic (tốt cho eval), >0 = creative
LLM_TEMPERATURE = 0

# Max tokens cho answer
LLM_MAX_TOKENS = 512

# =============================================================================
# 6️⃣ EVALUATION CONFIG (Sprint 4)
# =============================================================================

# BASELINE config (dùng cho eval.py)
BASELINE_CONFIG = {
    "retrieval_mode": RETRIEVAL_MODE_BASE,
    "top_k_search": TOP_K_SEARCH_BASE,
    "top_k_select": TOP_K_SELECT_BASE,
    "use_rerank": USE_RERANK_BASE,
    "label": "baseline_dense",
}

# VARIANT config (dùng để so sánh A/B)
# Chỉ đổi MỘT thông số so với BASELINE
VARIANT_CONFIG = {
    "retrieval_mode": RETRIEVAL_MODE_VARI,  # ← Đổi từ "dense" → "hybrid"
    "top_k_search": TOP_K_SEARCH_VARI,
    "top_k_select": TOP_K_SELECT_VARI,
    "use_rerank": USE_RERANK_VARI,
    "label": "variant_hybrid",
}

# =============================================================================
# 🔧 QUICK TUNE TEMPLATES (copy-paste để nhanh)
# =============================================================================

"""
TEMPLATE 1: Tăng Recall (lấy nhiều chunk hơn)
TOP_K_SEARCH = 20
TOP_K_SELECT = 5
MIN_CONFIDENCE = 0.10
VARIANT_CONFIG["retrieval_mode"] = "hybrid"

TEMPLATE 2: Tăng Precision (chọn chunk tốt nhất)
TOP_K_SEARCH = 10
TOP_K_SELECT = 3
USE_RERANK = True
VARIANT_CONFIG["use_rerank"] = True

TEMPLATE 3: Hybrid + Rerank (tối ưu nhất)
RETRIEVAL_MODE = "hybrid"
USE_RERANK = True
MIN_CONFIDENCE = 0.12
VARIANT_CONFIG = ...

TEMPLATE 4: Conservative (ít abstain)
MIN_CONFIDENCE = 0.05
TOP_K_SEARCH = 15
VARIANT_CONFIG["min_confidence"] = 0.05

TEMPLATE 5: Ultra-precise (nhiều abstain)
MIN_CONFIDENCE = 0.30
TOP_K_SEARCH = 5
USE_RERANK = True
"""

# =============================================================================
# 📊 TUNING GUIDE
# =============================================================================

TUNING_GUIDE = """
Hướng dẫn Fine-tune:

1. Bắt đầu với BASELINE (current config)
2. Chọn 1 TEMPLATE hoặc 1 thông số để thay đổi
3. Chạy: python eval.py
4. Xem scorecard → delta (baseline vs variant)
5. Nếu tốt hơn → cập nhật BASELINE_CONFIG
6. Lặp lại với thông số khác

Thứ tự ưu tiên tune (hiệu quả giảm dần):
1. TOP_K_SEARCH (10→20): +5-10% recall
2. RETRIEVAL_MODE ("dense"→"hybrid"): +5-15% (nếu có alias/keyword)
3. USE_RERANK (False→True): +3-10% precision
4. MIN_CONFIDENCE (0.18→0.10): -abstain, +5% (nhưng risk hallucinate)
5. CHUNK_SIZE: +2-5% (nếu chunking bị cắt giữa)

Cảnh báo:
- Tăng TOP_K_SELECT & RERANK = tốn nhiều token (cost ↑)
- Giảm MIN_CONFIDENCE = tăng risk bịa thông tin
- Hybrid + Rerank = chậm hơn (~2-3s per query)
"""

if __name__ == "__main__":
    print(TUNING_GUIDE)
