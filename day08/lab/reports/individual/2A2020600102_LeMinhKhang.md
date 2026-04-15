# Báo Cáo Cá Nhân - Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Minh Khang  
**Vai trò trong nhóm:** Indexing Support  
**Ngày nộp:** 13/04/2026  

---

## 1. Tôi đã làm gì trong lab này?

Trong bài lab này, tôi phụ trách chính phần indexing. Tôi tập trung xây dựng luồng lập chỉ mục trong file `index.py`, từ bước tiền xử lý dữ liệu cho đến tạo chỉ mục phục vụ truy xuất. Công việc cụ thể gồm: chuẩn hóa dữ liệu đầu vào, chia tài liệu thành các đoạn (chunking), tạo embedding cho từng chunk và lưu vào index để module retrieval có thể tìm kiếm nhanh và chính xác hơn. Ngoài phần cài đặt, tôi cũng kiểm tra tính ổn định của pipeline khi chạy với nhiều bộ dữ liệu khác nhau, bảo đảm quá trình indexing chạy nhất quán và không làm mất thông tin quan trọng của tài liệu gốc.

---

## 2. Điều tôi hiểu rõ hơn sau lab này

Sau lab, tôi hiểu rõ rằng chất lượng của toàn bộ hệ RAG phụ thuộc rất lớn vào tầng indexing và retrieval, không chỉ riêng prompt ở tầng generation. Nếu chunking chưa hợp lý hoặc dữ liệu đưa vào index chưa sạch, mô hình có thể vẫn trả lời sai dù prompt được viết tốt. Tôi cũng hiểu rõ hơn về đánh đổi giữa độ chi tiết và hiệu năng: chunk quá lớn làm giảm độ chính xác truy xuất, nhưng chunk quá nhỏ lại dễ mất ngữ cảnh. Từ trải nghiệm này, tôi rút ra rằng cần thiết kế pipeline indexing có cấu hình rõ ràng để dễ thử nghiệm, dễ điều chỉnh tham số và dễ đánh giá tác động của từng thay đổi.

---

## 3. Điều tôi gặp khó khăn

Khó khăn lớn nhất của tôi là xử lý dữ liệu đầu vào không đồng nhất. Một số tài liệu có cấu trúc rõ ràng, nhưng một số khác bị nhiễu định dạng, khiến bước chunking ban đầu cho kết quả chưa ổn định. Khi đó, tôi phải thử nhiều cách tách đoạn để cân bằng giữa khả năng giữ ngữ cảnh và khả năng truy xuất đúng phần thông tin cần thiết. Ngoài ra, việc tối ưu tham số indexing cần thời gian vì không thể điều chỉnh tất cả cùng lúc; nếu đổi nhiều biến trong một lần chạy thì rất khó xác định nguyên nhân cải thiện hay suy giảm chất lượng.

---

## 4. Kết quả và đóng góp chính

Kết quả chính của tôi là hoàn thiện module indexing trong `index.py` để pipeline có thể tạo chỉ mục ổn định cho các bước truy xuất phía sau. Phần việc này giúp nhóm có nền tảng dữ liệu tốt hơn để thực hiện retrieval và đánh giá chất lượng câu trả lời. Tôi cũng đóng góp ở khâu kiểm tra dữ liệu đầu vào và theo dõi chất lượng chỉ mục sau mỗi lần thay đổi tham số, từ đó giúp giảm lỗi khi chạy pipeline end-to-end. Nhìn chung, vai trò Indexing Support của tôi tập trung vào việc bảo đảm hệ thống có nguồn context đáng tin cậy trước khi đưa sang LLM.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

Nếu có thêm thời gian, tôi sẽ tiếp tục tối ưu chiến lược chunking theo từng loại tài liệu thay vì dùng một cấu hình chung cho tất cả. Tôi cũng muốn bổ sung thêm bước kiểm tra chất lượng chỉ mục tự động để phát hiện sớm các trường hợp dữ liệu lỗi hoặc thiếu ngữ cảnh. Mục tiêu là làm cho pipeline indexing vừa ổn định, vừa dễ mở rộng khi khối lượng tài liệu tăng.

---
