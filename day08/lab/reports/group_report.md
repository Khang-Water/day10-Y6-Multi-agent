# Báo Cáo Nhóm — Lab Day 08: Full RAG Pipeline

**Tên nhóm:** Nhóm Y6  
**Thành viên:**

| Tên | Vai trò | Email        |
|-----|---------|--------------|
| Võ Thanh Chung | Documentation Owner | vothanhchung95@gmail.com |
| Hoàng Thị Thanh Tuyền | Indexing Owner | hoangthanhtuyen1412@gmail.com             |
| Lê Minh Khang | Indexing Support | minhkhangle2k4@gmail.com             |
| Dương Khoa Điềm | Retrieval Owner | duongkhoadiemp@gmail.com             |
| Nguyễn Hồ Bảo Thiên | Eval Owner | thiennguyen3703@gmail.com             |
| Đỗ Thế Anh | Config Owner / Fine-tune | anh.dothe47@gmail.com |

**Ngày nộp:** 13/04/2026  
**Repo:** https://github.com/thiennguyen37-qn/Y6-401-Day08 

**Độ dài khuyến nghị:** 600–900 từ

---

> **Hướng dẫn nộp group report:**
>
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code, scorecard, hoặc tuning log** — không mô tả chung chung

---

## 1. Pipeline nhóm đã xây dựng (150–200 từ)

Nhóm xây dựng RAG pipeline cho internal knowledge base doanh nghiệp gồm 5 tài liệu nội bộ (policy hoàn tiền, SLA P1, access control SOP, IT helpdesk FAQ, HR leave policy). Pipeline nhận câu hỏi tiếng Việt, tìm đoạn văn bản liên quan từ ChromaDB, rồi dùng LLM sinh câu trả lời ngắn gọn có trích dẫn nguồn.

**Chunking decision:**
Nhóm dùng `chunk_size=400 tokens` (~1600 ký tự), `overlap=80 tokens` (~320 ký tự), chiến lược hybrid: tách theo section heading (`=== ... ===`) trước, sau đó paragraph-based với overlap trong mỗi section. Lý do: tài liệu có cấu trúc section rõ ràng (SLA P1, Access Control SOP), giữ nguyên header giúp retrieval tìm đúng phần; 400 tokens đủ chứa 1 điều khoản mà không quá dài gây noise; 80 tokens overlap tránh cắt giữa câu liên tiếp.

