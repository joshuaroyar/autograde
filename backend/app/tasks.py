from datetime import datetime
from typing import List, Tuple
from app.celery_app import celery_app
from app.database import SessionLocal
from app import crud
from app import models
from app.services.ocr import ocr_pdf, segment_questions


def _auto_grade(text: str, question: models.Question) -> Tuple[float, float, bool]:
    """
    Simple baseline auto-grader.
    - If question.rubric has {"keywords": [..]}: score = (#keywords present / total) * max_marks
    - Else: length-based heuristic on non-whitespace chars.
    Returns: (score, confidence, needs_review)
    """
    max_marks = float(question.max_marks or 0)
    text_lower = (text or "").lower()
    score = 0.0
    confidence = 0.4
    needs_review = True

    if isinstance(question.rubric, dict) and question.rubric.get("keywords"):
        keywords = [str(k).lower() for k in question.rubric.get("keywords", [])]
        if keywords:
            hits = sum(1 for k in keywords if k in text_lower)
            frac = hits / len(keywords)
            score = round(frac * max_marks, 2)
            confidence = 0.6 if frac >= 0.6 else 0.45
            needs_review = frac < 0.8
    else:
        # Length heuristic
        n = len("".join(text.split()))
        if n <= 10:
            score = 0.0
            confidence = 0.3
            needs_review = True
        elif n <= 100:
            score = round(0.5 * max_marks, 2)
            confidence = 0.4
            needs_review = True
        else:
            score = round(0.8 * max_marks, 2)
            confidence = 0.5
            needs_review = False if max_marks <= 2 else True

    return score, confidence, needs_review


@celery_app.task(bind=True, name="app.tasks.process_submission")
def process_submission(self, submission_id: str) -> dict:
    """
    Background task to process a submission:
    - Update submission status to processing
    - Run OCR over the uploaded PDF
    - Map segments to questions (best-effort) and auto-grade
    - Persist answers and update submission totals
    - Update job and submission status

    Returns summary.
    """
    db = SessionLocal()
    job_id = getattr(self.request, "id", None)
    try:
        # Create job entry
        job = models.ProcessingJob(
            id=job_id or "unknown",
            submission_id=submission_id,
            job_type="ocr",
            status="running",
            progress=0,
            started_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()

        # Mark submission as processing
        crud.update_submission_status(db, submission_id, status="processing")

        # Fetch submission and related subject
        submission = crud.get_submission(db, submission_id)
        if not submission:
            job.status = "failed"
            job.error_message = "Submission not found"
            job.completed_at = datetime.utcnow()
            db.commit()
            return {"error": "submission_not_found"}

        # Determine question paper (latest for subject) if not linked
        if not submission.question_paper_id:
            paper = crud.get_latest_question_paper(db, subject_id=submission.subject_id)
            if paper:
                submission.question_paper_id = paper.id
            db.commit()
        else:
            paper = db.get(models.QuestionPaper, submission.question_paper_id)

        # Run OCR
        texts = ocr_pdf(submission.file_path)
        segments = segment_questions(texts) if texts else []

        # Remove any existing answers for idempotency
        db.query(models.Answer).filter(models.Answer.submission_id == submission_id).delete()
        db.commit()

        total_score = 0.0
        max_possible = 0.0
        answers_created = 0

        if paper:
            questions: List[models.Question] = (
                db.query(models.Question)
                .filter(models.Question.question_paper_id == paper.id)
                .order_by(models.Question.question_number.asc())
                .all()
            )
            max_possible = float(sum(q.max_marks or 0 for q in questions))

            # Map segments to questions by order (best-effort)
            for idx, q in enumerate(questions):
                text = segments[idx] if idx < len(segments) else ("\n".join(texts) if texts else "")
                score, conf, needs_review = _auto_grade(text, q)
                ans = models.Answer(
                    submission_id=submission_id,
                    question_id=q.id,
                    extracted_text=text,
                    auto_score=score,
                    final_score=score,
                    confidence_score=conf,
                    needs_review=needs_review,
                )
                db.add(ans)
                total_score += score
                answers_created += 1
            db.commit()
        else:
            # No question paper: create a single answer with all text, zero max marks
            whole_text = "\n".join(texts) if texts else ""
            ans = models.Answer(
                submission_id=submission_id,
                question_id=0,  # orphan marker; no question mapping
                extracted_text=whole_text,
                auto_score=0.0,
                final_score=0.0,
                confidence_score=0.3,
                needs_review=True,
            )
            db.add(ans)
            answers_created = 1
            db.commit()

        # Update submission totals
        submission.total_score = round(total_score, 2)
        submission.max_possible_score = round(max_possible, 2)
        db.commit()

        # Update job and submission completion
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.utcnow()
        db.commit()

        crud.update_submission_status(db, submission_id, status="completed", processed_at=datetime.utcnow())

        return {
            "submission_id": submission_id,
            "pages": len(texts),
            "answers": answers_created,
            "max_possible": submission.max_possible_score,
            "total_score": submission.total_score,
        }

    except Exception as e:
        # Update job and submission to failed/error
        try:
            job = db.get(models.ProcessingJob, job_id) if job_id else None
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.commit()
            crud.update_submission_status(db, submission_id, status="error")
        finally:
            db.close()
        raise
    finally:
        db.close()
