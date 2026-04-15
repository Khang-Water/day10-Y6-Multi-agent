# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Võ Thanh Chung  
**MSSV:** 2A202600335  
**Vai trò:** Quality / Expectations Owner  
**Ngày nộp:** 2026-04-15  

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `quality/expectations.py` — viết và mở rộng expectation suite từ E1–E6 baseline lên E1–E8; gắn severity `halt` hoặc `warn` cho từng expectation; hàm `run_expectations()` trả về `(results, should_halt)` để `etl_pipeline.py` quyết định dừng pipeline.
- `docs/quality_report.md` — hoàn thiện từ template; ghi rõ `run_id=sprint2`, kết quả từng expectation, phân tích before/after retrieval (`hits_forbidden`), và mục freshness.

**Kết nối với thành viên khác:**

- Phối hợp với **Nguyễn Hồ Bảo Thiên** (Cleaning Rules Owner): expectation E3 và E6 kiểm tra đầu ra của `cleaning_rules.py` — nếu cleaning bỏ sót chunk stale, E3/E6 sẽ halt pipeline.
- Kết quả E7 (`no_duplicate_chunk_id`) bảo vệ **Dương Khoa Diễm** (Embed Owner): duplicate `chunk_id` vào Chroma gây overwrite lặng lẽ, E7 dừng pipeline trước khi embed.

**Bằng chứng (commit):**

- `412b909` — `Chung: expectations.py complete`
- `be72314` — `Chung: quality_report.md`

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Khi thêm E7 (`no_duplicate_chunk_id`) và E8 (`exported_at_not_empty`), tôi phải chọn severity `halt` hay `warn` cho mỗi expectation.

**E7 → halt:** Nếu hai chunk có cùng `chunk_id` nhưng nội dung khác nhau, Chroma sẽ overwrite lặng lẽ khi upsert. Kết quả: vector store chứa nội dung sai mà không có lỗi nào được raise — rủi ro trực tiếp đến chất lượng retrieval. Vì vậy tôi chọn `halt` để dừng pipeline ngay, không cho phép embed xảy ra khi dữ liệu đã mâu thuẫn.

**E8 → warn:** Nếu `exported_at` rỗng, `freshness_check.py` không tính được tuổi dữ liệu so với SLA, nhưng pipeline vẫn chạy được — cleaned CSV và Chroma đều đúng. Tôi chọn `warn` vì ảnh hưởng chỉ ở tầng monitoring, không ảnh hưởng tầng serving. Hạ severity ở đây tránh false halt khi chỉ mất một trường metadata.

Nguyên tắc: `halt` khi lỗi sẽ gây sai dữ liệu downstream; `warn` khi lỗi chỉ ảnh hưởng observability.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:** Khi chạy `python etl_pipeline.py run --run-id sprint2` lần đầu, log hiển thị `freshness_check=FAIL` dù tất cả expectations đều PASS.

**Metric phát hiện:** Dòng log:
```
freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.883, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Phân tích:** `latest_exported_at` trong dữ liệu mẫu là `2026-04-10T08:00:00` — cố định trong CSV nguồn, cách ngày chạy 5 ngày (120 giờ), vượt `SLA_HOURS=24`. Đây không phải lỗi code mà là **thiết kế có chủ đích** của lab để chứng minh monitoring phát hiện data cũ.

**Xử lý:** Tôi ghi rõ trong `docs/quality_report.md` (mục 3) rằng `FAIL` là **kết quả hợp lý** — dữ liệu mẫu có `exported_at` cố định trong quá khứ. Đồng thời, E8 (`exported_at_not_empty`, warn) đảm bảo trường này luôn có giá trị để freshness check có thể tính toán, không bị skip vì `None`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**run_id:** `sprint2` (commit `412b909`)

Kết quả từ `artifacts/logs/run_sprint2.log`:

```
expectation[no_duplicate_chunk_id] OK (halt) :: duplicate_chunk_ids=0
expectation[exported_at_not_empty] OK (warn) :: missing_exported_at=0
embed_upsert count=6 collection=day10_kb
manifest_written=artifacts\manifests\manifest_sprint2.json
```

Manifest `artifacts/manifests/manifest_sprint2.json` xác nhận:
```json
"raw_records": 10,
"cleaned_records": 6,
"quarantine_records": 4,
"skipped_validate": false
```

Cả 8 expectations (E1–E8) đều PASS trên `run_id=sprint2`. E7 và E8 là hai expectation tôi thêm mới so với baseline E1–E6 — đây là bằng chứng suite đã mở rộng và chạy thật trên data thật.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ thêm expectation **`all_doc_ids_in_allowlist`** (halt): so sánh tập `doc_id` trong cleaned CSV với danh sách cho phép trong `contracts/data_contract.yaml`. Hiện tại pipeline chấp nhận bất kỳ `doc_id` nào vượt qua cleaning — nếu một document lạ bị inject vào raw data, pipeline vẫn embed nó mà không ai hay. Expectation này sẽ chặn tầng đó trước khi publish.
