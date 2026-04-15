# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Hoàng Thị Thanh Tuyền
**Vai trò trong nhóm:** Thành viên - Indexing Owner
**Ngày nộp:** 13/04/2026

---

## 1. Tôi đã làm gì trong lab này?

Trong Lab Day 08, em chủ yếu phụ trách Sprint 1 và hỗ trợ phần A/B testing ở Sprint 3–4. Phần việc chính của em là triển khai và tinh chỉnh file index.py, bao gồm đọc tài liệu, tiền xử lý, chia chunk và đưa dữ liệu vào hệ thống indexing để phục vụ retrieval. Em đã tập trung điều chỉnh cách chunking để nội dung được cắt hợp lý hơn, hạn chế việc mất ngữ nghĩa khi chia tài liệu, đồng thời kiểm tra và sửa các lỗi phát sinh trong quá trình build index như lỗi không khớp kích thước embedding giữa collection cũ và model mới.

Sau khi phần index ổn định, em dùng chính kết quả này để hỗ trợ chạy A/B testing giữa baseline và các variant retrieval. Công việc của em kết nối trực tiếp với phần retrieval và evaluation của các thành viên khác, vì chất lượng index là đầu vào quyết định việc truy xuất đúng context và chấm điểm scorecard sau đó.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Hai core concept em am hiểu ra rất nhiều là: **Evaluation Loop (Vòng lặp đánh giá tự động)** và **Hybrid Retrieval vs Dense**.

Trước đây em thường code prompt gửi vào OpenAI và đọc bằng mắt xem có hay hay không. Sau khi làm Lab, em nhận ra việc đánh giá bằng mắt quá cảm tính và chậm. Thông qua cơ chế Evaluation Loop (chạy tập 10-20 câu hỏi mốc và chia ra 4 hệ số đo đạc qua LLM-as-judge), em hiểu được làm thế nào tối ưu hóa RAG theo hướng Engineering — có tham chiếu số hóa và lặp lại logic. Hệ số Context Recall (Retrieval làm tốt hay chưa) & Faithfulness (Generator có dựa đúng vào bối cảnh mang lên hay không) là xương sống. Ngoài ra, RRF (Reciprocal Rank Fusion) ở Hybrid Retrieval khá thú vị vì dense vector dở ở khoản bắt từ khóa viết tắt nhưng khoẻ ở đồng nghĩa, Sparse / BM25 thì ngược lại.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều em thấy đáng ngạc nhiên nhất nằm ở mức độ dễ bị **ảo giác thông tin (Hallucination)** của các model thế hệ mới, thậm chí là mô hình mạnh như ChatGPT-4o nếu đưa vào Retrieval dữ liệu dư thừa hoặc nhiễu rác.

Khó khăn lớn nhất em gặp là phần debug pipeline indexing và retrieval, vì lỗi thường không nằm ở một chỗ duy nhất như em nghĩ ban đầu. Trường hợp mất nhiều thời gian nhất là khi chương trình build index bị dừng do collection cũ của ChromaDB đang lưu vector 384 chiều, trong khi embedding mới sinh ra 1536 chiều. Ban đầu em tưởng lỗi nằm ở dữ liệu đầu vào hoặc bước chunking trong index.py, nhưng sau khi kiểm tra kỹ mới thấy nguyên nhân thật là collection cũ bị tái sử dụng sau khi đổi model embedding.

Một điều khác cũng không đúng kỳ vọng là có những câu trong A/B testing có context recall rất cao nhưng completeness vẫn thấp. Lúc đầu em nghĩ retrieval đã đúng thì answer sẽ tốt, nhưng thực tế cho thấy generator vẫn có thể trả lời thiếu ý hoặc xử lý chưa tốt khi ngữ cảnh không đủ rõ.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** q09 - "ERR-403-AUTH là lỗi gì và cách xử lý?" (Trường hợp Insufficient Context - Lệnh lạc hướng)

**Phân tích:**

- **Baseline trả lời sai và thiên vị nặng**: Ở Baseline, Context Recall được chấm là N/A (Vì cơ sở dữ liệu docs vốn dĩ không có thông tin này để retrieve), điểm Completeness rớt còn 2/5 và Answer Relevance cũng chỉ loanh quanh 2/5.
- **Lỗi nằm ở phía Generation (Prompt Grounding)**: Retrieval không kéo được gì có giá trị lên, lúc thế này đáng lẽ LLM Generator phải đọc Context và nhận thức "Tôi không đủ thông tin từ ngữ cảnh để đưa ra câu trả lời". Tuy nhiên, model vẫn phớt lờ và múa đại một lỗi 403 HTTP thông thường, tự nghĩ ra giải pháp cấp quyền qua Jira.
- **Variant có cải thiện**: Để chữa lỗi ảo giác này, nhóm đã thêm ngưỡng `MIN_CONFIDENCE` đối với dense core: Chặn không đưa ngữ cảnh kém vào prompt lúc query (Abstain early). Hơn nữa, prompt template siết grounding lại bắt buộc mô hình kết xuất chuỗi thông báo nếu evidence vượt tầm xử lý. Nhờ vậy mô hình báo "Không đủ thông tin" an toàn và Faithfulness tiếp tục vững ở mức 5.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm thời gian, em sẽ thực hiện **Chunking có ý nghĩa ngữ nghĩa (Semantic Chunking)** thay vì chunk thô bằng rule khoảng cách \n\n. Bởi lẽ, việc cắt bằng dấu hiệu ngắt dòng hay điểm '.' vẫn tồn tại giới hạn đối với các điều luật bị kéo dài miên man.
Hơn nữa, em sẽ thử tích hợp thêm phương pháp làm mịn Query (Query Rewriting / Expansion) trước khi đem tra cờ Sparse+Dense nhằm bắt dính chặt hơn ý định của user. Kết quả báo cáo variant ở các câu liên quan đến Từ Alias/Viết tắt sẽ tăng.

---
