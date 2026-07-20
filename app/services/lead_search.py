"""The one definition of what a lead search matches.

Lives here, not in a controller, because GET /leads and the export selection
must agree exactly — "what you see filtered is what exports". Two copies of
this expression would drift the first time a field is added.
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
