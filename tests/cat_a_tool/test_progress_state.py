from backend.cat_a_tool.progress_state import progress_data


def test_progress_data_defaults():
    assert progress_data["current"] == 0
    assert progress_data["total"] == 0
    assert progress_data["percent"] == 0
    assert progress_data["running"] is False


def test_progress_data_update():
    progress_data["current"] = 5
    progress_data["total"] = 10
    progress_data["percent"] = 50
    progress_data["running"] = True

    assert progress_data["current"] == 5
    assert progress_data["total"] == 10
    assert progress_data["percent"] == 50
    assert progress_data["running"] is True
