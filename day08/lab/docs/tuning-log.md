# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.80 /5 |
| Answer Relevance | 4.60 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.80 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> - q10 (Refund VIP): Relevance = 1/5, Completeness = 2/5 - Model không tìm được thông tin về quy trình VIP
> - q07 (Approval Matrix): Completeness = 2/5 - Dense retrieval tìm được tài liệu nhưng không giải thích được tên cũ/tên mới  
> - q09 (Insufficient Context): Completeness = 2/5 - ERR-403-AUTH là lỗi gì và cách xử lý?

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias (q07 "Approval Matrix" vs "Access Control SOP")
- [x] Retrieval: Top-k quá ít → thiếu evidence (q10 cần context về quy trình đặc biệt)
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** Hybrid retrieval + Rerank + Increased top_k  
**Lý do chọn biến này:**
> Baseline cho thấy q07 (Approval Matrix) và q09 (ERR-403-AUTH) là alias queries mà dense retrieval bỏ lỡ. Corpus có cả ngôn ngữ tự nhiên (policy) lẫn tên riêng/mã lỗi (ticket code, SLA label). Hybrid kết hợp semantic + keyword search sẽ giải quyết vấn đề alias. Thêm rerank để cải thiện precision khi tăng top_k.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # dense + sparse (BM25)
top_k_search = 15          # tăng từ 10 để lấy nhiều candidate
top_k_select = 5           # tăng từ 3 để đưa nhiều context
use_rerank = True          # thêm cross-encoder rerank
# chunk_size, overlap, llm_model giữ nguyên
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.80/5 | 4.20/5 | -0.60 |
| Answer Relevance | 4.60/5 | 4.20/5 | -0.40 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.80/5 | 3.90/5 | +0.10 |

**Nhận xét:**
> **Cải thiện:** q08 (Remote policy) completeness từ 4→5 do hybrid tìm được thêm context về probation period.
> **Kém hơn:** q09 (ERR-403) faithfulness từ 5→1, relevance từ 5→1 - hybrid+rerank quá conservative, baseline đã abstain đúng ("Không tìm thấy thông tin") nhưng variant chỉ trả lời "Tôi không biết". q10 (Refund VIP) faithfulness từ 4→2, relevance từ 1→2 - vẫn không tìm được thông tin VIP nhưng trả lời tệ hơn. q07 (Approval Matrix) relevance từ 5→4 - hybrid không cải thiện được alias query như mong đợi.

**Kết luận:**
> Variant 1 **không tốt hơn baseline** overall. Mặc dù hybrid giúp q08, nhưng rerank quá strict làm giảm faithfulness và relevance. Hybrid + rerank chậm hơn đáng kể (2-3s/query) mà không cải thiện overall scores. Baseline đơn giản và hiệu quả hơn cho use case này.

---

## Variant 2

**Ngày:** 2026-04-13  
**Biến thay đổi:** Hybrid retrieval KHÔNG có rerank — kiểm tra xem rerank hay hybrid mới là nguyên nhân giảm điểm Variant 1  
**Lý do chọn biến này:**
> Variant 1 cho thấy rerank là thủ phạm chính: cross-encoder quá conservative, hạ faithfulness -0.60. Giả thuyết: hybrid retrieval (dense + BM25 RRF) vẫn có ích cho corpus trộn lẫn ngôn ngữ tự nhiên và keyword kỹ thuật — nhưng cần bỏ rerank. Thay đổi duy nhất: `USE_RERANK_VARI = False`, giữ nguyên hybrid mode và top_k.

