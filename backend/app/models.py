from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

Base = declarative_base()


class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    submissions = relationship("Submission", back_populates="student")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    question_papers = relationship("QuestionPaper", back_populates="subject")
    submissions = relationship("Submission", back_populates="subject")


class QuestionPaper(Base):
    __tablename__ = "question_papers"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    total_marks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subject = relationship("Subject", back_populates="question_papers")
    questions = relationship("Question", back_populates="question_paper")
    submissions = relationship("Submission", back_populates="question_paper")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_paper_id = Column(Integer, ForeignKey("question_papers.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text)
    max_marks = Column(Integer, nullable=False)
    rubric = Column(JSON)  # Grading rubric/criteria
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    question_paper = relationship("QuestionPaper", back_populates="questions")
    answers = relationship("Answer", back_populates="question")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, index=True)  # UUID
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    question_paper_id = Column(Integer, ForeignKey("question_papers.id"), nullable=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default="queued")  # queued, processing, completed, error
    total_score = Column(Float, default=0.0)
    max_possible_score = Column(Float, default=0.0)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="submissions")
    subject = relationship("Subject", back_populates="submissions")
    question_paper = relationship("QuestionPaper", back_populates="submissions")
    answers = relationship("Answer", back_populates="submission")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    extracted_text = Column(Text)  # OCR extracted text
    auto_score = Column(Float, default=0.0)  # AI-generated score
    teacher_score = Column(Float, nullable=True)  # Teacher override
    final_score = Column(Float, default=0.0)  # Final score (teacher_score if exists, else auto_score)
    feedback = Column(Text)  # Teacher feedback
    confidence_score = Column(Float)  # AI confidence in scoring
    needs_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    submission = relationship("Submission", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String, primary_key=True, index=True)  # Celery task ID
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    job_type = Column(String, nullable=False)  # ocr, grading, etc.
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())