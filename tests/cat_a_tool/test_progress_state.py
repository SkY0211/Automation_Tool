from backend.cat_a_tool.progress_state import progress_data


def test_progress_state_structure():
    assert "current" in progress_data
    assert "total" in progress_data
    assert "percent" in progress_data
    assert "running" in progress_data


def test_progress_state_mutation():
    progress_data["current"] = 5
    progress_data["total"] = 10
    progress_data["percent"] = 50
    progress_data["running"] = True

    assert progress_data["percent"] == 50