**Config thay đổi:**
```
retrieval_mode = "hybrid"    # giữ nguyên từ Variant 1
top_k_search  = 15           # giữ nguyên từ Variant 1
top_k_select  = 5            # giữ nguyên từ Variant 1
use_rerank    = False        # ← THAY ĐỔI DUY NHẤT: bỏ cross-encoder
dense_weight  = 0.5
sparse_weight = 0.5
# chunk_size, overlap, min_confidence, llm_model giữ nguyên
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.80/5 | 4.20/5 | 4.40/5 | Baseline |
| Answer Relevance | 4.60/5 | 4.20/5 | 4.40/5 | Baseline |
| Context Recall | 5.00/5 | 5.00/5 | 5.00/5 | Tie |
| Completeness | 3.80/5 | 3.90/5 | **4.00/5** | **Variant 2** |

**Câu hỏi cải thiện (Variant 2 vs Baseline):**
> - q04 (Refund digital): Completeness 3→5, Faithfulness 4→5 — hybrid lấy được thêm chunk nêu rõ "license key, subscription"
> - q07 (Approval Matrix alias): Completeness 2→5 — BM25 match được exact term "Approval Matrix"
> - q10 (VIP refund): Faithfulness 4→5, Relevance 1→5, Completeness 2→5 — **win lớn nhất**: hybrid tìm được đúng refund policy chunk và LLM trả lời chuẩn "quy trình tiêu chuẩn 3-5 ngày"

**Câu hỏi giảm (Variant 2 vs Baseline):**
> - q06 (P1 escalation): Relevance 5→3, Completeness 5→1 — hybrid kéo vào chunk access-control khi retrieve SLA query; LLM bị lẫn context và trả lời thiếu trọng tâm
> - q07 (Approval Matrix): Faithfulness 5→2 — answer nói "tên cũ" nhưng bỏ sót tên hiện tại "Access Control SOP"; alias retrieval đúng nhưng generation bị cut
> - q08 (Remote policy): Completeness 4→3 — chi tiết "Team Lead phê duyệt" bị miss khi select 5 chunks thay vì 3 (context noise tăng)
> - q09 (ERR-403-AUTH): Vẫn Faithfulness=2, Relevance=1 — lưu ý: MIN_CONFIDENCE chỉ áp dụng cho dense mode, hybrid không có guard → LLM tự quyết abstain bằng "Tôi không biết"

**Kết luận:**
> Bỏ rerank đã phục hồi faithfulness từ 4.20→4.40 và completeness lên 4.00 (cao nhất trong 3 runs). Hybrid không rerank là **config tốt nhất cho Completeness** nhưng vẫn thua baseline về Faithfulness/Relevance do context noise từ BM25. Tradeoff rõ: baseline tốt hơn cho precision (q06, q08), Variant 2 tốt hơn cho recall và edge cases (q04, q07, q10).

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > **Generation hallucination khi context bị nhiễu.** Hybrid retrieval tăng recall nhưng đưa vào prompt các chunk từ domain khác (ví dụ: access-control chunk lọt vào query về SLA). LLM không phân biệt được context liên quan — kết quả là câu trả lời lạc đề hoặc mất completeness. Lỗi thứ hai là abstain quá sớm (q09): MIN_CONFIDENCE không hoạt động với hybrid, LLM tự abstain bằng "Tôi không biết" thay vì đưa hướng dẫn.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > **Rerank (cross-encoder)** có tác động tiêu cực mạnh nhất: -0.60 faithfulness (Variant 1). Lý do: model English cross-encoder chấm điểm tiếng Việt kém, loại bỏ nhầm các chunk đúng. **Hybrid retrieval không rerank** có tác động tích cực nhất cho completeness (+0.20 vs baseline) nhưng giảm precision cho focused queries. **Min_confidence** không ảnh hưởng với hybrid vì logic abstain chỉ check mode == "dense".

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > (a) **Metadata filtering**: Khi query về SLA thì filter source chứa "sla" — giảm cross-domain noise cho q06. (b) **Query expansion** cho q09: thêm "authentication error" vào query "ERR-403-AUTH" để tìm được helpdesk chunk. (c) **Giảm MIN_CONFIDENCE xuống 0.10 và bật lại cho hybrid** bằng cách kiểm tra max RRF score thay vì cosine distance. (d) Thử **multilingual rerank** (mmarco-mMiniLMv2) thay vì English-only ms-marco.
