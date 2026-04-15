# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** C401-Y6  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Hoàng Thị Thanh Tuyền | Pipeline Coordinator & Ingestion Owner | hoangthanhtuyen1412@gmail.com |
| Nguyễn Hồ Bảo Thiên | Cleaning & Quality Owner | thiennguyen3703@gmail.com |
| Võ Thanh Chung | Quality / Expectations Owner | vothanhchung95@gmail.com |
| Dương Khoa Điềm | Embed & Idempotency Owner | duongkhoadiemp@gmail.com |
| Đỗ Thế Anh | Eval & Inject (Before/After) Owner | anh.dothe47@gmail.com |
| Lê Minh Khang | Monitoring / Docs Owner | minhkhangle2k4@gmail.com |

**Ngày nộp:** 2026-04-15  
**Repo:** https://github.com/Khang-Water/day10-Y6-Data-pipeline

---

## 1. Pipeline tổng quan

Nhóm triển khai pipeline theo chuỗi `ingest -> clean -> validate -> embed -> monitor` trên cùng bài toán policy nội bộ (refund, SLA, FAQ, HR) để phục vụ retrieval của Day 08/09. Nguồn vào là `data/raw/policy_export_dirty.csv`; đầu ra gồm `artifacts/cleaned/cleaned_<run_id>.csv`, `artifacts/quarantine/quarantine_<run_id>.csv`, `artifacts/manifests/manifest_<run_id>.json` và vector snapshot trong collection `day10_kb`.

Pipeline có hai lớp kiểm soát chính. Lớp 1 là `cleaning_rules.py` để loại dữ liệu không hợp lệ (doc_id lạ, ngày sai định dạng, stale HR version, PII, artifact extraction). Lớp 2 là `expectations.py` để quyết định chặn/cho chạy tiếp trước khi embed. Với run tốt `final-good`, log ghi: `raw_records=17`, `cleaned_records=8`, `quarantine_records=9`, toàn bộ expectation severity `halt` đều `OK`, và `embed_prune_removed=1` trước khi upsert 8 chunk.

Freshness được tính từ `latest_exported_at` trong manifest. Do dữ liệu mẫu có timestamp `2026-04-10T08:00:00`, tại thời điểm chạy lab thì tuổi dữ liệu vượt SLA 24 giờ nên trạng thái monitor là `FAIL` (expected for demo dataset), nhưng pipeline vẫn hoàn thành để phục vụ bài thực hành observability.

**Lệnh chạy một dòng (run sạch):**

```bash
python etl_pipeline.py run --run-id final-good
```

---

## 2. Cleaning & expectation

Nhóm kế thừa baseline rule và mở rộng theo hướng “quality-as-code có đo được”. Ba rule mới tập trung vào lỗi thực tế từ export tài liệu:

1. `extraction_artifact_detected`: bắt các chuỗi lỗi trích xuất kiểu `Error! Reference source not found`.  
2. `empty_after_html_strip`: làm sạch HTML/format thừa; nếu rỗng sau strip thì quarantine.  
3. `pii_leakage_detected`: phát hiện số điện thoại/email cá nhân và cách ly khỏi cleaned.

Expectation mới được thêm để khóa chất lượng publish boundary:

- `no_duplicate_chunk_id` (halt): bảo vệ idempotency khi upsert Chroma.
- `exported_at_not_empty` (warn): cảnh báo dữ liệu thiếu mốc thời gian freshness.

### 2a. Bảng metric_impact

| Rule / Expectation mới | Trước (inject-bad-report) | Sau (final-good) | Chứng cứ |
|---|---:|---:|---|
| `extraction_artifact_detected` | 2 dòng bị quarantine | 2 dòng bị quarantine | `quarantine_*`: `reason=extraction_artifact_detected` count=2 |
| `pii_leakage_detected` | 2 dòng bị quarantine | 2 dòng bị quarantine | `quarantine_*`: `reason=pii_leakage_detected` count=2 |
| `empty_after_html_strip` | 1 dòng bị quarantine | 1 dòng bị quarantine | `quarantine_*`: `reason=empty_after_html_strip` count=1 |
| `refund_no_stale_14d_window` (halt) | FAIL, `violations=1` | OK, `violations=0` | `run_inject-bad-report.log` vs `run_final-good.log` |
| `no_duplicate_chunk_id` (halt) | OK, `duplicate_chunk_ids=0` | OK, `duplicate_chunk_ids=0` | `run_*.log` |

