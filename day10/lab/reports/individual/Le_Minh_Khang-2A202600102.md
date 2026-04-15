# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Minh Khang  
**Vai trò:** Monitoring / Docs Owner  
**Ngày nộp:** 2026-04-15  

---

## 1. Tôi phụ trách phần nào?

Trong Day 10, tôi phụ trách phần monitoring và chuẩn hóa tài liệu vận hành của nhóm. Các file chính tôi làm việc gồm `monitoring/freshness_check.py`, `docs/runbook.md`, `docs/pipeline_architecture.md`, `docs/data_contract.md`, và `docs/quality_report_template.md`. Trách nhiệm của tôi là đảm bảo mỗi lần chạy pipeline đều có thể truy vết được qua `run_id`, manifest, log, và có quy trình xử lý rõ khi xuất hiện tín hiệu xấu (đặc biệt là stale data và `hits_forbidden`).

Tôi phối hợp với owner cleaning/quality để đọc đúng ý nghĩa từng expectation trong log và chuyển thành hướng dẫn xử lý thực tế trong runbook. Tôi cũng phối hợp với owner eval để dùng cùng một cặp artifact before/after cho báo cáo nhóm: `artifacts/eval/grading_run_inject_bad_report.jsonl` (inject) và `artifacts/eval/grading_run.jsonl` (clean). Nhờ vậy phần tài liệu không bị tách rời code, mà phản ánh đúng những gì pipeline thực sự ghi nhận.

**Bằng chứng:** các tài liệu trong `day10/lab/docs/` đã được viết lại theo trạng thái code hiện tại, và quick-check được ghi nhận bằng output command trên hai file grading nêu trên.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là tách rõ “gating quality” và “monitoring freshness”. Cụ thể, expectation severity `halt` dùng để chặn dữ liệu bẩn trước khi publish vào vector store; còn freshness trong `freshness_check.py` được giữ như một tín hiệu vận hành (PASS/WARN/FAIL) thay vì chặn cứng trong toàn bộ bối cảnh lab.

Lý do: dữ liệu mẫu của lab có `latest_exported_at=2026-04-10T08:00:00`, nên tại thời điểm chạy sẽ thường vượt SLA 24 giờ. Nếu coi freshness FAIL là blocker tuyệt đối trong môi trường thực hành, nhóm sẽ không thể chạy được phần so sánh before/after của Sprint 3. Vì vậy tôi giữ logic “pipeline vẫn hoàn thành nhưng phải log và nêu rõ lý do FAIL” để vừa đúng tinh thần observability vừa không làm hỏng flow học tập.

Quyết định này cũng giúp runbook rõ ràng hơn: khi FAIL do stale timestamp, nhóm phải điều tra upstream data freshness thay vì nhảy ngay sang debug model/prompt. Tôi xem đây là điểm then chốt để giữ kỷ luật debug theo đúng thứ tự data-first.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly tôi gặp trực tiếp là kết quả quick-check không ổn định giữa các lần chạy do trạng thái index thay đổi theo run (inject vs clean). Ở trạng thái inject (`run_id=inject-bad-report`), quick-check cho `gq_d10_01 hits_forbidden=true`; sau khi restore clean (`run_id=final-good`) thì cùng câu này phải về `hits_forbidden=false`.

Trong quá trình verify, tôi còn gặp lỗi hiển thị Unicode khi chạy script check trên terminal Windows (lỗi mã hóa ký tự), làm việc đọc output khó tin cậy. Cách xử lý là chạy lệnh với `PYTHONIOENCODING=utf-8` để giữ output nhất quán. Sau đó tôi tách artifact rõ theo trạng thái:

- inject evidence: `artifacts/eval/grading_run_inject_bad_report.jsonl`
- clean evidence: `artifacts/eval/grading_run.jsonl`

Cách làm này giúp tránh nhầm giữa “file đúng” và “index đang ở trạng thái nào” khi đối chiếu báo cáo.

---

## 4. Bằng chứng trước / sau

Tôi dùng cặp file grading để chứng minh before/after:

- **Inject** (`grading_run_inject_bad_report.jsonl`):
  `gq_d10_01 ... "contains_expected": true, "hits_forbidden": true`
- **Clean** (`grading_run.jsonl`):
  `gq_d10_01 ... "contains_expected": true, "hits_forbidden": false`

Điểm quan trọng là ở cả hai trạng thái, hệ thống đều có thể “nhìn thấy đáp án đúng” (`contains_expected=true`), nhưng chỉ trạng thái clean mới loại được context cấm khỏi top-k. Đây là bằng chứng trực tiếp cho giá trị của publish boundary sạch + runbook giám sát theo `hits_forbidden`, thay vì chỉ nhìn top-1 hoặc câu trả lời cuối.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ bổ sung một script “post-run checklist” để tự động chạy theo thứ tự: `freshness`, `grading_run`, `instructor_quick_check`, rồi ghi snapshot ngắn vào một file `artifacts/release_notes/<run_id>.md`. Việc này giúp giảm sai sót thao tác thủ công, đồng thời tạo một audit trail rõ cho mỗi lần publish dữ liệu vào collection.
