# tests/unit/test_db_service.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.db_service import log_request
from app.models.schemas import LogEntry
import datetime

@patch('app.services.db_service.logs_collection')
def test_log_request_success(mock_logs_collection):
    request_id = "test-req-123"
    user_id = "fabio-test"
    query = "Engenheiro de Software"
    result_data = {"summary": "Algum resultado"}
    
    log_request(request_id, user_id, query, result_data)
    
    mock_logs_collection.insert_one.assert_called_once()
    args, _ = mock_logs_collection.insert_one.call_args
    log_document_passed = args[0]
    
    assert log_document_passed["request_id"] == request_id
    assert log_document_passed["user_id"] == user_id
    assert log_document_passed["query"] == query
    assert log_document_passed["result"] == result_data
    assert "timestamp" in log_document_passed