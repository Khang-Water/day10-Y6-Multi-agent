# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Hồ Bảo Thiên 
**Vai trò trong nhóm:** Eval Owner
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Trong lab này, tôi đảm nhận phần **Sprint 4: Evaluation & Scorecard** thông qua việc xây dựng và hoàn thiện file `eval.py`. Cụ thể, tôi đã implement logic cho các hàm đánh giá gồm: score_faithfulness, score_answer_relevance, score_context_recall, score_completeness. Với `score_context_recall`, tôi đã tối ưu hóa việc so sánh chuỗi bằng thư viện `os.path` để đối chiếu linh hoạt các đường dẫn file (tránh lỗi khi format path khác nhau). Với `score_completeness`, tôi thiết lập prompt để sử dụng phương pháp **LLM-as-Judge**, gọi API để AI tự động đối chiếu câu trả lời với đáp án chuẩn. Công việc của tôi đóng vai trò là "bộ lọc" cuối cùng, kết nối với Sprint 2 và 3 của các thành viên khác, chạy qua bộ test, và kiểm tra các variant có thực sự mang lại hiệu quả hay không.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Sau khi làm lab này, tôi hiểu sâu sắc hơn về khái niệm **Evaluation Loop (Vòng lặp đánh giá)** và phương pháp **LLM-as-Judge**. Trước đây, tôi nghĩ việc đánh giá AI đơn giản là đọc thử vài câu trả lời xem có lọt tai không. Tuy nhiên, qua lab này, tôi hiểu rằng đánh giá RAG phải tách bạch rõ ràng giữa *Retrieval quality* và *Generation quality*. 

Bên cạnh đó, tôi thực sự hiểu rõ cách hoạt động của LLM-as-Judge. Thay vì phải chật vật viết code bằng Regex để chấm điểm text rất cứng nhắc, ta có thể viết một system prompt thật chặt chẽ, định nghĩa rõ thang điểm 1-5 và ép LLM trả về cấu trúc JSON (chứa điểm số và lý do trừ điểm). Cách này linh hoạt và giống với tư duy chấm bài của con người hơn rất nhiều.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?


_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** "q10 - Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?"

**Phân tích:**
Ở Baseline, điểm Context Recall đạt tối đa (5/5) cho thấy hệ thống có lấy được đúng tài liệu chuẩn. Tuy nhiên, Answer Relevance lại chạm đáy (1/5) và Completeness cực thấp (2/5). Lỗi ở đây nằm ở sự chênh lệch giữa khâu retrieval và generation. Do chỉ dùng dense search, hệ thống kéo về các chunk có ý nghĩa tương đồng nhưng lại thiếu đi từ khóa quyết định để trả lời đúng câu hỏi. Hậu quả là khi đưa 3 chunks này cho LLM, nó sinh ra một câu trả lời hoàn toàn lạc đề.

Ở phiên bản Variant, điểm số đạt mức tuyệt đối. Sự cải thiện vượt bậc này nhờ vào việc đổi sang Hybrid Search. Tính năng tìm kiếm từ khóa đã khắc phục nhược điểm "trôi dạt ngữ nghĩa" của dense search, giúp hệ thống gắp chính xác đoạn văn có chứa câu trả lời trực tiếp. Bên cạnh đó, việc nới rộng top_k_search lên 15 và đưa cho LLM nhiều ngữ cảnh hơn (top_k_select từ 3 lên 5) đã giúp cho mô hình sinh ra một câu trả lời vừa đi thẳng vào trọng tâm vừa đầy đủ trọn vẹn mọi khía cạnh.

_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thêm thời gian, tôi sẽ thử nghiệm chiến lược Semantic Chunking thay vì chia nhỏ văn bản theo độ dài cố định. Kết quả eval cho thấy điểm Completeness đôi khi bị thấp do thông tin quan trọng bị cắt đôi giữa hai chunk, khiến LLM thiếu ngữ cảnh để trả lời trọn vẹn.
_________________

---


