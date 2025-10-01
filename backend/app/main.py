from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import uuid
import os
from datetime import datetime

from .database import get_db
from .models import Student, Subject, QuestionPaper, Question, Submission, Answer, ProcessingJob
from . import crud
from .utils.storage import submission_dir, save_upload_file, question_paper_dir
from .tasks import process_submission

app = FastAPI(title="Autograde API", version="0.1.0")

# Note: Table creation is handled manually or via migrations
# @app.on_event("startup")
# async def startup_event():
#     create_tables()


class UploadAnswerResponse(BaseModel):
    submission_id: str
    status: str


class SubmissionItem(BaseModel):
    submission_id: str
    subject: str
    status: str
    total_score: float
    max_possible_score: float
    is_published: bool
    created_at: Optional[str] = None
    processed_at: Optional[str] = None


class StudentResultsResponse(BaseModel):
    student_id: str
    subject: Optional[str]
    submissions: List[SubmissionItem]


class TeacherListResponse(BaseModel):
    subject: Optional[str]
    submissions: List[SubmissionItem]


class CorrectionRequest(BaseModel):
    score_delta: float


class AnswerItem(BaseModel):
    id: int
    question_id: int
    question_number: Optional[int] = None
    extracted_text: Optional[str] = None
    auto_score: float
    teacher_score: Optional[float] = None
    final_score: float
    feedback: Optional[str] = None
    confidence_score: Optional[float] = None
    needs_review: bool


class SubmissionDetailResponse(BaseModel):
    submission_id: str
    student_id: str
    subject: Optional[str]
    status: str
    total_score: float
    max_possible_score: float
    is_published: bool
    created_at: Optional[str] = None
    processed_at: Optional[str] = None
    answers: List[AnswerItem]


@app.get("/health")
def health():
    return {"status": "ok"}


# Student endpoints
@app.post("/api/v1/student/answer-sheets/upload", response_model=UploadAnswerResponse)
async def upload_answer_sheet(
    file: UploadFile = File(...),
    student_id: str = Form(...),
    subject: str = Form(...),
    db: Session = Depends(get_db),
):
    # Basic validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Ensure student and subject exist
    student = crud.get_or_create_student(db, student_id)
    subj = crud.get_or_create_subject(db, subject)

    # Create a submission record
    sub = crud.create_submission(
        db=db,
        student_id=student.id,
        subject_id=subj.id,
        filename=file.filename,
        file_path="",
        question_paper_id=None,
    )

    # Persist file to storage under submission directory
    dest_dir = submission_dir(sub.id)
    # Normalize extension to .pdf if present, otherwise keep original name
    fname = file.filename
    dest_path = os.path.join(dest_dir, fname)
    saved_path, _ = save_upload_file(file, dest_path)

    # Update submission with the actual file path
    sub.file_path = saved_path
    db.commit()

    # Enqueue background processing
    try:
        process_submission.delay(sub.id)
    except Exception:
        # If the broker is unavailable, keep it queued; worker can be started later
        pass

    return UploadAnswerResponse(submission_id=sub.id, status="queued")


@app.get("/api/v1/student/results/{student_id}", response_model=StudentResultsResponse)
async def get_student_results(student_id: str, subject: Optional[str] = None, db: Session = Depends(get_db)):
    subs = crud.get_submissions_by_student(db, student_id=student_id, subject=subject)
    items: List[SubmissionItem] = []
    for s in subs:
        subj_name = s.subject.name if s.subject else ""
        items.append(
            SubmissionItem(
                submission_id=s.id,
                subject=subj_name,
                status=s.status,
                total_score=s.total_score or 0.0,
                max_possible_score=s.max_possible_score or 0.0,
                is_published=bool(s.is_published),
                created_at=s.created_at.isoformat() if s.created_at else None,
                processed_at=s.processed_at.isoformat() if s.processed_at else None,
            )
        )
    return StudentResultsResponse(student_id=student_id, subject=subject, submissions=items)


