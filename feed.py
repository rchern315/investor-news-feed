import yaml
import requests
from xml.dom import minidom
import xml.etree.ElementTree as ET
import sys

# -----------------------------
# Load configuration
# -----------------------------
with open("feed.yaml", "r") as file:
    config = yaml.safe_load(file)

# -----------------------------
# Fetch external RSS feed
# -----------------------------
headers = {
    "User-Agent": "Mozilla/5.0 (compatible; GitHubActionsBot/1.0)"
}

try:
    response = requests.get(
        config["source_feed"],
        headers=headers,
        timeout=10
    )
except requests.RequestException as e:
    print(f"❌ Network error: {e}")
    sys.exit(0)

if response.status_code != 200:
    print(f"⚠️ Yahoo blocked request ({response.status_code}). Try again later.")
    sys.exit(0)

external_rss = ET.fromstring(response.content)

# -----------------------------
# Create RSS feed
# -----------------------------
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = config["title"]
ET.SubElement(channel, "link").text = config["link"]
ET.SubElement(channel, "description").text = config["description"]
ET.SubElement(channel, "language").text = config["language"]

# -----------------------------
# Copy items
# -----------------------------
for item in external_rss.findall("./channel/item")[:20]:
    new_item = ET.SubElement(channel, "item")
    ET.SubElement(new_item, "title").text = item.findtext("title")
    ET.SubElement(new_item, "link").text = item.findtext("link")
    ET.SubElement(new_item, "pubDate").text = item.findtext("pubDate")

# -----------------------------
# Write file (pretty printed)
# -----------------------------
rough_xml = ET.tostring(rss, encoding="utf-8")
pretty_xml = minidom.parseString(rough_xml).toprettyxml(indent="  ")

with open("news-feed.xml", "w", encoding="utf-8") as f:
    f.write(pretty_xml)

print("✅ Investor News RSS feed generated successfully")
