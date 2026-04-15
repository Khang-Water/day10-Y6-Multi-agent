# Runbook - Lab Day 10

## 1. Scope
Runbook cho incident data pipeline ảnh hưởng retrieval của trợ lý CS + IT Helpdesk.

## 2. Trigger conditions
- User hỏi refund window nhưng câu trả lời hoặc context chứa "14 ngày làm việc".
- `instructor_quick_check` báo `gq_d10_01 hits_forbidden=true`.
- `freshness_check` trả về `FAIL`.
- Expectation severity `halt` bị fail khi chạy pipeline.

## 3. Severity
| Level | Điều kiện | Mục tiêu xử lý |
|---|---|---|
| Sev-1 | dữ liệu sai đang phục vụ người dùng (forbidden top-k) | chặn publish sai và sửa trong phiên hiện tại |
| Sev-2 | freshness fail nhưng nội dung chưa sai | đánh giá risk và thông báo stale |
| Sev-3 | warn nhỏ, không ảnh hưởng trả lời | ghi nhận và xử lý theo batch tiếp theo |

## 4. Triage checklist
1. Xác nhận run gần nhất.
```powershell
Get-ChildItem artifacts\manifests | Sort-Object LastWriteTime -Descending | Select-Object -First 3
```
2. Kiểm tra quality signal từ log.
```powershell
Get-Content artifacts\logs\run_<run-id>.log
```
3. Kiểm tra quarantine reason.
```powershell
Get-Content artifacts\quarantine\quarantine_<run-id>.csv
```
4. Kiểm tra retrieval evidence.
```powershell
python eval_retrieval.py --out artifacts/eval/before_after_eval.csv
python grading_run.py --out artifacts/eval/grading_run.jsonl
$env:PYTHONIOENCODING='utf-8'; python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl
```

## 5. Standard mitigation
### 5.1 Case A - Forbidden stale policy trong top-k
1. Chạy pipeline clean mode, không skip validate.
```powershell
python etl_pipeline.py run --run-id final-good
```
2. Xác nhận có `embed_prune_removed` hoặc trạng thái index đã refresh.
3. Regenerate `grading_run.jsonl` và verify quick check PASS.

### 5.2 Case B - Freshness FAIL
1. Xác định `latest_exported_at` và `age_hours` trong manifest.
2. Nếu dữ liệu nguồn thực sự cũ, gắn trạng thái stale và yêu cầu refresh upstream.
3. Nếu môi trường demo, ghi rõ trong report rằng FAIL là expected monitoring signal.

### 5.3 Case C - Expectation halt
1. Mở expectation fail detail trong log.
2. Sửa dữ liệu nguồn hoặc cleaning rule.
3. Rerun không dùng `--skip-validate`.

## 6. Recovery validation
- Manifest mới được tạo: `artifacts/manifests/manifest_<new-run-id>.json`.
- `instructor_quick_check --grading` pass đủ 3 merit checks.
- `q_refund_window` có `contains_expected=yes`, `hits_forbidden=no`.
- Nếu có freshness fail, đã có giải thích rõ trong runbook/report.

## 7. Rollback strategy
- Không dùng snapshot index không rõ nguồn.
- Rollback chuẩn là rerun từ raw input hợp lệ với run_id mới.
- Giữ lại đầy đủ artifacts của run lỗi để phục vụ postmortem.

## 8. Communication template
```text
Incident: <short title>
Impact: <ai bị ảnh hưởng, câu hỏi nào bị sai>
Detected by: <expectation/eval/grading/freshness>
Root cause: <data issue / config / process>
Mitigation: <lệnh đã chạy>
Validation: <quick-check output>
Status: <resolved / monitoring>
Owner: <name>
```

## 9. Preventive actions
- Bổ sung expectation hoặc tighten rule cho pattern đã gây lỗi.
- Tự động hóa quick-check sau mỗi run quan trọng.
- Chuẩn hóa quy trình "inject only in isolated run_id" để tránh nhiễm index production/demo.
