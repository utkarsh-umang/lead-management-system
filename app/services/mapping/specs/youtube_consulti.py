"""Mapping spec for youtube-consulti.csv. Headers: title, channel_handle,
email, subscriber_count, video_count, niche, category, country, website_url,
twitter_url, instagram_url, tiktok_url, facebook_url, linkedin_url,
email_source, email_confidence, website_source.

Two real data-quality issues baked into these ops (see Master Schema.md):
`email` contains literal "x"/"X" not-found sentinels (and one stray name) —
handled by email_or_null. `website_url` is frequently a YouTube/Google CDN
link, not the creator's actual site — handled by website_or_null's reject
list. `website_source` is not mapped — no canonical field for "how the
website was found" yet; revisit if a future source needs it too.
"""

SOURCE_LABEL = "youtube-consulti"

MAPPING_SPEC = {
    "source_label": SOURCE_LABEL,
    "fields": [
        {"canonical": "youtube_channel_name", "source": "title", "op": "text"},
        {"canonical": "youtube_handle", "source": "channel_handle", "op": "text"},
        {"canonical": "social_youtube", "source": "channel_handle", "op": "youtube_url_from_handle"},
        {"canonical": "email", "source": "email", "op": "email_or_null"},
        {"canonical": "email_source", "source": "email_source", "op": "text"},
        {"canonical": "email_confidence", "source": "email_confidence", "op": "to_float"},
        {"canonical": "youtube_subscriber_count", "source": "subscriber_count", "op": "to_int"},
        {"canonical": "youtube_video_count", "source": "video_count", "op": "to_int"},
        {"canonical": "niche", "source": "niche", "op": "text"},
        {"canonical": "category", "source": "category", "op": "text"},
        {"canonical": "country", "source": "country", "op": "text"},
        {"canonical": "website", "source": "website_url", "op": "website_or_null"},
        {"canonical": "social_twitter", "source": "twitter_url", "op": "url_or_null"},
        {"canonical": "social_instagram", "source": "instagram_url", "op": "url_or_null"},
        {"canonical": "social_tiktok", "source": "tiktok_url", "op": "url_or_null"},
        {"canonical": "social_facebook", "source": "facebook_url", "op": "url_or_null"},
        {"canonical": "social_linkedin", "source": "linkedin_url", "op": "url_or_null"},
    ],
}
