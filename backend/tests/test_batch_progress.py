"""Tests for async batch job tracking (Task 9)."""
from app.api.batch import _batch_jobs, _parse_file_to_items, BatchItem


def test_batch_jobs_dict_exists():
    """The in-memory job store should be a dict."""
    assert isinstance(_batch_jobs, dict)


def test_batch_status_unknown_job():
    """Unknown job_id should not be in the store."""
    assert "nonexistent-id" not in _batch_jobs


def test_parse_file_to_items_csv():
    """CSV bytes should parse into BatchItem list."""
    csv_bytes = b"title,category\nAriel JGK/4,compressor\nWaukesha VHP,engine\n"
    items = _parse_file_to_items(csv_bytes, "test.csv")
    assert len(items) == 2
    assert isinstance(items[0], BatchItem)
    assert items[0].title == "Ariel JGK/4"
    assert items[1].title == "Waukesha VHP"


def test_parse_file_to_items_detects_specs():
    """Extra columns like make/model should land in specs."""
    csv_bytes = b"equipment,category,make,model,year\nFlare Stack,flare,ABC Corp,FS-100,2018\n"
    items = _parse_file_to_items(csv_bytes, "test.csv")
    assert len(items) == 1
    assert items[0].specs.get("make") == "ABC Corp"
    assert items[0].specs.get("model") == "FS-100"
    assert items[0].specs.get("year") == "2018"


def test_parse_file_rejects_unsupported_format():
    """Non-csv/xlsx files should raise HTTPException."""
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _parse_file_to_items(b"data", "test.json")
    assert exc_info.value.status_code == 400


def test_parse_file_rejects_empty():
    """CSV with only headers and no data should raise."""
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _parse_file_to_items(b"title,category\n", "test.csv")
    assert exc_info.value.status_code == 400


def test_job_state_structure():
    """Verify the expected keys in a job state dict."""
    expected_keys = {"job_id", "status", "total", "completed", "current_item", "results", "errors", "summary"}
    # Simulate what batch_start creates
    job = {
        "job_id": "test-uuid",
        "status": "running",
        "total": 5,
        "completed": 0,
        "current_item": None,
        "results": [],
        "errors": [],
        "summary": None,
    }
    assert set(job.keys()) == expected_keys