# Teacher endpoints
@app.post("/api/v1/teacher/question-papers/upload")
async def upload_question_paper(file: UploadFile = File(...), subject: str = Form(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    subj = crud.get_or_create_subject(db, subject)
    # Create question paper record first to get ID
    paper = crud.create_question_paper(db, subject_id=subj.id, filename=file.filename, file_path="", total_marks=0)

    # Save file under question_papers/{subject}/{paper_id}/{filename}
    dest_dir = question_paper_dir(subject, paper.id)
    dest_path = os.path.join(dest_dir, file.filename)
    saved_path, _ = save_upload_file(file, dest_path)

    # Update DB with path
    paper.file_path = saved_path
    db.commit()

    return {"subject": subject, "question_paper_id": paper.id, "status": "uploaded"}


@app.get("/api/v1/teacher/answer-sheets", response_model=TeacherListResponse)
async def list_answer_sheets(subject: Optional[str] = None, db: Session = Depends(get_db)):
    subs = crud.get_submissions_by_subject(db, subject=subject)
    items: List[SubmissionItem] = []
    for s in subs:
        subj_name = s.subject.name if s.subject else ""
        items.append(
            SubmissionItem(
                submission_id=s.id,
                subject=subj_name,
                status=s.status,
                total_score=s.total_score or 0.0,
                max_possible_score=s.max_possible_score or 0.0,
                is_published=bool(s.is_published),
                created_at=s.created_at.isoformat() if s.created_at else None,
                processed_at=s.processed_at.isoformat() if s.processed_at else None,
            )
        )
    return TeacherListResponse(subject=subject, submissions=items)


@app.patch("/api/v1/teacher/results/{submission_id}")
async def correct_result(submission_id: str, req: CorrectionRequest, db: Session = Depends(get_db)):
    sub = crud.get_submission(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    # Apply delta to total_score
    new_total = (sub.total_score or 0.0) + req.score_delta
    sub.total_score = max(0.0, new_total)
    db.commit()
    db.refresh(sub)
    return {"submission_id": sub.id, "new_total_score": sub.total_score}


@app.post("/api/v1/teacher/results/{submission_id}/publish")
async def publish_result(submission_id: str, db: Session = Depends(get_db)):
    sub = crud.publish_submission(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"submission_id": sub.id, "published": True}


@app.get("/api/v1/student/submissions/{submission_id}", response_model=SubmissionDetailResponse)
async def get_submission_detail_student(submission_id: str, db: Session = Depends(get_db)):
    sub = crud.get_submission(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    answers = db.query(Answer).filter(Answer.submission_id == sub.id).all()
    answer_items: List[AnswerItem] = []
    for a in answers:
        qnum = None
        if a.question_id:
            q = db.get(Question, a.question_id)
            qnum = q.question_number if q else None
        answer_items.append(
            AnswerItem(
                id=a.id,
                question_id=a.question_id or 0,
                question_number=qnum,
                extracted_text=a.extracted_text,
                auto_score=a.auto_score or 0.0,
                teacher_score=a.teacher_score,
                final_score=a.final_score or 0.0,
                feedback=a.feedback,
                confidence_score=a.confidence_score,
                needs_review=bool(a.needs_review),
            )
        )
    return SubmissionDetailResponse(
        submission_id=sub.id,
        student_id=sub.student_id,
        subject=sub.subject.name if sub.subject else None,
        status=sub.status,
        total_score=sub.total_score or 0.0,
        max_possible_score=sub.max_possible_score or 0.0,
        is_published=bool(sub.is_published),
        created_at=sub.created_at.isoformat() if sub.created_at else None,
        processed_at=sub.processed_at.isoformat() if sub.processed_at else None,
        answers=answer_items,
    )


@app.get("/api/v1/teacher/submissions/{submission_id}", response_model=SubmissionDetailResponse)
async def get_submission_detail_teacher(submission_id: str, db: Session = Depends(get_db)):
    # For now same as student; later can include more teacher-only metadata
    return await get_submission_detail_student(submission_id, db)
