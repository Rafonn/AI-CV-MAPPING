# app/models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4
import datetime

class ResumeSummary(BaseModel):
    file_name: str
    summary: str

class QueryMatch(BaseModel):
    file_name: Optional[str] = None
    justification: Optional[str] = None

class ProcessingErrorDetail(BaseModel):
    file_name: str
    error: str

class SummaryResponse(BaseModel):
    request_id: str
    summaries: List[ResumeSummary]
    processing_errors: Optional[List[ProcessingErrorDetail]] = None

class QueryResponse(BaseModel):
    request_id: str
    best_match: Union[QueryMatch, str]
    processing_errors: Optional[List[ProcessingErrorDetail]] = None

class LogEntry(BaseModel):
    request_id: str
    user_id: str
    timestamp: datetime.datetime
    query: Optional[str] = None
    result: Dict[str, Any]
    error: Optional[str] = None