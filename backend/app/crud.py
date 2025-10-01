from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid

from . import models


# Student CRUD operations
def get_student(db: Session, student_id: str) -> Optional[models.Student]:
    return db.query(models.Student).filter(models.Student.id == student_id).first()


def create_student(db: Session, student_id: str, name: str, email: str) -> models.Student:
    db_student = models.Student(id=student_id, name=name, email=email)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def get_or_create_student(db: Session, student_id: str, name: str = None, email: str = None) -> models.Student:
    student = get_student(db, student_id)
    if student:
        return student
    
    # Create new student with defaults if not provided
    if not name:
        name = f"Student {student_id}"
    if not email:
        email = f"{student_id}@student.local"
    
    return create_student(db, student_id, name, email)


# Subject CRUD operations
def get_subject_by_name(db: Session, name: str) -> Optional[models.Subject]:
    return db.query(models.Subject).filter(models.Subject.name == name).first()


def create_subject(db: Session, name: str, description: str = None) -> models.Subject:
    db_subject = models.Subject(name=name, description=description)
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject


def get_or_create_subject(db: Session, name: str, description: str = None) -> models.Subject:
    subject = get_subject_by_name(db, name)
    if subject:
        return subject
    return create_subject(db, name, description)


# Question Paper CRUD operations
def create_question_paper(
    db: Session, 
    subject_id: int, 
    filename: str, 
    file_path: str,
    total_marks: int = 0
) -> models.QuestionPaper:
    db_paper = models.QuestionPaper(
        subject_id=subject_id,
        filename=filename,
        file_path=file_path,
        total_marks=total_marks
    )
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper


def get_latest_question_paper(db: Session, subject_id: int) -> Optional[models.QuestionPaper]:
    return db.query(models.QuestionPaper)\
        .filter(models.QuestionPaper.subject_id == subject_id)\
        .order_by(models.QuestionPaper.created_at.desc())\
        .first()
def create_submission(
    db: Session,
    student_id: str,
    subject_id: int,
    filename: str,
    file_path: str,
    question_paper_id: Optional[int] = None
) -> models.Submission:
    submission_id = str(uuid.uuid4())
    
    db_submission = models.Submission(
        id=submission_id,
        student_id=student_id,
        subject_id=subject_id,
        question_paper_id=question_paper_id,
        filename=filename,
        file_path=file_path,
        status="queued"
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


def get_submission(db: Session, submission_id: str) -> Optional[models.Submission]:
    return db.query(models.Submission).filter(models.Submission.id == submission_id).first()


def get_submissions_by_student(
    db: Session, 
    student_id: str, 
    subject: Optional[str] = None
) -> List[models.Submission]:
    query = db.query(models.Submission).filter(models.Submission.student_id == student_id)
    
    if subject:
        query = query.join(models.Subject).filter(models.Subject.name == subject)
    
    return query.order_by(models.Submission.created_at.desc()).all()


def get_submissions_by_subject(
    db: Session, 
    subject: Optional[str] = None
) -> List[models.Submission]:
    query = db.query(models.Submission)
    
    if subject:
        query = query.join(models.Subject).filter(models.Subject.name == subject)
    
    return query.order_by(models.Submission.created_at.desc()).all()


def update_submission_status(
    db: Session, 
    submission_id: str, 
    status: str, 
    processed_at: Optional[datetime] = None
) -> Optional[models.Submission]:
    submission = get_submission(db, submission_id)
    if submission:
        submission.status = status
        if processed_at:
            submission.processed_at = processed_at
        db.commit()
        db.refresh(submission)
    return submission


def publish_submission(db: Session, submission_id: str) -> Optional[models.Submission]:
    submission = get_submission(db, submission_id)
    if submission:
        submission.is_published = True
        submission.published_at = datetime.utcnow()
        db.commit()
        db.refresh(submission)
    return submission


# Answer CRUD operations
def create_answer(
    db: Session,
    submission_id: str,
    question_id: int,
    extracted_text: str = None,
    auto_score: float = 0.0,
    confidence_score: float = None
) -> models.Answer:
    db_answer = models.Answer(
        submission_id=submission_id,
        question_id=question_id,
        extracted_text=extracted_text,
        auto_score=auto_score,
        final_score=auto_score,  # Initially same as auto_score
        confidence_score=confidence_score,
        needs_review=confidence_score is not None and confidence_score < 0.8
    )
    db.add(db_answer)
    db.commit()
    db.refresh(db_answer)
    return db_answer


def update_answer_teacher_score(
    db: Session,
    answer_id: int,
    teacher_score: float,
    feedback: str = None
) -> Optional[models.Answer]:
    answer = db.query(models.Answer).filter(models.Answer.id == answer_id).first()
    if answer:
        answer.teacher_score = teacher_score
        answer.final_score = teacher_score  # Teacher score overrides auto score
        if feedback:
            answer.feedback = feedback
        answer.reviewed_at = datetime.utcnow()
        answer.needs_review = False
        db.commit()
        db.refresh(answer)
    return answer


def get_answers_by_submission(db: Session, submission_id: str) -> List[models.Answer]:
    return db.query(models.Answer)\
        .filter(models.Answer.submission_id == submission_id)\
        .order_by(models.Answer.question_id)\
        .all()
def create_processing_job(
    db: Session,
    job_id: str,
    submission_id: str,
    job_type: str
) -> models.ProcessingJob:
    db_job = models.ProcessingJob(
        id=job_id,
        submission_id=submission_id,
        job_type=job_type,
        status="pending"
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def update_processing_job_status(
    db: Session,
    job_id: str,
    status: str,
    progress: Optional[int] = None,
    error_message: Optional[str] = None
) -> Optional[models.ProcessingJob]:
    job = db.query(models.ProcessingJob).filter(models.ProcessingJob.id == job_id).first()
    if job:
        job.status = status
        if progress is not None:
            job.progress = progress
        if error_message:
            job.error_message = error_message
        if status == "running" and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            job.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
    return job