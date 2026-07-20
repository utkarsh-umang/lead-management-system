"""What a lead search matches. The full-name case is the regression this
file exists for: person names are stored split, so "Catherine Santonacita"
matches neither first_name nor last_name alone — searching the name people
actually type returned nothing until the concatenation was added."""

from sqlalchemy.dialects import postgresql

from app.services.lead_filters import email_from_finder_condition, search_condition


def _sql(pattern: str) -> str:
    return str(
        search_condition(pattern).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def test_matches_person_company_and_channel_columns():
    sql = _sql("%acme%")
    for column in [
        "youtube_channel_name",
        "email",
        "first_name",
        "last_name",
        "company_name",
    ]:
        assert f"master_leads.{column}" in sql, column


def test_matches_concatenated_full_name():
    """first_name || ' ' || last_name — without this, searching a person by
    their full name silently returns zero rows."""
    sql = _sql("%catherine santonacita%")
    assert "concat" in sql.lower()
    # The concat must join first and last with a space, or "First Last"
    # still won't match.
    assert sql.lower().count("first_name") >= 2
    assert sql.lower().count("last_name") >= 2


def test_email_from_finder_splits_earned_from_free():
    """The enricher always stamps email_source='email_finder'; NULL (never
    enriched) must land on the "came with the list" side, which is why the
    predicate coalesces before comparing."""
    earned = str(
        email_from_finder_condition(True).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    free = str(
        email_from_finder_condition(False).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "email_finder" in earned and "email_finder" in free
    assert "coalesce" in earned.lower()
    # The two must be complements, or a lead would fall into both or neither.
    assert free != earned
    assert "!=" in free or "NOT" in free.upper()
