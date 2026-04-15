"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows

# Pattern cho Rule 1: nhận diện lỗi trích xuất phổ biến từ Word/PDF hoặc OCR lỗi (Tiếng Anh + Tiếng Việt)
_BROKEN_ARTIFACTS_RE = re.compile(
    r"(error!\s*reference source not found|error!\s*bookmark not defined|lỗi!\s*chưa xác định được dấu trang|\{{2,}|_{3,}|-{3,})",
    re.IGNORECASE
)

# Pattern cho Rule 2: Các thẻ HTML phổ biến (<br>, <b>, <div>...), HTML entities (&nbsp;), ký tự ẩn (zero-width)
_HTML_TAGS_RE = re.compile(r"<[^>]+>|&[a-zA-Z0-9#]+;|[\u200b\ufeff]", re.IGNORECASE)

# Pattern cho Rule 3: Số điện thoại VN và Email cá nhân (gmail, yahoo, hotmail)
_PII_RE = re.compile(r"(\b0[3|5|7|8|9][0-9]{8}\b|[a-zA-Z0-9_.+-]+@(gmail|yahoo|hotmail)\.com)", re.IGNORECASE)


def _has_extraction_artifacts(text: str) -> Tuple[bool, str]:
    """
    Rule 1 (Mới): Phát hiện tàn dư lỗi từ quá trình trích xuất PDF/Word (Broken Artifacts).
    
    metric_impact:
      - Tăng RAG_Answer_Quality: Ngăn chặn LLM đọc các thông báo lỗi hệ thống bị lọt vào chunk và nhầm đó là một phần của chính sách.
      - Giảm Hallucination_Rate: Xóa bỏ dữ liệu nhiễu, giúp giảm rủi ro chatbot đưa ra câu trả lời vô nghĩa hoặc sai lệch.
      
    Trả về (has_artifact, matched_pattern).
    """
    match = _BROKEN_ARTIFACTS_RE.search(text)
    if match:
        return True, match.group(0)
    return False, ""


def _clean_html_and_formats(text: str) -> Tuple[bool, str]:
    """
    Rule 2: Phát hiện và làm sạch mã định dạng / HTML tags thừa (Format Stripping).
    
    metric_impact:
      - Tăng Readability_Score: Dữ liệu sạch sẽ, không bị rác định dạng khi hiển thị cho end-user.
      - Cải thiện Token_Efficiency: Tiết kiệm chi phí token do LLM không phải đọc các thẻ HTML vô nghĩa.
      
    Trả về (is_cleaned, cleaned_text).
    """
    new_text = _HTML_TAGS_RE.sub(" ", text)
    new_text = _norm_text(new_text)  # Chuẩn hóa lại khoảng trắng sau khi xóa tag
    return new_text != text, new_text


def _has_pii_leakage(text: str) -> Tuple[bool, str]:
    """
    Rule 3: Phát hiện rò rỉ dữ liệu nhạy cảm cá nhân (PII - Personally Identifiable Information).
    
    metric_impact:
      - Giảm PII_Leakage_Risk: Ngăn chặn RAG rò rỉ thông tin liên lạc cá nhân của nhân sự.
      - Tăng Compliance_Score: Đảm bảo tuân thủ các chính sách bảo mật dữ liệu của doanh nghiệp.
      
    Trả về (has_pii, matched_pii).
    """
    match = _PII_RE.search(text)
    if match:
        return True, match.group(0)
    return False, ""

def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # --- RULE 1 (Mới): Kiểm duyệt tàn dư lỗi trích xuất ---
        has_artifact, matched_err = _has_extraction_artifacts(text)
        if has_artifact:
            quarantine.append(
                {
                    **raw,
                    "reason": "extraction_artifact_detected",
                    "artifact_pattern": matched_err,
                }
            )
            continue
        # -----------------------------------------------------
        # --- RULE 2: Làm sạch mã định dạng / HTML tags thừa (Clean Rule) ---
        is_html_cleaned, text = _clean_html_and_formats(text)
        if not text:  # Nếu text chỉ toàn chứa thẻ HTML, xóa xong thành chuỗi rỗng
            quarantine.append({**raw, "reason": "empty_after_html_strip"})
            continue
        # -------------------------------------------------------------------

        # --- RULE 3: Cách ly đoạn văn bản rò rỉ dữ liệu cá nhân (PII) ---
        has_pii, pii_val = _has_pii_leakage(text)
        if has_pii:
            quarantine.append(
                {**raw, "reason": "pii_leakage_detected", "matched_text": pii_val}
            )
            continue
        # ----------------------------------------------------------------

        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# --- ĐOẠN CODE NÀY ĐỂ CHẠY FILE THỰC TẾ ---
if __name__ == "__main__":
    # Đảm bảo bạn đang để file data thô ở đúng đường dẫn, ví dụ: 'data/raw_export.csv'
    raw_path = Path("data/raw/policy_export_dirty.csv") # <-- Sửa lại đường dẫn này nếu cần
    
    if raw_path.exists():
        print("Đang tải dữ liệu thô...")
        raw_data = load_raw_csv(raw_path)
        
        print("Đang làm sạch dữ liệu...")
        cleaned_data, quarantine_data = clean_rows(raw_data)
        
        # Xuất file theo đúng yêu cầu đề bài
        cleaned_out_path = Path("artifacts/cleaned/cleaned_rows.csv")
        quarantine_out_path = Path("artifacts/quarantine/quarantine_log.csv")
        write_cleaned_csv(cleaned_out_path, cleaned_data)
        write_quarantine_csv(quarantine_out_path, quarantine_data)
        print(f"Xong! Đã xuất {len(cleaned_data)} dòng sạch và {len(quarantine_data)} dòng lỗi.")
        print(f"Quarantine file lưu tại: {quarantine_out_path}")
    else:
        print(f"Lỗi: Không tìm thấy file dữ liệu thô tại {raw_path}")
