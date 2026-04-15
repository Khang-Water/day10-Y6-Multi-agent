# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Võ Thanh Chung  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 13/04/2026  
**Mã học viên:** 2A202600335  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi đảm nhận vai trò người tích hợp end-to-end và đảm bảo pipeline chạy được từ đầu đến cuối.

- **Sprint 2**: Implement `call_llm()` trong `rag_answer.py` để hỗ trợ 3 providers: OpenAI (qua Azure endpoint), Gemini, và Groq. Fix lỗi OpenAI API key trong 3 files (`eval.py`, `rag_answer.py`, `index.py`) — phải commit 3 lần riêng biệt vì mỗi file dùng API key theo cách khác nhau. Sau khi fix, chạy pipeline end-to-end và tạo `results/scorecard_baseline.md`.

- **Sprint 3**: Phối hợp với nhóm chọn variant. Verify `scorecard_variant.md` sau khi Đỗ Thế Anh implement hybrid config trong `config.py`.

- **Sprint 4**: Viết `docs/tuning-log.md` (ghi đầy đủ kết quả baseline, Variant 1, Variant 2 với bảng so sánh và kết luận) và `docs/architecture.md` (full pipeline diagram, chunking decision, failure mode checklist).

Công việc của tôi kết nối với nhóm như sau: Tuyền implement `index.py`, Điềm implement skeleton `rag_answer.py`, Thiên implement `eval.py` — tôi là điểm tích hợp, đảm bảo các module import đúng nhau và API key hoạt động.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Tích hợp pipeline quan trọng không kém implement từng component.** Trong RAG, các phần indexing → retrieval → generation → evaluation được viết bởi người khác, nhưng nếu không có ai test end-to-end và fix integration bugs, pipeline vẫn không chạy được dù từng phần đúng.

Tôi thấy rõ điều này qua lỗi API key: `index.py` và `rag_answer.py` dùng trực tiếp `os.getenv("OPENAI_API_KEY")` nhưng `eval.py` cần Azure endpoint `base_url`. Fix một chỗ không đủ — phải fix tất cả. Sau khi Đỗ Thế Anh tạo `config.py` tập trung tất cả tham số, vấn đề này được giải quyết dứt điểm.

Bài học thứ hai từ q10 (VIP refund): **"abstain" không phải lúc nào cũng là câu trả lời đúng khi có context liên quan.** Baseline abstain vì không tìm thấy "VIP policy" riêng — nhưng context có quy trình tiêu chuẩn 3-5 ngày. Câu trả lời đúng là dùng context chung khi không có context đặc thù. Hybrid retrieval giải quyết bằng cách tìm thêm được refund chunk qua BM25.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

**Ngạc nhiên nhất:** Fix API key mất nhiều thời gian hơn dự kiến rất nhiều. Tôi tưởng là sửa một biến là xong. Nhưng thực tế: `rag_answer.py` dùng Azure `base_url` không cần, `eval.py` hardcode endpoint cũ, `index.py` thiếu fallback khi key không hợp lệ. Ba commits riêng biệt (commit `604c2ab`, `b74a27e`, `56e3c96`) cho cùng một vấn đề là bằng chứng rõ nhất. Sau này nhìn lại, lý do là thiếu standardization từ đầu — mỗi người xử lý API key theo cách của mình.

**Khó khăn nhất:** Debug integration khi các branches chưa merge. Khi tôi cần test `eval.py` gọi `rag_answer.py`, code của Thiên đang ở branch `thien` và code của Điềm ở branch `diem`. Phải merge PR #1 và PR #2 trước khi có thể test end-to-end. Trong thực tế, nên integrate liên tục thay vì cuối cùng merge tất cả một lúc.

**Giả thuyết ban đầu:** "Pipeline sẽ chạy được ngay sau khi merge các PRs." Thực tế: còn cần fix thêm 4 commits nữa (`4a018a3`, `604c2ab`, `b74a27e`, `56e3c96`) sau khi merge.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi (q10):** "Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?"

**Baseline (dense):** Trả lời "Không có thông tin nào trong bối cảnh đề cập đến quy trình hoàn tiền khẩn cấp cho khách hàng VIP."
- Faithfulness: 4/5 | Relevance: 1/5 | Completeness: 2/5

**Variant 2 (hybrid):** Trả lời đúng "Không có quy trình đặc biệt cho VIP, áp dụng quy trình tiêu chuẩn 3-5 ngày làm việc."
- Faithfulness: 5/5 | Relevance: 5/5 | Completeness: 5/5

**Phân tích failure ở baseline:**

1. **Retrieval**: Dense search với query "hoàn tiền khẩn cấp khách hàng VIP" không match semantic với chunk về "quy trình tiêu chuẩn hoàn tiền 3-5 ngày" — quá khác nhau về từ ngữ.

2. **Generation**: Prompt có rule "Nếu context không đủ, nói không biết" → model thấy không có chunk về "VIP" → abstain. Nhưng đây là **abstain sai**: context *có* câu trả lời (quy trình tiêu chuẩn áp dụng cho mọi người), chỉ là không có quy trình riêng cho VIP.

**Tại sao Variant 2 sửa được:** BM25 trong hybrid match keyword "refund" / "hoàn tiền" và tìm được chunk về quy trình tiêu chuẩn. Với context đó, LLM hiểu rằng không có quy trình VIP riêng → trả lời đúng bằng cách nêu quy trình chung.

**Bài học:** Dense-only retrieval dễ fail với "negative evidence queries" — câu hỏi mà câu trả lời đúng là "không có ngoại lệ, dùng rule chung." Hybrid + đủ context giải quyết được class lỗi này.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

**Cải tiến 1 — Fix MIN_CONFIDENCE guard cho hybrid mode:** Trong `rag_answer.py:500`, logic `if retrieval_mode == "dense" and candidates[0]["score"] < MIN_CONFIDENCE` chỉ áp dụng cho dense. Cần thêm RRF score threshold cho hybrid — nếu max RRF score < 0.015, trả về abstain cụ thể: "Không tìm thấy thông tin trong tài liệu nội bộ, hãy liên hệ IT Helpdesk." Bằng chứng: q09 variant Faithfulness=2 vì "Tôi không biết" không có guidance.

**Cải tiến 2 — Refactor `call_llm()` thành factory trong `config.py`:** Hiện tại providers được hardcode trong `rag_answer.py`. Nếu có thêm thời gian, tạo `get_llm_client()` trong `config.py` để tất cả files import từ một chỗ — tránh lặp lại bug API key tôi đã gặp phải khi integration.

---

*File: `reports/individual/Vo_Thanh_Chung-2A202600335.md`*
