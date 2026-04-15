# Báo cáo cá nhân — Lab Day 10

**Họ và tên:** Dương Khoa Điềm  
**Vai trò:** Embed & Idempotency Owner  
**Độ dài:** ~400 từ

---

## 1. Phụ trách

Tôi triển khai logic chống trùng lặp và dọn dẹp vector dư thừa tại hàm `cmd_embed_internal` trong `etl_pipeline.py`. Kết nối với Ingestion Owner (Võ Thanh Chung) qua list `chunk_id` truyền vào để đảm bảo tính duy nhất làm primary key khi embed.

**Bằng chứng:** Sửa log file tracking thành `embed_upserted` theo yêu cầu tại dòng 176 `etl_pipeline.py` và xuất thành công tại `artifacts/logs/run_test-embed-1.log` (và run_test-embed-2).

---

## 2. Quyết định kỹ thuật

**Idempotency (Upsert):** Để tránh việc nạp đi nạp lại dữ liệu làm Vector DB bị phình to (duplicate), tôi quyết định dùng phương thức `col.upsert(ids=ids, ...)` thay cho `client.add()`. Như vậy khi luồng `chunk_id` cũ được feed lại, ChromaDB chỉ ghi đè/update nội dung mới thay vì nạp trùng tạo sinh rác.

**Pruning (Dọn dẹp):** Để tiêu diệt triệt để các "Stale IDs" (tức là file raw từ lượt ingestion trước đã dính luật Clean và bị cách ly, nhưng vector lại vẫn "sống" trong DB). Tôi sử dụng cơ chế kéo tập Set cũ bằng lệnh `col.get()` trừ cho tập bản ghi mới `set(ids)` để lọc ra dư thừa, tạo danh sách `drop` và gọi trực tiếp `col.delete` để dọn tận gốc rễ.

---

## 3. Sự cố / anomaly

Lúc bỏ quy trình Prune để chạy thử, tôi liên tục phát hiện `similarity_search` thỉnh thoảng trỏ sai vào những file đáng ra đã bị vứt bỏ ở phần Data Cleaning, khiến retrieval/RAG gặp hiện tượng nhiễu "mồi nhử". Nguyên nhân xuất phát từ việc vector id lưu trữ trong disk chưa từng bị clear. Fix: Thêm lệnh xoá theo mảng `prev_ids - set(ids)` vào sát khâu trước Upsert.

---

## 4. Before/after

**Log (Test Idempotency):** Ở lần nạp lưu 1 (`run_test-embed-1.log`), pipeline xác nhận qua câu log `embed_upserted=6 collection=day10_kb`. Ngay lập tức Test kích hoạt pipeline phát thứ 2 bằng (`run_id=test-embed-2`), hệ thống ghi đè trơn tru, lượng record vẫn in y nguyên `embed_upserted=6 collection=day10_kb`, Database size tại thư mục `chroma_db/` không bị tăng cấp số nhân.

**File CSV/Log prune:** Vector DB lúc này duy trì sạch sẽ song song với size của file `artifacts/cleaned/cleaned_test-embed-2.csv`.

---

## 5. Cải tiến thêm 2 giờ

Tối ưu hàm lấy danh sách ID cũ từ ChromaDB trong logic Pruning (`col.get()`) bằng cách đọc từng đợt (pagination batch khoảng 100 row một lần) và thay phần tải `col.upsert()` bằng luồng "Batch Upsert" kèm queue. Vì list data ở phòng thí nghiệm chỉ có 10 dòng thì ổn định nhưng nếu dùng scale sản xuất với RAW file cỡ chục vạn dòng dễ văng `Memory OOM` cho môi trường deploy của Ingestion Server.
