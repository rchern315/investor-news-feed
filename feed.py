import yaml
import requests
from xml.dom import minidom
import xml.etree.ElementTree as ET
import sys
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# -----------------------------
# Load configuration
# -----------------------------
with open("feed.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Support BOTH styles:
# - source_feed: "https://..."
# - source_feeds: ["https://...", "https://..."]
feed_urls = []

if "source_feeds" in config and isinstance(config["source_feeds"], list):
    feed_urls = [u for u in config["source_feeds"] if isinstance(u, str) and u.strip()]
elif "source_feed" in config and isinstance(config["source_feed"], str):
    feed_urls = [config["source_feed"].strip()]

if not feed_urls:
    print("❌ No feed URLs found. Add 'source_feed' or 'source_feeds' to feed.yaml")
    sys.exit(0)

# Where we write the final RSS for GitHub Pages
output_file = config.get("output_file", "docs/news-feed.xml")

# -----------------------------
# Helpers for RSS + Atom feeds
# -----------------------------
def local_name(tag):
    """Return an XML tag name without its namespace."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def child_text(element, names):
    """
    Return the text of the first direct child whose local tag name
    matches one of the supplied names.
    """
    for child in list(element):
        if local_name(child.tag) in names:
            return (child.text or "").strip()
    return ""


def entry_link(element):
    """
    Read a link from either:
    - RSS:  <link>https://example.com/article</link>
    - Atom: <link href="https://example.com/article" />
    """
    fallback = ""

    for child in list(element):
        if local_name(child.tag) != "link":
            continue

        href = (child.attrib.get("href") or "").strip()
        rel = (child.attrib.get("rel") or "").strip().lower()

        # Prefer Atom's normal article URL.
        if href and (not rel or rel == "alternate"):
            return href

        if href and not fallback:
            fallback = href

        text_link = (child.text or "").strip()
        if text_link and not fallback:
            fallback = text_link

    return fallback


def parse_pubdate(pubdate_str: str) -> datetime:
    """
    Parse both RSS/RFC 2822 and Atom/ISO-8601 dates.

    Always return a timezone-aware datetime so sorting cannot fail.
    """
    if not pubdate_str:
        return datetime.min.replace(tzinfo=timezone.utc)

    # RSS/RFC 2822:
    # Sat, 20 Dec 2025 12:08:46 +0000
    try:
        parsed = parsedate_to_datetime(pubdate_str)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError, OverflowError):
        pass

    # Atom/ISO-8601:
    # 2025-12-20T12:08:46Z
    # 2025-12-20T12:08:46+00:00
    try:
        iso_value = pubdate_str.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(iso_value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def to_rss_pubdate(pubdate_str: str) -> str:
    """
    Keep RSS dates as-is when possible.
    Convert Atom ISO dates to an RSS-compatible date string.
    """
    if not pubdate_str:
        return ""

    try:
        parsed = parse_pubdate(pubdate_str)
        if parsed == datetime.min.replace(tzinfo=timezone.utc):
            return pubdate_str
        return parsed.strftime("%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        return pubdate_str


# -----------------------------
# Fetch external RSS / Atom feeds
# -----------------------------
headers = {
    "User-Agent": "Mozilla/5.0 (compatible; GitHubActionsBot/1.0)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

all_items = []
failed = 0

for url in feed_urls:
    print(f"🔎 Fetching: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️ Network/HTTP error for {url}: {e}")
        failed += 1
        continue

    try:
        external_feed = ET.fromstring(response.content)
    except ET.ParseError as e:
        print(f"⚠️ Could not parse XML from {url}: {e}")
        failed += 1
        continue

    feed_items = []

    # Find both RSS <item> and Atom <entry>, regardless of XML namespace.
    for element in external_feed.iter():
        name = local_name(element.tag)

        if name not in ("item", "entry"):
            continue

        title = child_text(element, {"title"})
        link = entry_link(element)
        pubdate = child_text(
            element,
            {"pubDate", "published", "updated", "date", "dc:date"},
        )

        # Ignore completely empty entries.
        if not title and not link:
            continue

        feed_items.append(
            {
                "title": title,
                "link": link,
                "pubDate": pubdate,
            }
        )

    print(f"✅ Found {len(feed_items)} article(s) in this feed.")
    all_items.extend(feed_items)

if not all_items:
    print("⚠️ No articles found in any source feed. No output written.")
    print("ℹ️ Check the feed URLs and the GitHub Actions log for the per-feed article counts.")
    sys.exit(0)

# -----------------------------
# Dedupe + sort items
# -----------------------------
deduped = {}

for item in all_items:
    link = (item.get("link") or "").strip()
    title = (item.get("title") or "").strip()
    pubdate = (item.get("pubDate") or "").strip()

    # Use link as the primary unique key; fall back to title if needed.
    key = link if link else title

    if not key:
        continue

    # Keep the first occurrence.
    if key not in deduped:
        deduped[key] = {
            "title": title,
            "link": link,
            "pubDate": pubdate,
        }

items_list = list(deduped.values())

items_list.sort(
    key=lambda x: parse_pubdate(x.get("pubDate", "")),
    reverse=True,
)

# Limit how many items to publish.
max_items = int(config.get("max_items", 40))
items_list = items_list[:max_items]

print(f"📰 Publishing {len(items_list)} unique article(s).")

# -----------------------------
# Create RSS feed
# -----------------------------
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = config.get("title", "Investor News Alerts")
ET.SubElement(channel, "link").text = config.get("link", "")
ET.SubElement(channel, "description").text = config.get("description", "")
ET.SubElement(channel, "language").text = config.get("language", "en-us")

for item in items_list:
    new_item = ET.SubElement(channel, "item")

    ET.SubElement(new_item, "title").text = item.get("title", "")
    ET.SubElement(new_item, "link").text = item.get("link", "")

    pubdate = item.get("pubDate", "")
    if pubdate:
        ET.SubElement(new_item, "pubDate").text = to_rss_pubdate(pubdate)

# -----------------------------
# Write file (pretty printed)
# -----------------------------
rough_xml = ET.tostring(rss, encoding="utf-8")
pretty_xml = minidom.parseString(rough_xml).toprettyxml(indent="  ")

# Ensure docs/ exists if you're writing there.
os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

with open(output_file, "w", encoding="utf-8") as f:
    f.write(pretty_xml)

print(f"✅ Investor News RSS feed generated successfully: {output_file}")

if failed:
    print(f"ℹ️ Note: {failed} feed(s) failed/skipped due to network, HTTP, or XML parse issues.")
