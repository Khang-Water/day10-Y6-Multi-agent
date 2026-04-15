# Phân Công Nhiệm Vụ — Lab Day 10: Data Pipeline & Data Observability

**Môn:** AI in Action (AICB-P1)  
**Ngày:** 2026-04-15  
**Repo:** day10-Y6-Data-pipeline

---

## Thành viên & Vai trò

| # | Họ tên | MSSV | Vai trò | Sprint chính |
|---|--------|------|---------|--------------|
| 1 | Hoàng Thị Thanh Tuyền | 2A202600074 | Pipeline Coordinator & Ingestion Owner | 1, 4 |
| 2 | Nguyễn Hồ Bảo Thiên | 2A202600163 | Cleaning Rules Owner | 1–2 |
| 3 | Võ Thanh Chung | 2A202600335 | Quality / Expectations Owner | 2–3 |
| 4 | Dương Khoa Diễm | 2A202600366 | Embed & Idempotency Owner | 2–3 |
| 5 | Đỗ Thế Anh | 2A202600040 | Eval & Inject (Before/After) Owner | 3 |
| 6 | Lê Minh Khang | 2A2020600102 | Monitoring & Docs Owner | 4 |

---

## Chi Tiết Từng Người

---

### 1. Hoàng Thị Thanh Tuyền — Pipeline Coordinator & Ingestion Owner

**Files phải commit:**

- `etl_pipeline.py` — đảm bảo `cmd_run` log đủ `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`; kiểm tra các flag `--run-id`, `--raw`, `--no-refund-fix`, `--skip-validate` hoạt động đúng
- `contracts/data_contract.yaml` — điền `owner`, `SLA`, ít nhất 2 nguồn dữ liệu
- `reports/group_report.md` — tổng hợp và điền thông tin nhóm (phối hợp với Lê Minh Khang)

**Nhiệm vụ cụ thể:**

- Chạy `python etl_pipeline.py run --run-id sprint1` lần đầu, lưu log làm baseline
- Điền `contracts/data_contract.yaml` với `owner`, `sla_hours`, source map (≥ 2 nguồn)
- Setup môi trường `.env`, `requirements.txt` cho cả nhóm
- Viết báo cáo cá nhân: `reports/individual/HoangThiThanhTuyen_2A202600074.md`

---

### 2. Nguyễn Hồ Bảo Thiên — Cleaning Rules Owner

**Files phải commit:**

- `transform/cleaning_rules.py` — thêm **≥ 3 rule mới** (mỗi rule có comment/docstring, không được trivial)
- `artifacts/quarantine/` — ít nhất 1 file CSV quarantine từ run thật

**Nhiệm vụ cụ thể:**

- Baseline đã có: allowlist `doc_id`, normalize date, quarantine HR stale, dedupe, fix refund
- Gợi ý rule mới có thể thêm: strip BOM/control characters, whitespace chuẩn hoá cứng hơn, min chunk length, detect malformed `chunk_id`, flag `exported_at` rỗng, v.v.
- **Bắt buộc:** điền bảng `metric_impact` trong `reports/group_report.md` — mỗi rule mới phải có số liệu trước/sau (ví dụ: `quarantine_records` tăng bao nhiêu khi inject BOM)
- Viết báo cáo cá nhân: `reports/individual/NguyenHoBaoThien_2A202600163.md`

---

### 3. Võ Thanh Chung — Quality / Expectations Owner

**Files phải commit:**

- `quality/expectations.py` — thêm **≥ 2 expectation mới**, ghi rõ severity (`warn` vs `halt`)
- `docs/quality_report.md` — hoàn thiện từ `docs/quality_report_template.md` (có `run_id` + phân tích kết quả)

**Nhiệm vụ cụ thể:**

- Baseline đã có: E1–E6 (`min_one_row`, `no_empty_doc_id`, `refund_no_stale_14d`, `chunk_min_length_8`, `effective_date_iso`, `hr_no_stale_10d`)
- Gợi ý expectation mới: `no_duplicate_chunk_id`, `exported_at_not_empty`, `chunk_text_no_control_chars`, `all_doc_ids_in_allowlist`, v.v.
- Phân biệt rõ cái nào là `halt`, cái nào là `warn` — ghi lý do trong code comment
- Viết báo cáo cá nhân: `reports/individual/Vo_Thanh_Chung-2A202600335.md`

---

### 4. Dương Khoa Diễm — Embed & Idempotency Owner

**Files phải commit:**

- `etl_pipeline.py` — phần embed vào Chroma sau clean/validate: upsert theo `chunk_id`, prune id cũ (phối hợp với Hoàng Thị Thanh Tuyền)
- `artifacts/manifests/manifest_<run-id>.json` — ít nhất 1 file manifest từ run thật
- `artifacts/logs/run_<run-id>.log` — log có `embed_prune_removed`, `embed_upserted`

**Nhiệm vụ cụ thể:**