Một điểm quan trọng: run inject có chủ đích (`--no-refund-fix --skip-validate`) vẫn cho pipeline đi tiếp để phục vụ đo before/after, nhưng log luôn ghi rõ `WARN: expectation failed but --skip-validate` để tránh nhầm với run production-ready.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent

Nhóm dùng hai lớp bằng chứng:

1. **Eval top-k=3** (`after_inject_bad.csv`, `before_after_eval_final-good.csv`) để theo dõi câu hỏi chuẩn retrieval.  
2. **Grading top-k=5** (`grading_run_inject_bad_report.jsonl`, `grading_run.jsonl`) để bắt nhiễm stale sâu hơn trong top-k.

Kết quả chính:

- Ở inject run (`grading_run_inject_bad_report.jsonl`), `gq_d10_01` có `contains_expected=true` nhưng `hits_forbidden=true`. Nghĩa là hệ thống vẫn nhìn thấy câu đúng “7 ngày”, nhưng top-k còn dính context cấm (“14 ngày làm việc”).
- Ở clean run (`grading_run.jsonl`), cùng câu `gq_d10_01` chuyển sang `hits_forbidden=false`.
- `gq_d10_02` (SLA 4 giờ) ổn định ở cả hai trạng thái (`contains_expected=true`, `hits_forbidden=false`).
- `gq_d10_03` (HR leave 12 ngày) giữ đúng `top1_doc_id=hr_leave_policy` và `top1_doc_matches=true` sau khi clean.

Bài học quan trọng là chỉ nhìn `contains_expected` chưa đủ; cần thêm `hits_forbidden` trên toàn top-k để tránh false sense of correctness. Đây là lý do nhóm giữ cơ chế prune stale ids trước khi upsert và duy trì bài kiểm tra grading riêng cho tình huống inject.

---

## 4. Freshness & monitoring

Nhóm đặt SLA freshness = 24 giờ (`FRESHNESS_SLA_HOURS=24`) theo contract hiện tại. Trên run `final-good`, manifest ghi `latest_exported_at=2026-04-10T08:00:00`; freshness check trả `FAIL` với `reason=freshness_sla_exceeded`. Nhóm coi đây là tín hiệu monitoring hợp lệ vì dữ liệu lab cố ý cũ để minh họa incident triage, không phải lỗi code pipeline.

Trong runbook, nhóm định nghĩa:

- `PASS`: dữ liệu trong SLA.
- `WARN`: thiếu timestamp hoặc không đủ dữ liệu để tính tuổi dữ liệu.
- `FAIL`: tuổi dữ liệu vượt SLA hoặc manifest lỗi.

Với môi trường production, nhóm sẽ không publish khi freshness `FAIL`; còn trong lab hiện tại, pipeline vẫn chạy để hoàn tất phần thực hành so sánh before/after và viết postmortem.

---

## 5. Liên hệ Day 09

Day 10 là lớp data reliability cho retrieval worker ở Day 09. Collection `day10_kb` được cập nhật theo snapshot sạch giúp supervisor/worker tránh trả lời dựa trên chunk stale. Về mặt kiến trúc, Day 09 xử lý orchestration (route, trace, synthesis), còn Day 10 đảm bảo input knowledge base đúng version, có lineage theo `run_id`, và có kiểm tra chất lượng trước publish.

---

## 6. Rủi ro còn lại & việc chưa làm

- Freshness hiện chỉ là signal, chưa có cơ chế hard-block theo môi trường (dev/stage/prod).
- Rule phát hiện PII mới tập trung vào pattern cơ bản; chưa phủ hết định dạng số quốc tế hoặc email nội bộ doanh nghiệp.
- Chưa externalize đầy đủ policy cutoff từ contract vào toàn bộ rule/expectation (một phần vẫn nằm trong code).
- Chưa có dashboard time-series cho trend `hits_forbidden`, `quarantine_records`, `age_hours` theo run_id.
