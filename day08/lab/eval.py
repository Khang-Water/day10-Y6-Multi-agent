"""
eval.py — Sprint 4: Evaluation & Scorecard
==========================================
Mục tiêu Sprint 4 (60 phút):
  - Chạy 10 test questions qua pipeline
  - Chấm điểm theo 4 metrics: Faithfulness, Relevance, Context Recall, Completeness
  - So sánh baseline vs variant
  - Ghi kết quả ra scorecard

Definition of Done Sprint 4:
  ✓ Demo chạy end-to-end (index → retrieve → answer → score)
  ✓ Scorecard trước và sau tuning
  ✓ A/B comparison: baseline vs variant với giải thích vì sao variant tốt hơn

A/B Rule (từ slide):
  Chỉ đổi MỘT biến mỗi lần để biết điều gì thực sự tạo ra cải thiện.
  Đổi đồng thời chunking + hybrid + rerank + prompt = không biết biến nào có tác dụng.
"""

import json
import csv
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rag_answer import rag_answer
from openai import OpenAI
from config import (
    TEST_QUESTIONS_PATH,
    RESULTS_DIR,
    BASELINE_CONFIG,
    VARIANT_CONFIG,
    OPENAI_API_KEY,
)

# Model used exclusively for LLM-as-Judge (always OpenAI JSON mode)
JUDGE_MODEL = "gpt-4o-mini"

# =============================================================================
# SCORING FUNCTIONS
# 4 metrics từ slide: Faithfulness, Answer Relevance, Context Recall, Completeness
# =============================================================================

