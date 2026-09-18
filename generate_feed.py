#!/usr/bin/env python3
"""
Regenerate feed.xml from episodes_manifest.json.
Run this from the repo root after adding a new episode's mp3 + manifest entry.

Usage: python3 generate_feed.py <base_url>
  base_url example: https://USERNAME.github.io/REPO/SLUG
"""
import json
import sys
import email.utils

CHANNEL_TITLE = "Shane's Daily Briefing (Private)"
CHANNEL_DESC = "A private daily news briefing: AI/Anthropic, world news, Ireland, Central Oregon, and sports (Man Utd, Seahawks). Not intended for public distribution."
CHANNEL_LANG = "en-us"
CHANNEL_AUTHOR = "sgalligan"

ITEM_TEMPLATE = """    <item>
      <title>{title}</title>
      <description>{description}</description>
      <pubDate>{pubDate}</pubDate>
      <enclosure url="{audio_url}" length="{size_bytes}" type="audio/mpeg" />
      <guid isPermaLink="false">{guid}</guid>
      <itunes:duration>{duration}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>"""

FEED_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{channel_title}</title>
    <link>{base_url}</link>
    <language>{lang}</language>
    <description>{description}</description>
    <itunes:author>{author}</itunes:author>
    <itunes:explicit>false</itunes:explicit>
    <itunes:category text="News" />
    <atom:link href="{feed_url}" rel="self" type="application/rss+xml" />
{items}
  </channel>
</rss>
"""


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 generate_feed.py <base_url>", file=sys.stderr)
        sys.exit(1)
    base_url = sys.argv[1].rstrip("/")
    feed_url = f"{base_url}/feed.xml"

    with open("episodes_manifest.json") as f:
        episodes = json.load(f)

    # Newest first
    episodes_sorted = sorted(episodes, key=lambda e: e["date"], reverse=True)

    items_xml = []
    for ep in episodes_sorted:
        audio_url = f"{base_url}/episodes/{ep['filename']}"
        items_xml.append(ITEM_TEMPLATE.format(
            title=ep["title"],
            description=ep["description"],
            pubDate=ep["pubDate"],
            audio_url=audio_url,
            size_bytes=ep["size_bytes"],
            guid=audio_url,
            duration=ep["duration"],
        ))

    feed = FEED_TEMPLATE.format(
        channel_title=CHANNEL_TITLE,
        base_url=base_url,
        lang=CHANNEL_LANG,
        description=CHANNEL_DESC,
        author=CHANNEL_AUTHOR,
        feed_url=feed_url,
        items="\n".join(items_xml),
    )

    with open("feed.xml", "w") as f:
        f.write(feed)
    print(f"Wrote feed.xml with {len(episodes_sorted)} episode(s), base_url={base_url}")


if __name__ == "__main__":
    main()