**Embedding model:**
`text-embedding-3-small` (OpenAI) khi có `OPENAI_API_KEY`; fallback: `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers, local). Vector store: ChromaDB PersistentClient, cosine similarity, collection `"rag_lab"`.

**Retrieval variant (Sprint 3):**
Hybrid dense + BM25 via Reciprocal Rank Fusion (RRF, k=60), `top_k_search=15`, `top_k_select=5`, **không dùng rerank** (xem lý do ở mục 2). Dense weight=0.5, Sparse weight=0.5. Lý do chọn hybrid: corpus trộn lẫn ngôn ngữ tự nhiên (policy clauses) và exact keyword (mã priority "P1", tên tài liệu cũ "Approval Matrix") — BM25 giải quyết alias queries mà dense bỏ lỡ.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Bỏ cross-encoder rerank khỏi variant cuối cùng

**Bối cảnh vấn đề:**
Variant 1 thêm cả hybrid retrieval lẫn cross-encoder rerank (`ms-marco-MiniLM-L-6-v2`). Kết quả: faithfulness giảm mạnh -0.60 (từ 4.80 xuống 4.20/5). Phân tích lỗi cho thấy cross-encoder English-only chấm điểm chunks tiếng Việt kém — nó loại bỏ nhầm các chunks đúng khi query bằng tiếng Việt, khiến LLM thiếu context và hallucinate hoặc trả lời tệ hơn.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Giữ rerank (Variant 1: hybrid + rerank) | Precision cao về lý thuyết, loại noise tốt | English-only cross-encoder hại tiếng Việt; faith -0.60; chậm hơn 2-3s/query |
| Hybrid không rerank (Variant 2) | Faithful hơn, không bị language bias; completeness tốt nhất | Một số câu (q06, q08) hơi nhiều noise hơn do BM25 kéo cross-domain chunks |
| Giữ baseline dense | Đơn giản, ổn định | Bỏ lỡ alias queries (q07 "Approval Matrix"), VIP queries (q10) |

**Phương án đã chọn và lý do:**
Variant 2: hybrid không rerank. Quyết định dựa trên nguyên tắc A/B — chỉ thay đổi một biến: bỏ rerank, giữ hybrid. Kết quả xác nhận rerank là nguyên nhân giảm điểm, không phải hybrid.

**Bằng chứng từ scorecard/tuning-log:**
`results/scorecard_variant.md` — Variant 2: Faithfulness 4.40/5 (phục hồi từ 4.20), Completeness 4.00/5 (cao nhất trong 3 runs). `docs/tuning-log.md` ghi rõ: q07 Completeness 2→5 (alias query), q10 Relevance 1→5 và Completeness 2→5 (VIP query) nhờ hybrid tìm được đúng chunk.

---

## 3. Kết quả grading questions (100–150 từ)

Pipeline chạy với `retrieval_mode="hybrid"` (Variant 2) và kết quả được log tại `logs/grading_run.json` (timestamp 17:44, trong khung 17:00–18:00).

**Ước tính điểm raw:** ~55–65 / 98

**Câu tốt nhất:** q01 (SLA P1), q02 (Refund 7 ngày), q03 (Level 3 approval), q05 (account lockout) — Lý do: câu hỏi đơn giản, một nguồn, hybrid dense tìm đúng ngay. Câu trả lời có citation `[1]`, đúng fact, ngắn gọn.

**Câu fail:** q09 (ERR-403-AUTH) — Root cause: (1) **Indexing**: không có chunk nào nêu rõ error code này; (2) **Retrieval**: hybrid lấy chunks về "authentication" nhưng không có "ERR-403-AUTH"; (3) **Generation**: MIN_CONFIDENCE guard chỉ hoạt động với dense mode, hybrid không có abstain guard → LLM nói "Tôi không biết" mà không cung cấp guidance về IT Helpdesk.

**Câu gq07 (abstain):** Pipeline trả lời "Tôi không biết." khi không tìm thấy thông tin. Đây là **vague abstain** — đúng về việc không bịa nhưng thiếu hướng dẫn cụ thể ("Không tìm thấy trong tài liệu hiện có, hãy liên hệ IT Helpdesk"). Theo rubric SCORING.md: ~5/10 (abstain nhưng mơ hồ, không nêu rõ lý do).

---

## 4. A/B Comparison — Baseline vs Variant (150–200 từ)

**Biến đã thay đổi (chỉ 1 biến):** Retrieval mode — `dense` (baseline) → `hybrid + no rerank` (Variant 2). Giữ nguyên: chunk_size=400, overlap=80, top_k từ 10→15 (tăng để đáp ứng hybrid), llm_model=gpt-4o-mini, temperature=0.

| Metric | Baseline | Variant 2 | Delta |
|--------|---------|---------|-------|
| Faithfulness | 4.80/5 | 4.40/5 | **-0.40** |
| Answer Relevance | 4.50/5 | 4.40/5 | -0.10 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.80/5 | **4.00/5** | **+0.20** |

**Kết luận:**
Variant 2 **tốt hơn baseline về Completeness** (+0.20) và giải quyết được alias queries và edge cases: q07 (Approval Matrix alias) Completeness 2→5 nhờ BM25 match exact term; q10 (VIP refund) Relevance 1→5 và Completeness 2→5 nhờ hybrid tìm được standard refund policy chunk. Baseline **tốt hơn về Faithfulness** (-0.40 trong variant) do hybrid đôi khi kéo cross-domain chunks: q06 (SLA escalation) bị lẫn access-control chunk, LLM bị confuse. Tradeoff rõ ràng: **hybrid tốt hơn cho recall và edge cases, baseline tốt hơn cho precision và focused queries**.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm                                                                                                                                                               | Sprint |
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| Võ Thanh Chung | Documentation Owner: tích hợp end-to-end, `call_llm()` (multi-provider), fix OpenAI API key (3 commits), chạy baseline scoring, viết `tuning-log.md` và `architecture.md` | 2, 3, 4 |
| Hoàng Thị Thanh Tuyền | Indexing Owner: `index.py` hoàn chỉnh — chunking, metadata extraction, ChromaDB setup                                                                                     | 1 |
| Lê Minh Khang | Indexing support: refactor `index.py` — clean code, cải thiện metadata extraction và chunking logic                                                                       | 1 |
| Dương Khoa Điềm | Retrieval Owner: `rag_answer.py` initial — skeleton retrieve và generate                                                                                                  | 2 |
| Nguyễn Hồ Bảo Thiên | Eval Owner: `eval.py` hoàn chỉnh (LLM-as-Judge), `grading.py`, chạy grading log                                                                                           | 2, 4 |
| Đỗ Thế Anh | Config Owner: `config.py` (tập trung siêu tham số), fine-tuning hybrid variant, mở rộng eval sang Groq                                                                    | 1, 3 |

**Điều nhóm làm tốt:**
Phân công theo component rõ ràng, mỗi người có ownership riêng. Tuning log chi tiết với A/B evidence cụ thể. Việc tạo `config.py` sớm giúp thay đổi tham số chỉ ở một chỗ.

**Điều nhóm làm chưa tốt:**
Integration xảy ra muộn — các branches merge gần deadline, khó test end-to-end sớm. OpenAI embedding quota bị hết sau vài lần chạy, gián đoạn validation. MIN_CONFIDENCE abstain logic không được điều chỉnh cho hybrid mode.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

**Cải tiến 1 — Fix MIN_CONFIDENCE cho hybrid mode:** Hiện tại `rag_answer.py` chỉ check `if retrieval_mode == "dense"` trước khi abstain. Thêm max-RRF-score threshold cho hybrid — nếu max score < 0.015 (tương đương confidence thấp) → trả về abstain với message cụ thể: "Không tìm thấy thông tin trong các tài liệu hiện có, hãy liên hệ IT Helpdesk." Bằng chứng: q09 variant Faithfulness=2, Relevance=1 do vague "Tôi không biết."

**Cải tiến 2 — Metadata filtering cho SLA queries:** Khi query chứa "SLA", "P1", hoặc "escalation", filter trước với `source in ["sla_p1_2026.txt"]` rồi mới retrieve. Bằng chứng: q06 Completeness 5→1 trong Variant 2 vì hybrid kéo access-control chunks vào SLA query.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
