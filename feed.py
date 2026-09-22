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

feed_urls = []

if "source_feeds" in config and isinstance(config["source_feeds"], list):
    feed_urls = [
        u.strip()
        for u in config["source_feeds"]
        if isinstance(u, str) and u.strip()
    ]
elif "source_feed" in config and isinstance(config["source_feed"], str):
    if config["source_feed"].strip():
        feed_urls = [config["source_feed"].strip()]

if not feed_urls:
    print("❌ No feed URLs found in feed.yaml")
    sys.exit(1)

output_file = config.get("output_file", "docs/news-feed.xml")
max_items = int(config.get("max_items", 40))

# -----------------------------
# Helpers
# -----------------------------
def local_name(tag):
    if not isinstance(tag, str):
        return ""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def direct_child_text(element, accepted_names):
    for child in list(element):
        if local_name(child.tag).lower() in accepted_names:
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return ""


def get_link(element):
    fallback = ""

    for child in list(element):
        if local_name(child.tag).lower() != "link":
            continue

        href = (child.attrib.get("href") or "").strip()
        rel = (child.attrib.get("rel") or "").strip().lower()

        if href and rel in ("", "alternate"):
            return href

        if href and not fallback:
            fallback = href

        text_value = "".join(child.itertext()).strip()
        if text_value and not fallback:
            fallback = text_value

    # Some feeds use <guid> as the article URL.
    if not fallback:
        fallback = direct_child_text(element, {"guid"})

    return fallback


def parse_pubdate(value):
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    value = value.strip()

    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError, OverflowError):
        pass

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def rss_date(value):
    if not value:
        return ""

    parsed = parse_pubdate(value)

    if parsed == datetime.min.replace(tzinfo=timezone.utc):
        return value

    return parsed.strftime("%a, %d %b %Y %H:%M:%S %z")


# -----------------------------
# Fetch feeds
# -----------------------------
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, "
        "application/xml, text/xml, */*"
    ),
}

all_items = []
failed = 0

for url in feed_urls:
    print("")
    print("=" * 70)
    print(f"🔎 SOURCE FEED: {url}")

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        print(f"❌ Request failed: {exc}")
        failed += 1
        continue

    print(f"HTTP status: {response.status_code}")
    print(f"Final URL: {response.url}")
    print(f"Content-Type: {response.headers.get('Content-Type', '(missing)')}")
    print(f"Response bytes: {len(response.content)}")

    if response.status_code != 200:
        print("❌ Feed did not return HTTP 200.")
        print("Response preview:")
        print(response.text[:1000])
        failed += 1
        continue

    if not response.content.strip():
        print("❌ Feed returned an empty response.")
        failed += 1
        continue

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        print(f"❌ Response is not valid XML: {exc}")
        print("Response preview:")
        print(response.text[:1500])
        failed += 1
        continue

    print(f"XML root tag: {root.tag}")

    # Collect article-like nodes regardless of namespace.
    candidates = []

    for element in root.iter():
        name = local_name(element.tag).lower()
        if name in ("item", "entry"):
            candidates.append(element)

    print(f"Article nodes found: {len(candidates)}")

    # If none were found, show the first several XML tag names.
    if not candidates:
        tag_names = []
        for element in root.iter():
            name = local_name(element.tag)
            if name and name not in tag_names:
                tag_names.append(name)
            if len(tag_names) >= 30:
                break

        print("⚠️ No <item> or <entry> elements found.")
        print(f"Tags seen in feed: {tag_names}")
        print("XML preview:")
        print(response.text[:2000])
        continue

    feed_count = 0

    for element in candidates:
        title = direct_child_text(element, {"title"})
        link = get_link(element)
        pubdate = direct_child_text(
            element,
            {
                "pubdate",
                "published",
                "updated",
                "date",
                "issued",
                "created",
            },
        )

        if not title and not link:
            continue

        all_items.append(
            {
                "title": title,
                "link": link,
                "pubDate": pubdate,
            }
        )

        feed_count += 1

        # Print a few examples so the Actions log shows what is being read.
        if feed_count <= 3:
            print(
                f"  ARTICLE {feed_count}: "
                f"title={title!r}, link={link!r}, pubDate={pubdate!r}"
            )

    print(f"✅ Usable articles collected from this feed: {feed_count}")

# -----------------------------
# Stop if nothing was collected
# -----------------------------
if not all_items:
    print("")
    print("❌ ZERO ARTICLES WERE COLLECTED.")
    print("Look above for the SOURCE FEED diagnostics.")
    sys.exit(1)

# -----------------------------
# Dedupe
# -----------------------------
deduped = {}

for item in all_items:
    title = (item.get("title") or "").strip()
    link = (item.get("link") or "").strip()
    pubdate = (item.get("pubDate") or "").strip()

    key = link or title

    if not key:
        continue

    if key not in deduped:
        deduped[key] = {
            "title": title,
            "link": link,
            "pubDate": pubdate,
        }

items_list = list(deduped.values())

# -----------------------------
# Sort newest first
# -----------------------------
items_list.sort(
    key=lambda item: parse_pubdate(item.get("pubDate", "")),
    reverse=True,
)

items_list = items_list[:max_items]

print("")
print(f"📰 Total unique articles being written: {len(items_list)}")

# -----------------------------
# Build RSS
# -----------------------------
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = config.get(
    "title",
    "Investor News Alerts",
)
ET.SubElement(channel, "link").text = config.get("link", "")
ET.SubElement(channel, "description").text = config.get(
    "description",
    "",
)
ET.SubElement(channel, "language").text = config.get(
    "language",
    "en-us",
)

for item in items_list:
    new_item = ET.SubElement(channel, "item")

    ET.SubElement(new_item, "title").text = item["title"]
    ET.SubElement(new_item, "link").text = item["link"]

    if item["link"]:
        ET.SubElement(new_item, "guid").text = item["link"]

    if item["pubDate"]:
        ET.SubElement(new_item, "pubDate").text = rss_date(
            item["pubDate"]
        )

# -----------------------------
# Write XML
# -----------------------------
rough_xml = ET.tostring(rss, encoding="utf-8")

pretty_xml = minidom.parseString(
    rough_xml
).toprettyxml(indent="  ")

output_dir = os.path.dirname(output_file)

if output_dir:
    os.makedirs(output_dir, exist_ok=True)

with open(output_file, "w", encoding="utf-8") as file:
    file.write(pretty_xml)

print(f"✅ Generated: {output_file}")
print(f"✅ Feed contains {len(items_list)} article(s).")

if failed:
    print(f"⚠️ {failed} source feed(s) failed.")
