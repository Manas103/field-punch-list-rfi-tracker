from app.routing import route_discipline


def test_mep_keywords_route_to_mep():
    assert route_discipline("duct hanger missing insulation clamp") == "mep"
    assert route_discipline("Sprinkler head clearance issue") == "mep"
    assert route_discipline("panelboard door won't close") == "mep"


def test_structural_keywords_route_to_structural():
    assert route_discipline("beam camber exceeds tolerance") == "structural"
    assert route_discipline("footing rebar cover under minimum") == "structural"


def test_unmatched_description_defaults_to_architectural():
    assert route_discipline("wall paint touch-up needed") == "architectural"
    assert route_discipline("door hardware missing closer arm") == "architectural"


def test_mep_keyword_takes_priority_when_multiple_disciplines_are_mentioned():
    # A duct routed past a beam is an MEP coordination item first.
    assert route_discipline("duct conflicts with beam at this gridline") == "mep"
