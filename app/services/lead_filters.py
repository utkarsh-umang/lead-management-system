"""The shared lead filter predicates.

They live here, not in a controller, because GET /leads and the export
selection must agree exactly — "what you see filtered is what exports".
Two copies of these expressions would drift the first time a field is
added (and did: the export path kept treating "has an email" as one state
for a while after the leads table had split it into list-supplied vs
finder-earned).
"""

from __future__ import annotations

from sqlalchemy import func, or_

from app.models.master_lead import MasterLead


def search_condition(pattern: str):  # noqa: ANN201 — SQLAlchemy expression
    """`pattern` is an already-wrapped ILIKE pattern (%foo%)."""
    # Person names are stored split, so "Catherine Santonacita" matches
    # neither column alone — the concatenation is what makes a full-name
    # search (the thing people actually type) work.
    full_name = func.concat(
        func.coalesce(MasterLead.first_name, ""),
        " ",
        func.coalesce(MasterLead.last_name, ""),
    )
    return or_(
        MasterLead.youtube_channel_name.ilike(pattern),
        MasterLead.email.ilike(pattern),
        MasterLead.first_name.ilike(pattern),
        MasterLead.last_name.ilike(pattern),
        full_name.ilike(pattern),
        MasterLead.company_name.ilike(pattern),
    )


def email_from_finder_condition(from_finder: bool):  # noqa: ANN201 — SQLAlchemy expression
    """True = the enricher earned this email (it always stamps
    email_source='email_finder'); False = it arrived with the uploaded CSV
    (any other value, including NULL)."""
    is_finder = func.coalesce(MasterLead.email_source, "") == "email_finder"
    return is_finder if from_finder else ~is_finder
