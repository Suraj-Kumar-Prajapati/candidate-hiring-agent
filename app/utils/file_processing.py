from fastapi import UploadFile
import PyPDF2
import os
from typing import Tuple
from pathlib import Path
import uuid
import aiofiles
from docx import Document

from app.core.config import settings
from app.core.exceptions import FileProcessingError


async def process_uploaded_resume(file: UploadFile) -> Tuple[str, str]:
    """Process uploaded resume file and extract text"""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx', '.doc')):
            raise FileProcessingError("Only PDF and Word documents are supported")
        
        # Validate file size
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise FileProcessingError(f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit")
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIRECTORY, unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Extract text based on file type
        if file.filename.lower().endswith('.pdf'):
            resume_text = await extract_pdf_text(file_path)
        else:
            resume_text = await extract_docx_text(file_path)
        
        if not resume_text.strip():
            raise FileProcessingError("Could not extract text from the uploaded file")
        
        return resume_text, file_path
        
    except Exception as e:
        if isinstance(e, FileProcessingError):
            raise e
        raise FileProcessingError(f"File processing failed: {str(e)}")


async def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF file"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise FileProcessingError(f"PDF text extraction failed: {str(e)}")


async def extract_docx_text(file_path: str) -> str:
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)
        return '\n'.join(text).strip()
    except Exception as e:
        raise FileProcessingError(f"DOCX text extraction failed: {str(e)}")


def cleanup_old_files(directory: str, days: int = 30):
    """Clean up old files from directory"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for file_path in Path(directory).glob('*'):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_path.unlink()
                    
    except Exception as e:
        print(f"File cleanup error: {str(e)}")


async def validate_file_content(file_path: str) -> bool:
    """Validate that file contains meaningful content"""
    try:
        if file_path.lower().endswith('.pdf'):
            text = await extract_pdf_text(file_path)
        else:
            text = await extract_docx_text(file_path)
        
        # Basic validation: check if text has reasonable length and contains common resume keywords
        if len(text) < 100:
            return False
        
        resume_keywords = [
            'experience', 'education', 'skills', 'work', 'employment', 
            'university', 'college', 'degree', 'certified', 'project'
        ]
        
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in resume_keywords if keyword in text_lower)
        
        return keyword_count >= 2
        
    except Exception:
        return False
