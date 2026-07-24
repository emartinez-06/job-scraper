from job_watch.state import newly_seen


def test_newly_seen_returns_only_unseen_ids():
    assert newly_seen(previous_ids=["a", "b"], current_ids=["a", "b", "c"]) == ["c"]


def test_newly_seen_empty_when_nothing_new():
    assert newly_seen(previous_ids=["a", "b"], current_ids=["a"]) == []


def test_newly_seen_all_new_when_state_empty():
    assert newly_seen(previous_ids=[], current_ids=["a", "b"]) == ["a", "b"]
