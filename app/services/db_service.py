from pymongo import MongoClient
from app.core.config import settings # Supondo que você tenha um settings.MONGODB_URL
from app.models.schemas import LogEntry
from typing import Optional, Dict, Any
import datetime

client = MongoClient(settings.MONGODB_URL)
db = client[settings.MONGODB_DATABASE_NAME]
logs_collection = db["usage_logs"]

def log_request(request_id: str, user_id: str, query: Optional[str], result: dict, error: Optional[str] = None):
    log_entry = LogEntry(
        request_id=request_id,
        user_id=user_id,
        timestamp=datetime.datetime.utcnow(),
        query=query,
        result=result,
        error=error
    )
    try:
        logs_collection.insert_one(log_entry.model_dump(exclude_none=True)) # Pydantic v2+
    except Exception as e:
        print(f"Erro ao salvar log no MongoDB: {e}")