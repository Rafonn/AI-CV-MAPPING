from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
import datetime

class ProcessRequest(BaseModel):
    request_id: str # Ou UUID
    user_id: str
    query: Optional[str] = None

class ResumeSummary(BaseModel):
    file_name: str
    summary: str

class QueryMatch(BaseModel):
    file_name: str
    justification: str

class SummaryResponse(BaseModel):
    request_id: str
    summaries: List[ResumeSummary]

class QueryResponse(BaseModel):
    request_id: str
    best_match: Optional[QueryMatch]

class LogEntry(BaseModel):
    request_id: str
    user_id: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    query: Optional[str] = None
    result: Dict[str, Any]
    error: Optional[str] = None