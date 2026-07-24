from job_watch.roles import Role, matches_keywords


def _role(title: str, division: str = "") -> Role:
    return Role(id="1", title=title, division=division, location="Somewhere", url="https://example.com")


def test_matches_keywords_is_case_insensitive_substring_match():
    role = _role("Summer Analyst, FICC and Equities Quantitative Strats")
    assert matches_keywords(role, ["quant"])
    assert matches_keywords(role, ["QUANT"])
    assert not matches_keywords(role, ["marketing"])


def test_matches_keywords_checks_division_too():
    role = _role("New Analyst", division="Engineering Division")
    assert matches_keywords(role, ["engineer"])


def test_matches_keywords_empty_list_matches_everything():
    role = _role("Anything")
    assert matches_keywords(role, [])
