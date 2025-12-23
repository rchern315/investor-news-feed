import yaml
import requests
from xml.dom import minidom
import xml.etree.ElementTree as ET
import sys
from datetime import datetime

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
# Fetch external RSS feeds
# -----------------------------
headers = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActionsBot/1.0)"}

all_items = []
failed = 0

for url in feed_urls:
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"⚠️ Network error for {url}: {e}")
        failed += 1
        continue

    if response.status_code != 200:
        print(f"⚠️ Skipping feed (status {response.status_code}): {url}")
        failed += 1
        continue

    try:
        external_rss = ET.fromstring(response.content)
    except ET.ParseError as e:
        print(f"⚠️ Could not parse RSS XML from {url}: {e}")
        failed += 1
        continue

    all_items.extend(external_rss.findall("./channel/item"))

if not all_items:
    print("⚠️ No items fetched (all feeds failed or returned empty). No output written.")
    sys.exit(0)

# -----------------------------
# Dedupe + sort items (best-effort)
# -----------------------------
def parse_pubdate(pubdate_str: str) -> datetime:
    """
    RSS pubDate often looks like:
    'Sat, 20 Dec 2025 12:08:46 +0000'
    We'll best-effort parse it for sorting.
    """
    if not pubdate_str:
        return datetime.min
    try:
        # Common RFC 2822 style date
        return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        return datetime.min

deduped = {}
for item in all_items:
    link = (item.findtext("link") or "").strip()
    title = (item.findtext("title") or "").strip()
    pubdate = (item.findtext("pubDate") or "").strip()

    # Use link as the primary unique key; fall back to title if needed.
    key = link if link else title
    if not key:
        continue

    # Keep the first occurrence
    if key not in deduped:
        deduped[key] = {"title": title, "link": link, "pubDate": pubdate}

items_list = list(deduped.values())
items_list.sort(key=lambda x: parse_pubdate(x.get("pubDate", "")), reverse=True)

# Limit how many items to publish
max_items = int(config.get("max_items", 40))
items_list = items_list[:max_items]

# -----------------------------
# Create RSS feed
# -----------------------------
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = config.get("title", "Investor News Alerts")
ET.SubElement(channel, "link").text = config.get("link", "")
ET.SubElement(channel, "description").text = config.get("description", "")
ET.SubElement(channel, "language").text = config.get("language", "en-us")

for i in items_list:
    new_item = ET.SubElement(channel, "item")
    ET.SubElement(new_item, "title").text = i.get("title", "")
    ET.SubElement(new_item, "link").text = i.get("link", "")
    ET.SubElement(new_item, "pubDate").text = i.get("pubDate", "")

# -----------------------------
# Write file (pretty printed)
# -----------------------------
rough_xml = ET.tostring(rss, encoding="utf-8")
pretty_xml = minidom.parseString(rough_xml).toprettyxml(indent="  ")

# Ensure docs/ exists if you’re writing there (useful locally)
# (GitHub Actions will have it if it’s committed, but this helps local runs.)
import os
os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

with open(output_file, "w", encoding="utf-8") as f:
    f.write(pretty_xml)

print(f"✅ Investor News RSS feed generated successfully: {output_file}")
if failed:
    print(f"ℹ️ Note: {failed} feed(s) failed/skipped due to network/rate limit/parse issues.")
