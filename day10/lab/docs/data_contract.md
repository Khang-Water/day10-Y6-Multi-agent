# Data Contract - Lab Day 10

File này là bản mô tả human-readable của [data_contract.yaml](C:/Users/minhk/day10/day10-Y6-Multi-agent/day10/lab/contracts/data_contract.yaml).

## 1. Mục tiêu contract
- Chuẩn hóa dữ liệu trước khi embed vào Chroma collection `day10_kb`.
- Giữ ranh giới rõ giữa dữ liệu được publish (`cleaned`) và dữ liệu bị cô lập (`quarantine`).
- Ngăn stale policy (refund 14 ngày, HR 10 ngày) đi vào retrieval top-k.
- Có thể quan sát được chất lượng theo run qua `manifest`, `log`, `eval`.

## 2. Dataset scope
- `dataset`: `kb_chunk_export`
- `version`: `1.0`
- `owner_team`: `C401-Y6`
- `allowed_doc_ids`: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`, `access_control_sop`
- `freshness_sla_hours`: `24`

## 3. Source map
| Source | Ingest | Failure mode chính | Detection |
|---|---|---|---|
| `data/raw/policy_export_dirty.csv` | CSV batch qua `etl_pipeline.py run` | missing date, format sai, duplicate, doc_id lạ | `raw_records`, `quarantine_records`, expectation halt |
| `data/docs/policy_refund_v4.txt` | Canonical policy | stale text "14 ngày làm việc" | `refund_no_stale_14d_window`, `hits_forbidden` |
| `data/docs/hr_leave_policy.txt` | Canonical policy | conflict version "10 ngày phép năm" | `hr_leave_no_stale_10d_annual`, `q_leave_version` |
| `data/docs/sla_p1_2026.txt` | Canonical policy | drift nội dung hoặc thiếu cập nhật | eval `q_p1_sla`, grading `gq_d10_02` |
| `data/docs/it_helpdesk_faq.txt` | Canonical policy | PII leakage | `pii_leakage_detected` trong quarantine |
| Chroma `day10_kb` | `upsert` theo `chunk_id` + `prune` id thừa | stale vector còn tồn tại sau rerun | `embed_prune_removed`, eval/grading top-k |

## 4. Cleaned schema
| Column | Type | Required | Constraint |
|---|---|---|---|
| `chunk_id` | string | yes | unique, stable hash (`doc_id + text + seq`) |
| `doc_id` | string | yes | thuộc `allowed_doc_ids` |
| `chunk_text` | string | yes | min length 8 |
| `effective_date` | date | yes | ISO `YYYY-MM-DD` |
| `exported_at` | datetime string | yes (warn nếu thiếu) | phục vụ freshness check |

## 5. Quality gates (theo code hiện tại)
- `min_one_row` (halt)
- `no_empty_doc_id` (halt)
- `refund_no_stale_14d_window` (halt)
- `chunk_min_length_8` (warn)
- `effective_date_iso_yyyy_mm_dd` (halt)
- `hr_leave_no_stale_10d_annual` (halt)
- `no_duplicate_chunk_id` (halt)
- `exported_at_not_empty` (warn)

## 6. Quarantine policy
| Reason | Action |
|---|---|
| `unknown_doc_id` | quarantine, không publish |
| `missing_effective_date` | quarantine |
| `invalid_effective_date_format` | quarantine |
| `stale_hr_policy_effective_date` | quarantine |
| `missing_chunk_text` | quarantine |
| `extraction_artifact_detected` | quarantine |
| `empty_after_html_strip` | quarantine |
| `pii_leakage_detected` | quarantine |
| `duplicate_chunk_text` | quarantine |

## 7. Freshness contract
- Nguồn timestamp: `latest_exported_at` trong manifest.
- Rule: `age_hours <= sla_hours` thì `PASS`, ngược lại `FAIL`.
- Mặc định SLA: `FRESHNESS_SLA_HOURS=24`.
- Freshness là monitoring signal, không chặn pipeline run.

## 8. Idempotency contract
- Publish boundary là file `cleaned_<run_id>.csv`.
- Embed sử dụng `upsert(ids=chunk_id, ...)`.
- Trước khi upsert, pipeline `prune` toàn bộ id không còn trong cleaned snapshot hiện tại.
- Yêu cầu: rerun cùng cleaned snapshot không tạo duplicate vector.

## 9. Change management
- Khi thêm `doc_id` mới:
  - cập nhật `allowed_doc_ids` trong code và contract,
  - cập nhật canonical source map,
  - thêm test question/eval để chứng minh không hồi quy.
- Khi đổi policy business (ví dụ refund window):
  - cập nhật canonical docs,
  - cập nhật expectation liên quan,
  - rerun pipeline và lưu before/after evidence.
