"""Mapping spec for youtube-tool.csv (our own internal YouTube Data API v3
tool). Headers: Channel Name, Channel URL, Channel ID, Email, Email Status,
Subscribers, Uploads Last 30d, Avg Views, Score, Country, Last Upload,
Discovered At, Search Term ID.

`Email Status` (none/captcha/found) and `Score` (this tool's own weighted
formula) are deliberately not mapped — kept in raw_rows only, not promoted
to canonical. See Master Schema.md for why.
"""

SOURCE_LABEL = "youtube-tool"

MAPPING_SPEC = {
    "source_label": SOURCE_LABEL,
    "fields": [
        {"canonical": "youtube_channel_name", "source": "Channel Name", "op": "text"},
        {"canonical": "youtube_channel_id", "source": "Channel ID", "op": "text"},
        {"canonical": "social_youtube", "source": "Channel URL", "op": "url_or_null"},
        {"canonical": "email", "source": "Email", "op": "email_or_null"},
        {"canonical": "youtube_subscriber_count", "source": "Subscribers", "op": "to_int"},
        {"canonical": "youtube_uploads_last_30d", "source": "Uploads Last 30d", "op": "to_int"},
        {"canonical": "youtube_avg_views", "source": "Avg Views", "op": "to_int"},
        {"canonical": "country", "source": "Country", "op": "text"},
        {
            "canonical": "youtube_last_upload_date",
            "source": "Last Upload",
            "op": "date_parse",
            "op_args": {"fmt": "%Y-%m-%d"},
        },
        {
            "canonical": "source_discovered_at",
            "source": "Discovered At",
            "op": "datetime_parse",
            "op_args": {"fmt": "%Y-%m-%d %H:%M UTC"},
        },
    ],
}
