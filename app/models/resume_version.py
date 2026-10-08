from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, Float
from sqlalchemy.orm import relationship
from app.database import Base


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    version = Column(Integer, default=1)
    content = Column(Text, nullable=False)
    ats_score = Column(Float, nullable=True)
    pdf_path = Column(String, nullable=True)
    docx_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="resume_versions")