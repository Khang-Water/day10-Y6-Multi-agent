# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Hồ Bảo Thiên
**Vai trò:** Cleaning Owner 
**Ngày nộp:** 2026-04-15 

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

Tôi chịu trách nhiệm chính cho transform/cleaning_rules.py. Nhiệm vụ của tôi là phát triển ≥ 3 rule làm sạch (lọc rác OCR, lột thẻ HTML, chặn rò rỉ PII) để tạo ra bản sạch tại artifacts/cleaned/cleaned_rows.csv. Các dữ liệu vi phạm được tôi cách ly triệt để vào artifacts/quarantine/quarantine_log.csv. 

**File / module:**

- transform/cleaning_rules.py
- data/raw/policy_export_dirty_1.csv
- artifacts/cleaned/cleaned_rows.csv
- artifacts/quarantine/quarantine_log.csv

**Kết nối với thành viên khác:**

Tôi tiếp nhận dữ liệu thô từ thành viên làm Ingest (Sprint 1). Sau quá trình làm sạch và kiểm định (Validate), tôi bàn giao dữ liệu chuẩn cho người phụ trách Embed Chroma (Sprint 2). Cuối cùng, tôi cung cấp log lỗi cho team để phục vụ việc đối chiếu Eval và viết Quality Report ở Sprint 3

**Bằng chứng (commit / comment trong code):**
- Add cleaning_rules.py (8f54de8)
- Add synthetic policy_export_dirty_1 and test (20727ac)
- Merge branch 'main' of https://github.com/Khang-Water/day10-Y6-Data-pipeline (a725288)

_________________

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Trong quá trình kiểm định dữ liệu tại Sprint 2, tôi quyết định thiết lập mức độ đình chỉ (halt) thay vì chỉ cảnh báo (warn) đối với các vi phạm rò rỉ dữ liệu cá nhân (PII) và lỗi trích xuất tài liệu (OCR/Word artifacts).

Lý do là rò rỉ PII vi phạm nghiêm trọng chuẩn mực bảo mật doanh nghiệp, trong khi rác định dạng (như "Error! Reference source not found") sẽ làm RAG mất ngữ cảnh và khiến LLM sinh ảo giác (hallucination). Nếu file Expectation phát hiện các lỗi này lọt qua bước Clean, luồng ETL sẽ lập tức dừng lại (should_halt = True), ngăn chặn tuyệt đối việc nhúng vector bẩn vào database. Ngược lại, lỗi nhẹ như đoạn văn ngắn (chunk_min_length) chỉ được gán mức warn.
_________________

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Trong quá trình phân tích dữ liệu thô, tôi phát hiện triệu chứng một số chunk chỉ chứa toàn thẻ dàn trang và ký tự tàng hình. Nếu nhúng thẳng, chúng sẽ tạo ra các vector "rỗng" vô nghĩa, gây tốn dung lượng Vector DB và làm giảm độ chính xác khi RAG truy xuất.

Để khắc phục, tôi đã áp dụng Rule 2 (Format Stripping) dùng Regex lột sạch HTML. Điểm then chốt là đoạn logic hậu kiểm: nếu văn bản sau khi lột thẻ bị biến thành chuỗi rỗng (if not text:), hệ thống sẽ lập tức gán lý do empty_after_html_strip và cách ly dòng đó vào quarantine.log. Nhờ cách xử lý này, hệ thống đã chặn thành công các vector nhiễu trước khi bước vào giai đoạn Embed.
_________________

---

## 4. Bằng chứng trước / sau (80–120 từ)

run_id,chunk_id,before_text,after_text,status
run_20260410_2130,7,"`<div><br>&nbsp;&#8203;</div>`","[REMOVED_BY_SYSTEM]",quarantined
run_20260410_2130,3,"Tiền <b>hoàn lại</b>&nbsp;","Tiền hoàn lại",cleaned
_________________

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ viết một script webhook tự động phân tích file quarantine.log và đẩy cảnh báo trực tiếp lên kênh Slack/Teams của nhóm. Script sẽ tổng hợp số lượng dòng bị cách ly theo từng reason (PII, rỗng HTML, lỗi OCR) và kích hoạt cảnh báo khẩn nếu tỷ lệ dữ liệu bẩn vượt ngưỡng 5%. Việc này giúp tự động hóa khâu giám sát (monitoring) thay vì phải mở file CSV kiểm tra thủ công.
_________________