def score_faithfulness(
    answer: str,
    chunks_used: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Faithfulness: Câu trả lời có bám đúng chứng cứ đã retrieve không?
    Câu hỏi: Model có tự bịa thêm thông tin ngoài retrieved context không?

    Thang điểm 1-5:
      5: Mọi thông tin trong answer đều có trong retrieved chunks
      4: Gần như hoàn toàn grounded, 1 chi tiết nhỏ chưa chắc chắn
      3: Phần lớn grounded, một số thông tin có thể từ model knowledge
      2: Nhiều thông tin không có trong retrieved chunks
      1: Câu trả lời không grounded, phần lớn là model bịa

    TODO Sprint 4 — Có 2 cách chấm:

    Cách 1 — Chấm thủ công (Manual, đơn giản):
        Đọc answer và chunks_used, chấm điểm theo thang trên.
        Ghi lý do ngắn gọn vào "notes".

    Cách 2 — LLM-as-Judge (Tự động, nâng cao):
        Gửi prompt cho LLM:
            "Given these retrieved chunks: {chunks}
             And this answer: {answer}
             Rate the faithfulness on a scale of 1-5.
             5 = completely grounded in the provided context.
             1 = answer contains information not in the context.
             Output JSON: {'score': <int>, 'reason': '<string>'}"

    Trả về dict với: score (1-5) và notes (lý do)
    """
    # 1. Gom các chunks lại thành một đoạn text duy nhất
    chunks_text = "\n\n".join([
        f"--- Chunk {i+1} ---\n{chunk.get('content', chunk.get('text', str(chunk)))}" 
        for i, chunk in enumerate(chunks_used)
    ])

    # 2. Xây dựng prompt theo đúng mô tả trong Docstring
    system_prompt = "You are an expert evaluator. Your task is to rate the faithfulness of an answer based on retrieved contexts."
    user_prompt = f"""
    Given these retrieved chunks: 
    {chunks_text}
    
    And this answer: 
    {answer}
    
    Rate the faithfulness on a scale of 1-5.
    5 = completely grounded in the provided context.
    1 = answer contains information not in the context.
    Output JSON: {{"score": <int>, "notes": "<string>"}}
    """

    # 3. Gọi LLM để chấm điểm tự động
    try:
        client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://models.inference.ai.azure.com/")
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        # 4. Parse kết quả JSON trả về
        result = json.loads(response.choices[0].message.content)

        return {
            "score": result.get("score"),
            "notes": result.get("notes"),
        }

    except Exception as e:
        # Nếu API lỗi hoặc LLM tạch, fallback về chấm thủ công
        return {
            "score": None,
            "notes": f"Lỗi LLM-as-Judge ({str(e)}). Yêu cầu chấm thủ công."
        }


def score_answer_relevance(
    query: str,
    answer: str,
) -> Dict[str, Any]:
    """
    Answer Relevance: Answer có trả lời đúng câu hỏi người dùng hỏi không?
    Câu hỏi: Model có bị lạc đề hay trả lời đúng vấn đề cốt lõi không?

    Thang điểm 1-5:
      5: Answer trả lời trực tiếp và đầy đủ câu hỏi
      4: Trả lời đúng nhưng thiếu vài chi tiết phụ
      3: Trả lời có liên quan nhưng chưa đúng trọng tâm
      2: Trả lời lạc đề một phần
      1: Không trả lời câu hỏi

    TODO Sprint 4: Implement tương tự score_faithfulness
    """
    # 1. Xây dựng prompt đánh giá dựa trên tiêu chí của docstring
    system_prompt = "You are an expert evaluator. Your task is to rate the relevance of an AI-generated answer to a user's query."
    user_prompt = f"""
    Given the user query: 
    {query}
    
    And the AI's answer: 
    {answer}
    
    Rate the answer relevance on a scale of 1-5 based on these criteria:
    5: Trả lời trực tiếp và đầy đủ câu hỏi.
    4: Trả lời đúng nhưng thiếu vài chi tiết phụ.
    3: Trả lời có liên quan nhưng chưa đúng trọng tâm.
    2: Trả lời lạc đề một phần.
    1: Hoàn toàn không trả lời câu hỏi.
    
    Output strictly ONE JSON object in this format: {{"score": <int>, "notes": "<string explaining the reason>"}}
    """

    # 2. Gọi LLM để chấm điểm tự động
    try:
        client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://models.inference.ai.azure.com/")
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        # 3. Parse kết quả JSON trả về
        result = json.loads(response.choices[0].message.content)

        return {
            "score": result.get("score"),
            "notes": result.get("notes"),
        }
    except Exception as e:
        return {
            "score": None,
            "notes": f"Lỗi LLM-as-Judge ({str(e)}). Yêu cầu chấm thủ công."
        }


def score_context_recall(
    chunks_used: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Dict[str, Any]:
    """
    Context Recall: Retriever có mang về đủ evidence cần thiết không?
    Câu hỏi: Expected source có nằm trong retrieved chunks không?

    Đây là metric đo retrieval quality, không phải generation quality.

    Cách tính đơn giản:
        recall = (số expected source được retrieve) / (tổng số expected sources)

    Ví dụ:
        expected_sources = ["policy/refund-v4.pdf", "sla-p1-2026.pdf"]
        retrieved_sources = ["policy/refund-v4.pdf", "helpdesk-faq.md"]
        recall = 1/2 = 0.5
        
    TODO Sprint 4:
    1. Lấy danh sách source từ chunks_used
    2. Kiểm tra xem expected_sources có trong retrieved sources không
    3. Tính recall score
    """
    if not expected_sources:
        # Câu hỏi không có expected source (ví dụ: "Không đủ dữ liệu" cases)
        return {"score": None, "recall": None, "notes": "No expected sources"}

    # 1. Lấy danh sách source từ chunks_used
    retrieved_sources = {
        c.get("metadata", {}).get("source", "")
        for c in chunks_used if c.get("metadata", {}).get("source")
    }

    # 2. Kiểm tra matching theo partial path (vì source paths có thể khác format)
    found = 0
    missing = []
    
    for expected in expected_sources:
        # Tách lấy tên file gốc (Bỏ đường dẫn thư mục và đuôi file)
        # VD: "docs/policy/refund-v4.pdf" -> "refund-v4"
        expected_basename = os.path.splitext(os.path.basename(expected))[0].lower()
        
        matched = False
        for retrieved in retrieved_sources:
            retrieved_basename = os.path.splitext(os.path.basename(retrieved))[0].lower()

            # Normalize hyphens → underscores before comparing (sources use both conventions)
            expected_norm = expected_basename.replace("-", "_")
            retrieved_norm = retrieved_basename.replace("-", "_")

            if expected_norm in retrieved_norm or retrieved_norm in expected_norm:
                matched = True
                break
                
        if matched:
            found += 1
        else:
            missing.append(expected)

    # 3. Tính recall score
    recall = found / len(expected_sources)
    
    # Chuyển đổi sang thang điểm 1-5
    score = 1 if recall == 0 else round(recall * 5)
    score = max(1, min(5, score)) # Chặn trên/dưới để đảm bảo điểm từ 1 đến 5

    return {
        "score": score,
        "recall": round(recall, 4),
        "found": found,
        "missing": missing,
        "notes": f"Retrieved: {found}/{len(expected_sources)} expected sources" +
                 (f". Missing: {missing}" if missing else ""),
    }


def score_completeness(
    query: str,
    answer: str,
    expected_answer: str,
) -> Dict[str, Any]:
    """
    Completeness: Answer có thiếu điều kiện ngoại lệ hoặc bước quan trọng không?
    Câu hỏi: Answer có bao phủ đủ thông tin so với expected_answer không?

    Thang điểm 1-5:
      5: Answer bao gồm đủ tất cả điểm quan trọng trong expected_answer
      4: Thiếu 1 chi tiết nhỏ
      3: Thiếu một số thông tin quan trọng
      2: Thiếu nhiều thông tin quan trọng
      1: Thiếu phần lớn nội dung cốt lõi

    TODO Sprint 4:
    Option 1 — Chấm thủ công: So sánh answer vs expected_answer và chấm.
    Option 2 — LLM-as-Judge:
        "Compare the model answer with the expected answer.
         Rate completeness 1-5. Are all key points covered?
         Output: {'score': int, 'missing_points': [str]}"
    """
    # 1. Xây dựng prompt để LLM đóng vai trò giám khảo đối chiếu 2 câu trả lời
    system_prompt = "You are an expert evaluator. Your task is to evaluate the completeness of an AI-generated answer against an expected ground-truth answer."
    user_prompt = f"""
    Given the user query:
    {query}
    
    The expected ideal answer is:
    {expected_answer}
    
    The AI-generated answer to evaluate is:
    {answer}
    
    Compare the model answer with the expected answer. Rate completeness on a scale of 1-5.
    5: Answer includes all key points from the expected answer.
    4: Missing 1 minor detail.
    3: Missing some important information.
    2: Missing many important details.
    1: Missing most of the core content.
    
    Output strictly ONE JSON object in this format: 
    {{
        "score": <int>, 
        "missing_points": ["<point 1>", "<point 2>"], 
        "notes": "<string explaining the reason>"
    }}
    """

    # 2. Gọi LLM để chấm điểm tự động
    try:
        client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://models.inference.ai.azure.com/")
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        # 3. Parse kết quả JSON trả về
        result = json.loads(response.choices[0].message.content)

        return {
            "score": result.get("score"),
            "missing_points": result.get("missing_points", []),
            "notes": result.get("notes"),
        }

    except Exception as e:
        return {
            "score": None,
            "missing_points": [],
            "notes": f"Lỗi LLM-as-Judge ({str(e)}). Yêu cầu chấm thủ công."
        }


# =============================================================================
# SCORECARD RUNNER
# =============================================================================

def run_scorecard(
    config: Dict[str, Any],
    test_questions: Optional[List[Dict]] = None,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """
    Chạy toàn bộ test questions qua pipeline và chấm điểm.

    Args:
        config: Pipeline config (retrieval_mode, top_k, use_rerank, ...)
        test_questions: List câu hỏi (load từ JSON nếu None)
        verbose: In kết quả từng câu

    Returns:
        List scorecard results, mỗi item là một row

    TODO Sprint 4:
    1. Load test_questions từ data/test_questions.json
    2. Với mỗi câu hỏi:
       a. Gọi rag_answer() với config tương ứng
       b. Chấm 4 metrics
       c. Lưu kết quả
    3. Tính average scores
    4. In bảng kết quả
    """
    if test_questions is None:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)

    results = []
    label = config.get("label", "unnamed")

    print(f"\n{'='*70}")
    print(f"Chạy scorecard: {label}")
    print(f"Config: {config}")
    print('='*70)

    for q in test_questions:
        question_id = q["id"]
        query = q["question"]
        expected_answer = q.get("expected_answer", "")
        expected_sources = q.get("expected_sources", [])
        category = q.get("category", "")

        if verbose:
            print(f"\n[{question_id}] {query}")

        # --- Gọi pipeline ---
        try:
            result = rag_answer(
                query=query,
                retrieval_mode=config.get("retrieval_mode", "dense"),
                top_k_search=config.get("top_k_search", 10),
                top_k_select=config.get("top_k_select", 3),
                use_rerank=config.get("use_rerank", False),
                verbose=False,
            )
            answer = result["answer"]
            chunks_used = result["chunks_used"]

        except NotImplementedError:
            answer = "PIPELINE_NOT_IMPLEMENTED"
            chunks_used = []
        except Exception as e:
            answer = f"ERROR: {e}"
            chunks_used = []

        # --- Chấm điểm ---
        faith = score_faithfulness(answer, chunks_used)
        relevance = score_answer_relevance(query, answer)
        recall = score_context_recall(chunks_used, expected_sources)
        complete = score_completeness(query, answer, expected_answer)

        row = {
            "id": question_id,
            "category": category,
            "query": query,
            "answer": answer,
            "expected_answer": expected_answer,
            "faithfulness": faith["score"],
            "faithfulness_notes": faith["notes"],
            "relevance": relevance["score"],
            "relevance_notes": relevance["notes"],
            "context_recall": recall["score"],
            "context_recall_notes": recall["notes"],
            "completeness": complete["score"],
            "completeness_notes": complete["notes"],
            "config_label": label,
        }
        results.append(row)

        if verbose:
            print(f"  Answer: {answer[:100]}...")
            print(f"  Faithful: {faith['score']} | Relevant: {relevance['score']} | "
                  f"Recall: {recall['score']} | Complete: {complete['score']}")

    # Tính averages (bỏ qua None)
    for metric in ["faithfulness", "relevance", "context_recall", "completeness"]:
        scores = [r[metric] for r in results if r[metric] is not None]
        avg = sum(scores) / len(scores) if scores else None
        print(f"\nAverage {metric}: {avg:.2f}" if avg else f"\nAverage {metric}: N/A (chưa chấm)")

    if verbose:
        print(f"\n{'='*85}")
        print(f"BẢNG TỔNG HỢP KẾT QUẢ CHI TIẾT - {label.upper()}")
        print(f"{'ID':<5} | {'Category':<15} | {'Faithful':<10} | {'Relevant':<10} | {'Recall':<8} | {'Complete':<8}")
        print("-" * 85)
        for r in results:
            f_score = str(r['faithfulness']) if r['faithfulness'] is not None else 'N/A'
            rel_score = str(r['relevance']) if r['relevance'] is not None else 'N/A'
            rec_score = str(r['context_recall']) if r['context_recall'] is not None else 'N/A'
            comp_score = str(r['completeness']) if r['completeness'] is not None else 'N/A'
            
            # Cắt ngắn category nếu quá dài để bảng không bị vỡ
            cat_display = r['category'][:15] if isinstance(r['category'], str) else str(r['category'])
            
            print(f"{r['id']:<5} | {cat_display:<15} | {f_score:<10} | {rel_score:<10} | {rec_score:<8} | {comp_score:<8}")
        print(f"{'='*85}\n")

    return results


# =============================================================================
# A/B COMPARISON
# =============================================================================

def compare_ab(
    baseline_results: List[Dict],
    variant_results: List[Dict],
    output_csv: Optional[str] = None,
) -> None:
    """
    So sánh baseline vs variant theo từng câu hỏi và tổng thể.

    TODO Sprint 4:
    Điền vào bảng sau để trình bày trong báo cáo:

    | Metric          | Baseline | Variant | Delta |
    |-----------------|----------|---------|-------|
    | Faithfulness    |   ?/5    |   ?/5   |  +/?  |
    | Answer Relevance|   ?/5    |   ?/5   |  +/?  |
    | Context Recall  |   ?/5    |   ?/5   |  +/?  |
    | Completeness    |   ?/5    |   ?/5   |  +/?  |

    Câu hỏi cần trả lời:
    - Variant tốt hơn baseline ở câu nào? Vì sao?
    - Biến nào (chunking / hybrid / rerank) đóng góp nhiều nhất?
    - Có câu nào variant lại kém hơn baseline không? Tại sao?
    """
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]

    print(f"\n{'='*70}")
    print("A/B Comparison: Baseline vs Variant")
    print('='*70)
    print(f"{'Metric':<20} {'Baseline':>10} {'Variant':>10} {'Delta':>8}")
    print("-" * 55)

    for metric in metrics:
        b_scores = [r[metric] for r in baseline_results if r[metric] is not None]
        v_scores = [r[metric] for r in variant_results if r[metric] is not None]

        b_avg = sum(b_scores) / len(b_scores) if b_scores else None
        v_avg = sum(v_scores) / len(v_scores) if v_scores else None
        delta = (v_avg - b_avg) if (b_avg and v_avg) else None

        b_str = f"{b_avg:.2f}" if b_avg else "N/A"
        v_str = f"{v_avg:.2f}" if v_avg else "N/A"
        d_str = f"{delta:+.2f}" if delta else "N/A"

        print(f"{metric:<20} {b_str:>10} {v_str:>10} {d_str:>8}")

    # Per-question comparison
    print(f"\n{'Câu':<6} {'Baseline F/R/Rc/C':<22} {'Variant F/R/Rc/C':<22} {'Better?':<10}")
    print("-" * 65)

    b_by_id = {r["id"]: r for r in baseline_results}
    for v_row in variant_results:
        qid = v_row["id"]
        b_row = b_by_id.get(qid, {})

        b_scores_str = "/".join([
            str(b_row.get(m, "?")) for m in metrics
        ])
        v_scores_str = "/".join([
            str(v_row.get(m, "?")) for m in metrics
        ])

        # So sánh đơn giản
        b_total = sum(b_row.get(m, 0) or 0 for m in metrics)
        v_total = sum(v_row.get(m, 0) or 0 for m in metrics)
        better = "Variant" if v_total > b_total else ("Baseline" if b_total > v_total else "Tie")

        print(f"{qid:<6} {b_scores_str:<22} {v_scores_str:<22} {better:<10}")

    # Export to CSV
    if output_csv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = RESULTS_DIR / output_csv
        combined = baseline_results + variant_results
        if combined:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=combined[0].keys())
                writer.writeheader()
                writer.writerows(combined)
            print(f"\nKết quả đã lưu vào: {csv_path}")


# =============================================================================
# REPORT GENERATOR
# =============================================================================

def generate_scorecard_summary(results: List[Dict], label: str) -> str:
    """
    Tạo báo cáo tóm tắt scorecard dạng markdown.

    TODO Sprint 4: Cập nhật template này theo kết quả thực tế của nhóm.
    """
    metrics = ["faithfulness", "relevance", "context_recall", "completeness"]
    averages = {}
    for metric in metrics:
        scores = [r[metric] for r in results if r[metric] is not None]
        averages[metric] = sum(scores) / len(scores) if scores else None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"""# Scorecard: {label}
Generated: {timestamp}

## Summary

| Metric | Average Score |
|--------|--------------|
"""
    for metric, avg in averages.items():
        avg_str = f"{avg:.2f}/5" if avg else "N/A"
        md += f"| {metric.replace('_', ' ').title()} | {avg_str} |\n"

    md += "\n## Per-Question Results\n\n"
    md += "| ID | Category | Faithful | Relevant | Recall | Complete | Notes |\n"
    md += "|----|----------|----------|----------|--------|----------|-------|\n"

    for r in results:
        md += (f"| {r['id']} | {r['category']} | {r.get('faithfulness', 'N/A')} | "
               f"{r.get('relevance', 'N/A')} | {r.get('context_recall', 'N/A')} | "
               f"{r.get('completeness', 'N/A')} | {r.get('faithfulness_notes', '')[:50]} |\n")

    return md


# =============================================================================
# MAIN — Chạy evaluation
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 4: Evaluation & Scorecard")
    print("=" * 60)

    # Kiểm tra test questions
    print(f"\nLoading test questions từ: {TEST_QUESTIONS_PATH}")
    try:
        with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            test_questions = json.load(f)
        print(f"Tìm thấy {len(test_questions)} câu hỏi")

        # In preview
        for q in test_questions[:3]:
            print(f"  [{q['id']}] {q['question']} ({q['category']})")
        print("  ...")

    except FileNotFoundError:
        print("Không tìm thấy file test_questions.json!")
        test_questions = []

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Chạy Baseline ---
    print("\n--- Chạy Baseline ---")
    print("Lưu ý: Cần hoàn thành Sprint 2 trước khi chạy scorecard!")
    try:
        baseline_results = run_scorecard(
            config=BASELINE_CONFIG,
            test_questions=test_questions,
            verbose=True,
        )

        # Save scorecard
        baseline_md = generate_scorecard_summary(baseline_results, "baseline_dense")
        scorecard_path = RESULTS_DIR / "scorecard_baseline.md"
        scorecard_path.write_text(baseline_md, encoding="utf-8")
        print(f"\nScorecard lưu tại: {scorecard_path}")

    except NotImplementedError:
        print("Pipeline chưa implement. Hoàn thành Sprint 2 trước.")
        baseline_results = []

    # --- Chạy Variant (sau khi Sprint 3 hoàn thành) ---
    # TODO Sprint 4: Uncomment sau khi implement variant trong rag_answer.py
    print("\n--- Chạy Variant ---")
    variant_results = run_scorecard(
        config=VARIANT_CONFIG,
        test_questions=test_questions,
        verbose=True,
    )
    variant_md = generate_scorecard_summary(variant_results, VARIANT_CONFIG["label"])
    (RESULTS_DIR / "scorecard_variant.md").write_text(variant_md, encoding="utf-8")

    # --- A/B Comparison ---
    # TODO Sprint 4: Uncomment sau khi có cả baseline và variant
    if baseline_results and variant_results:
        compare_ab(
            baseline_results,
            variant_results,
            output_csv="ab_comparison.csv"
        )

    # --- Tạo grading_run.json (chạy sau 17:00 khi grading_questions.json được public) ---
    grading_path = Path(__file__).parent / "data" / "grading_questions.json"
    if grading_path.exists():
        print("\n--- Tạo logs/grading_run.json ---")
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)

        with open(grading_path, encoding="utf-8") as f:
            grading_qs = json.load(f)

        grading_log = []
        for q in grading_qs:
            try:
                result = rag_answer(
                    q["question"],
                    retrieval_mode=VARIANT_CONFIG["retrieval_mode"],
                    top_k_search=VARIANT_CONFIG["top_k_search"],
                    top_k_select=VARIANT_CONFIG["top_k_select"],
                    use_rerank=VARIANT_CONFIG["use_rerank"],
                    verbose=False,
                )
                grading_log.append({
                    "id": q["id"],
                    "question": q["question"],
                    "answer": result["answer"],
                    "sources": result["sources"],
                    "chunks_retrieved": len(result["chunks_used"]),
                    "retrieval_mode": result["config"]["retrieval_mode"],
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                grading_log.append({
                    "id": q["id"],
                    "question": q["question"],
                    "answer": f"PIPELINE_ERROR: {e}",
                    "sources": [],
                    "chunks_retrieved": 0,
                    "retrieval_mode": VARIANT_CONFIG["retrieval_mode"],
                    "timestamp": datetime.now().isoformat(),
                })

        log_path = logs_dir / "grading_run.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(grading_log, f, ensure_ascii=False, indent=2)
        print(f"Grading log saved: {log_path} ({len(grading_log)} câu)")
    else:
        print(f"\n[Grading] {grading_path} chưa có — chạy lại eval.py sau 17:00 khi file được public.")
