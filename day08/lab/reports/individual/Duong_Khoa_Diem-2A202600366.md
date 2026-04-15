# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Dương Khoa Điềm (2A202600366)  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ  

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong Lab 08, tôi đảm nhận vai trò Retrieval Owner, chủ yếu phụ trách Sprint 2 liên quan đến truy xuất dữ liệu từ Vector Database. Chi tiết bao gồm: 
- Thiết lập và thử nghiệm phương pháp Dense Retrieval bằng ChromaDB sử dụng vector similarity. 
- Mở rộng kiến trúc thành Hybrid Retrieval: Triển khai thuật toán tìm kiếm Sparse bằng thư viện `rank_bm25` (phân tích keyword) và kết hợp với Dense qua cơ chế chấm điểm chéo Reciprocal Rank Fusion (RRF). 
- Triển khai cross-encoder Re-ranking để nâng cao độ chính xác (Precision) cho Top K chunks thu được. 

Tôi cộng tác chặt chẽ cùng một AI assistant để hoàn thiện các module tìm kiếm này (từ dòng 1 đến 231 trong `rag_answer.py`). Tuy nhiên, phần khởi tạo mô hình ngôn ngữ và sinh câu trả lời trong hàm `call_llm` là do thành viên Võ Thanh Chung trong nhóm phụ trách. Tôi đảm bảo kết quả Retrieved Chunks được truyền chuẩn xác qua format prompt để thành viên Chung có dữ liệu đúng.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi thực sự hiểu rõ hơn về concept **Hybrid Retrieval** và sự thiết yếu của nó khi bù đắp giới hạn của Dense Retrieval. 

Trước đây tôi cho rằng chỉ cần Vector Embedding là đủ mạnh để RAG hiệu quả. Tuy nhiên, qua quá trình làm Lab tôi nhận ra Vector Embedding rất dễ bỏ lỡ những dữ kiện đòi hỏi sự chính xác tuyệt đối như tên riêng, mã số tài liệu, hay mã lỗi báo hệ thống (ví dụ: `ERR-403`). Hybrid Retrieval tỏa sáng nhờ sự đóng góp của Sparse Retrieval (điển hình như hệ quy chiếu BM25) trong việc tìm ra các đoạn text trùng lặp từ khóa tuyệt đối, trong khi Vector DB lo giải quyết đồng thời bài toán tìm từ đồng nghĩa. Công thức tích hợp RRF giúp hài hòa điểm số trả về, cho kết quả tìm kiếm rất vững vàng.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Việc khó khăn lớn nhất nằm ở khả năng kiểm soát độ nhiễu. Khi tôi nâng số lượng chunk (`top_k_search`) lên để đảm bảo đoạt lại Context Recall cao, mô hình lại thu thập lượng lớn các "rác" context, làm giảm đi Answer Relevance vì hệ thống LLM bị phân tâm (hiện tượng Lost in the middle).

Điều khiến tôi bất ngờ nhất là **Cross-Encoder Re-ranker** tuy hiệu quả nhưng tốn tài nguyên khá nhiều. Việc tính toán so khớp mô hình trực tiếp qua cặp text queries và từng candidate mất một lượng mili-giây đáng kể, làm độ trễ phản hồi đôi khi lên đến hơn vài giây so với tìm kiếm vector thông thường. Từ đó, tôi hình dung rõ được logic thiết kế phễu: "Search rộng (BM25 + Dense) -> Re-rank thu hẹp -> Generation".

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** (gq10 - Tính năng Temporal scoping) Chính sách v4 áp dụng đơn trước 01/02 không?

**Phân tích:**
Với hệ thống RAG cài đặt Baseline Dense ban đầu (Sprint 2), hệ thống trả về điểm Context Recall rất thấp (mức 2/5) và điểm Faithfulness thỉnh thoảng chỉ ở mức 2-3 (mô hình LLM có xu hướng tự đoán hoặc dựa vào kiến thức nền ngoài tài liệu). Lỗi hệ thống nằm chủ yếu ở bước Retrieval: Khi nhắc đến định danh tài liệu "v4" hay một mốc thời gian cực kỳ cụ thể về ngày áp dụng chính sách, chức năng Vector Similarity không match và bắt dính được ý đồ truy vấn, hệ thống trả về rất nhiều chunk quy định hoàn tiền chung chung của các ver cũ.

Khi tôi kích hoạt chuỗi công cụ Hybrid Retrieval + Query Expansion (ở Sprint 3), kết quả đã cải thiện tuyệt đối về 5/5 Recall. Variant tốt hơn Baseline vì tính năng Query Expansion đã mở rộng hoàn cảnh để hệ thống tìm song song Sparse (BM25 bắt chặt "v4" và "01/02"). Cải tiến Retrieval này cung cấp cho luồng Generation các chunk chứa chính xác ngày hiệu lực của chính sách V4, nhờ đó LLM không bịa thông tin lệch ngày.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi muốn cài đặt thêm các phương pháp **Semantic Chunking** thay vì chỉ chia đoạn bằng Heading và số lượng tokens tĩnh. Ngoài ra, tôi muốn thử áp dụng pipeline Self-Reflective RAG (Self-RAG), ở đó mô hình LLM có thể tự review lại các chunks tôi lấy từ bước Hybrid Filtering để nhận diện và loại bỏ các thông tin sai lệch trước cả khi gửi vào prompt sinh answer cuối cùng.