- Đảm bảo embed **idempotent**: chạy pipeline 2 lần không tạo duplicate vector
- Sau publish: xoá các `chunk_id` trong Chroma không còn có trong cleaned (prune)
- Test bằng cách chạy `python etl_pipeline.py run` 2 lần, so sánh collection size — ghi kết quả vào log
- Viết báo cáo cá nhân: `reports/individual/Duong_Khoa_Diem-2A202600366.md`

---

### 5. Đỗ Thế Anh — Eval & Inject (Before/After) Owner

**Files phải commit:**

- `eval_retrieval.py` — kiểm tra hoạt động, có thể mở rộng thêm query nếu cần
- `grading_run.py` — chạy sau 17:00, output `artifacts/eval/grading_run.jsonl`
- `artifacts/eval/before_after_eval.csv` — kết quả so sánh sau clean vs sau inject
- `artifacts/eval/after_inject_bad.csv` — kết quả eval khi pipeline inject xấu (Sprint 3)

**Nhiệm vụ cụ thể:**

- Sprint 3: chạy inject có chủ đích:
  ```bash
  python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
  python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
  ```
- So sánh 2 file eval, viết đoạn văn trong `group_report.md` chứng minh retrieval **tệ hơn** khi inject (đặc biệt câu `q_refund_window`)
- Chạy `grading_run.py`, đảm bảo đúng **3 dòng** `gq_d10_01`…`gq_d10_03`, JSON hợp lệ trước 18:00
- Viết báo cáo cá nhân: `reports/individual/Do_The_Anh-2A202600040.md`

---

### 6. Lê Minh Khang — Monitoring & Docs Owner

**Files phải commit:**

- `monitoring/freshness_check.py` — đảm bảo chạy được, giải thích PASS/WARN/FAIL
- `docs/pipeline_architecture.md` — điền sơ đồ Mermaid/ASCII + bảng ranh giới trách nhiệm với tên thật từng thành viên
- `docs/data_contract.md` — điền source map (≥ 2 nguồn), schema cleaned, quy tắc quarantine
- `docs/runbook.md` — điền đủ 5 mục: Symptom → Detection → Diagnosis → Mitigation → Prevention

**Nhiệm vụ cụ thể:**

- Chạy `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json`
- Ghi vào `runbook.md`: SLA chọn bao nhiêu giờ (`FRESHNESS_SLA_HOURS`), tại sao FAIL trên data mẫu là hợp lý, cách điều chỉnh
- `docs/pipeline_architecture.md` phải có bảng "Ranh giới trách nhiệm" điền đúng owner từng thành phần
- Viết báo cáo cá nhân: `reports/individual/2A2020600102_LeMinhKhang.md`

---

## Tóm Tắt Files Commit Theo Người

| Thành viên            | Files phải commit                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------ |
| Hoàng Thị Thanh Tuyền | `etl_pipeline.py`, `contracts/data_contract.yaml`, `reports/group_report.md`                                 |
| Nguyễn Hồ Bảo Thiên   | `transform/cleaning_rules.py`, `artifacts/quarantine/*.csv`                                                  |
| Võ Thanh Chung        | `quality/expectations.py`, `docs/quality_report.md`                                                          |
| Dương Khoa Diễm       | `etl_pipeline.py` (embed section), `artifacts/manifests/*.json`, `artifacts/logs/*.log`                      |
| Đỗ Thế Anh            | `eval_retrieval.py`, `artifacts/eval/before_after_eval.csv`, `artifacts/eval/grading_run.jsonl`              |
| Lê Minh Khang         | `monitoring/freshness_check.py`, `docs/pipeline_architecture.md`, `docs/data_contract.md`, `docs/runbook.md` |

---

## Lưu Ý Quan Trọng (Tránh Bị Trừ Điểm)

1. **Mỗi người phải có commit riêng** vào file mình phụ trách — không commit chung 1 người
2. **Rule/expectation mới phải có số liệu thay đổi thực tế** trong bảng `metric_impact` của `group_report.md` — rule trivial sẽ bị trừ điểm
3. **Grading JSONL** phải đúng 3 dòng, JSON hợp lệ, commit trước deadline **18:00**
4. **Báo cáo cá nhân** (400–650 từ): phải ghi `run_id` thật, tên file thật, không được paraphrase slide — 0 điểm nếu thiếu bằng chứng
5. **Report không được copy nhau** giữa các thành viên — 0/40 điểm cá nhân cho các bên vi phạm

---

## Thứ Tự Chạy Đề Xuất (Cả Nhóm)

```bash
# Sprint 1 — Hoàng Thị Thanh Tuyền khởi động
python etl_pipeline.py run --run-id sprint1

# Sprint 2 — sau khi Nguyễn Hồ Bảo Thiên & Võ Thanh Chung thêm rule/expectation
python etl_pipeline.py run --run-id sprint2

# Sprint 3 — Đỗ Thế Anh inject & eval
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
python etl_pipeline.py run --run-id sprint3-clean
python eval_retrieval.py --out artifacts/eval/before_after_eval.csv

# Sprint 4 — freshness check
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3-clean.json

# Sau 17:00 — grading
python grading_run.py --out artifacts/eval/grading_run.jsonl
```
