# Quality report — Lab Day 10 (nhóm)

**run_id:** dirty-clean  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước | Sau | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | Không đổi — cùng file nguồn |
| cleaned_records | 6 | 6 | Giữ nguyên sau clean |
| quarantine_records | 4 | 4 | Các dòng thiếu `doc_id`, ngày không ISO, HR stale |
| Expectation halt? | Không | Không | Tất cả E1–E8 PASS trên dirty-clean |

**Expectation results (dirty-clean):**
- E1 `min_one_row`: PASS (6 rows)
- E2 `no_empty_doc_id`: PASS (0 empty)
- E3 `refund_no_stale_14d_window`: PASS (0 violations)
- E4 `chunk_min_length_8`: PASS (warn severity, 0 short)
- E5 `effective_date_iso_yyyy_mm_dd`: PASS (0 non-ISO)
- E6 `hr_leave_no_stale_10d_annual`: PASS (0 violations)
- E7 `no_duplicate_chunk_id`: PASS (0 duplicates) — *expectation mới*
- E8 `exported_at_not_empty`: PASS (warn severity, 0 missing) — *expectation mới*

---

## 2. Before / after retrieval (bắt buộc)

File tham chiếu: `artifacts/eval/dirty_clean_eval.csv` (dirty-clean) so sánh với `artifacts/eval/after_inject_bad.csv` (inject-bad)

**Câu hỏi then chốt:** refund window (`q_refund_window`)

**Trước (dirty-clean — sau khi fix):**
```csv
q_refund_window,policy_refund_v4,yêu cầu được gửi trong vòng 7 ngày làm việc...,yes,no,,3
```
- `contains_expected=yes` — câu trả lời có chứa "7 ngày"
- `hits_forbidden=no` — không có chunk "14 ngày" trong top-k

**Sau (inject-bad — cố ý không fix refund):**
```csv
q_refund_window,policy_refund_v4,yêu cầu được gửi trong vòng 7 ngày làm việc...,yes,yes,,3
```
- `contains_expected=yes` — vẫn có "7 ngày" ở top-1
- `hits_forbidden=yes` — **có chunk "14 ngày" stale trong top-k** → retrieval bị nhiễm

**Phân tích:** Khi chạy với `--no-refund-fix --skip-validate`, policy vẫn chứa "14 ngày làm việc" cũ. Mặc dù top-1 trả về "7 ngày", nhưng `hits_forbidden=yes` cho thấy vector cũ vẫn nằm trong top-k — đây là rủi ro nếu LLM aggregatet context. Pipeline chuẩn (dirty-clean) đã xoá hoàn toàn chunk "14 ngày" khỏi cleaned và index.

---

**Merit (khuyến nghị):** versioning HR — `q_leave_version`

**Trước (inject-bad):**
```csv
q_leave_version,hr_leave_policy,nhân viên dưới 3 năm...12 ngày phép năm...,yes,no,yes,3
```

**Sau (dirty-clean):**
```csv
q_leave_version,hr_leave_policy,nhân viên dưới 3 năm...12 ngày phép năm...,yes,no,yes,3
```

**Grading results (`artifacts/eval/grading_run.json`):**
- `gq_d10_01` (refund): `contains_expected=true`, `hits_forbidden=true` — inject-bad scenario, stale "14 ngày" detected in top-k
- `gq_d10_02` (P1 SLA): `contains_expected=true`, `hits_forbidden=false`
- `gq_d10_03` (HR leave): `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` — **Merit criteria satisfied**

**Nhận xét:** Cả hai scenario đều `top1_doc_expected=yes` vì cleaning rule `hr_leave_no_stale_10d` đã quarantine dòng chứa "10 ngày phép năm" cũ. Sự khác biệt nằm ở quarantine: inject-bad không quarantine nếu skip validate → vector cũ có thể còn trong index.

---

## 3. Freshness & monitor

**Kết quả:** `FAIL` (dự kiến)

**Lý do:** `freshness_check` so sánh `latest_exported_at` (2026-04-10T08:00:00) với `FRESHNESS_SLA_HOURS` (mặc định 24h). Dữ liệu mẫu đã cũ >24h → FAIL là **hợp lý** theo định nghĩa SLA.

**Giải thích SLA:**
- SLA 24h áp dụng cho "data snapshot" — dữ liệu export từ hệ thống nguồn
- Trong production thực, timestamp sẽ là thời điểm export thực tế, không phải ngày cố định trong CSV mẫu
- `exported_at_not_empty` (E8) đảm bảo monitoring có dữ liệu để tính SLA

---

## 4. Corruption inject (Sprint 3)

**Mô tả corruption:**
- **Kiểu:** Stale policy version + bỏ qua validation
- **Cách inject:** Chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
- **Tác động:** 
  - Không áp dụng rule "fix refund 14→7 ngày"
  - Bỏ qua `run_expectations()` → E3 không chạy, không halt dù có stale data
  - Kết quả: vector store chứa cả chunk "14 ngày" và "7 ngày"

**Cách phát hiện:**
- `eval_retrieval.py` quét toàn bộ top-k và đánh dấu `hits_forbidden=yes` khi thấy "14 ngày" trong context
- So sánh 2 file CSV cho thấy sự khác biệt rõ ràng ở cột `hits_forbidden`

---

## 5. Hạn chế & việc chưa làm

- **Chưa tích hợp Great Expectations / pydantic:** Expectation suite hiện là custom Python đơn giản. Có thể nâng cấp lên GE hoặc pydantic model để validate schema chặt hơn.
- **Freshness chỉ 1 boundary:** Hiện tại chỉ đo ở ingest (exported_at). Chưa có freshness check riêng cho publish boundary (thời điểm upsert vào Chroma).
- **Eval chưa mở rộng LLM-judge:** Chỉ dùng keyword matching. Có thể thêm LLM-as-judge cho semantic evaluation.
- **Rule versioning hard-code:** Cleaning rule HR dùng cutoff date cố định (2026). Chưa đọc từ contract/env như gợi ý Distinction.
