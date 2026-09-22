# Central Garden & Pet — Investor News Alerts

Published RSS feed:

https://rchern315.github.io/investor-news-feed/news-feed.xml

This repository powers an automated investor news alert system for Central Garden & Pet (CENTA / CENT). It aggregates company-related investor and market news from public RSS sources, normalizes the results into a single RSS feed, and publishes that feed through GitHub Pages.

The project is built with Python, configured through YAML, and updated automatically with GitHub Actions.

## How the system works

The overall flow is:

```text
Yahoo Finance CENTA RSS
          \
Yahoo Finance CENT RSS
            \
Google News search RSS
              ↓
           feed.py
              ↓
      Parse + normalize
              ↓
      Dedupe + sort dates
              ↓
      docs/news-feed.xml
              ↓
        GitHub commit
              ↓
        GitHub Pages
              ↓
https://rchern315.github.io/investor-news-feed/news-feed.xml
```

Every six hours, GitHub Actions checks the configured source feeds, runs the Python script, rebuilds the combined RSS feed, and commits the generated XML file if anything changed.

The workflow can also be started manually from the GitHub Actions tab.

## Repository structure

### `feed.py`

This is the main Python script.

It is responsible for:

- Reading configuration from `feed.yaml`
- Downloading all configured RSS or Atom feeds
- Following redirects
- Logging HTTP status, final URL, content type, and response size
- Parsing XML
- Supporting standard RSS `<item>` entries
- Supporting Atom `<entry>` entries
- Handling XML namespaces
- Extracting article title, link, and publication date
- Falling back to `<guid>` when a normal article link is not available
- Normalizing publication dates
- Deduplicating articles
- Sorting articles newest-first
- Limiting the total number of published articles
- Building a new RSS 2.0 feed
- Writing the result to `docs/news-feed.xml`

### `feed.yaml`

This file contains the configurable feed settings.

Current configuration:

```yaml
title: Central Garden & Pet — Investor News Alerts
link: https://finance.yahoo.com/quote/CENTA
description: Automated investor news feed for Central Garden & Pet (CENTA / CENT)
language: en-us

source_feeds:
  - https://feeds.finance.yahoo.com/rss/2.0/headline?s=CENTA&region=US&lang=en-US
  - https://feeds.finance.yahoo.com/rss/2.0/headline?s=CENT&region=US&lang=en-US
  - https://news.google.com/rss/search?q=Central+Garden+%26+Pet&hl=en-US&gl=US&ceid=US:en
```

The script supports either:

```yaml
source_feed: https://example.com/feed.xml
```

or multiple feeds:

```yaml
source_feeds:
  - https://example.com/feed-one.xml
  - https://example.com/feed-two.xml
```

### `requirements.txt`

This file defines the Python packages required by the project.

Current dependencies:

```text
requests
pyyaml
```

### `.github/workflows/build-feed.yml`

This is the GitHub Actions workflow.

It:

1. Runs on Ubuntu.
2. Checks out the repository.
3. Installs Python 3.12.
4. Installs the packages from `requirements.txt`.
5. Runs `python feed.py`.
6. Adds `docs/news-feed.xml` to Git.
7. Commits the file only if the generated feed changed.
8. Pushes the update back to the repository.

The workflow runs on this schedule:

```yaml
schedule:
  - cron: "0 */6 * * *"
```

That means the feed is rebuilt every six hours.

The workflow also includes:

```yaml
workflow_dispatch:
```

This allows it to be run manually from GitHub.

### `docs/news-feed.xml`

This is the generated RSS feed.

It should not normally be edited by hand because `feed.py` regenerates it.

GitHub Pages publishes this file at:

https://rchern315.github.io/investor-news-feed/news-feed.xml

## What happens inside `feed.py`

### 1. Load configuration

The script opens `feed.yaml` and loads the YAML configuration.

It reads:

- Feed title
- Feed link
- Feed description
- Language
- Source feed URLs
- Optional output file
- Optional maximum article count

If no source feeds are configured, the script exits with an error.

### 2. Download the source feeds

For each source URL, the script sends an HTTP request with headers that accept RSS, Atom, XML, and standard web responses.

Redirects are allowed.

The request uses a timeout so a source cannot hang the build indefinitely.

The GitHub Actions log prints:

- Source URL
- HTTP status
- Final URL after redirects
- Content type
- Response size

### 3. Parse the XML

The response is parsed using Python's `xml.etree.ElementTree`.

The parser supports both:

```xml
<item>
```

and:

```xml
<entry>
```

This allows the script to work with both traditional RSS feeds and Atom-style feeds.

The parser also strips XML namespaces before comparing tag names.

### 4. Extract article information

For every article entry, the script looks for:

- Title
- Link
- Publication date

For links, it supports:

```xml
<link>https://example.com/article</link>
```

and Atom-style links:

```xml
<link href="https://example.com/article" />
```

If no normal link is available, it can fall back to `<guid>`.

For dates, the script checks several common names, including:

- `pubDate`
- `published`
- `updated`
- `date`
- `issued`
- `created`

### 5. Normalize publication dates

RSS feeds do not always format dates the same way.

The script supports standard RSS / RFC 2822 dates such as:

```text
Wed, 16 Sep 2026 13:40:03 +0000
```

It also supports ISO-style dates such as:

```text
2026-09-16T13:40:03Z
```

All parsed dates are made timezone-aware before sorting.

This is important because Python cannot safely compare a timezone-aware datetime with a timezone-naive datetime.

If a date cannot be parsed, it receives a very old fallback date so it does not break the build.

### 6. Deduplicate articles

The script removes duplicate articles.

It uses the article link as the primary unique key.

If no link is available, it falls back to the article title.

### 7. Sort articles

Articles are sorted newest-first using their publication date.

### 8. Limit the number of published articles

The script supports an optional `max_items` setting in `feed.yaml`.

Example:

```yaml
max_items: 40
```

If `max_items` is not present, the script defaults to:

```text
40
```

### 9. Build the combined RSS feed

The script creates a new RSS 2.0 document.

Each article is written as an `<item>` containing:

- `<title>`
- `<link>`
- `<guid>` when a link exists
- `<pubDate>` when a date exists

### 10. Write the output file

The generated feed is written to:

```text
docs/news-feed.xml
```

The XML is pretty-printed before it is saved.

## GitHub Actions automation

The workflow is located at:

```text
.github/workflows/build-feed.yml
```

It runs automatically every six hours.

The important generation step is:

```yaml
- name: Generate feed
  run: python feed.py
```

After generation, GitHub adds only the generated feed file:

```bash
git add docs/news-feed.xml
```

Then it checks whether anything changed.

If there are no changes, no commit is created.

If there are changes, GitHub Actions commits and pushes the new feed.

## GitHub Pages publishing

GitHub Pages serves the contents of the `docs` folder.

The repository file:

```text
docs/news-feed.xml
```

is therefore published at:

```text
https://rchern315.github.io/investor-news-feed/news-feed.xml
```

That public URL is the canonical RSS feed URL to use in applications, integrations, or other websites.

## Running the project locally on Windows

### 1. Clone the repository

Open PowerShell and run:

```powershell
git clone https://github.com/rchern315/investor-news-feed.git
cd investor-news-feed
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, you may need to allow local scripts for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the environment again.

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Run the feed generator

```powershell
python feed.py
```

A successful run should show diagnostics for each source feed and finish with messages similar to:

```text
Total unique articles being written: 20
Generated: docs/news-feed.xml
Feed contains 20 article(s).
```

### 6. Review the generated feed

Open:

```text
docs/news-feed.xml
```

Confirm that the newest article appears near the top.

## Adding another source feed

Open `feed.yaml`.

Add the new source under `source_feeds`:

```yaml
source_feeds:
  - https://feeds.finance.yahoo.com/rss/2.0/headline?s=CENTA&region=US&lang=en-US
  - https://feeds.finance.yahoo.com/rss/2.0/headline?s=CENT&region=US&lang=en-US
  - https://news.google.com/rss/search?q=Central+Garden+%26+Pet&hl=en-US&gl=US&ceid=US:en
  - https://example.com/new-feed.xml
```

Run locally:

```powershell
python feed.py
```

Check the console output to confirm that articles were found in the new source.

## Changing the maximum number of articles

Add `max_items` to `feed.yaml`.

Example:

```yaml
max_items: 50
```

The script will then publish at most 50 unique articles.

If the setting is omitted, the default is 40.

## Running the workflow manually

In GitHub:

1. Open the repository.
2. Select the **Actions** tab.
3. Select **Investor News RSS Feed**.
4. Choose **Run workflow**.
5. Run the workflow from the `main` branch.

After the workflow completes, review the log for the **Generate feed** step.

## Diagnostics in the GitHub Actions log

For every source feed, the script prints diagnostic information.

Example:

```text
SOURCE FEED: https://example.com/feed.xml
HTTP status: 200
Final URL: https://example.com/feed.xml
Content-Type: application/rss+xml
Response bytes: 12345
XML root tag: rss
Article nodes found: 20
Usable articles collected from this feed: 20
```

It also prints up to three example articles from each source.

These messages are useful when troubleshooting a source feed.

## Troubleshooting

### No articles are being generated

Look at the GitHub Actions log for:

```text
ZERO ARTICLES WERE COLLECTED
```

Then review each source feed section.

Check:

- HTTP status
- Final URL
- Content type
- XML root tag
- Article node count

### HTTP 403

A `403` means the source is refusing the request.

Possible causes include:

- Bot protection
- Rate limiting
- User-agent restrictions
- Source-side access rules

The failed source will be skipped while other working feeds continue.

### HTTP 404

A `404` usually means the source feed URL changed or no longer exists.

Open the URL in a browser and verify the current RSS endpoint.

### HTTP 500 or other server errors

These usually indicate a temporary source-side problem.

If other feeds are working, the script continues and builds the combined feed from the available sources.

### Content-Type is `text/html`

If the response says:

```text
Content-Type: text/html
```

the URL may be returning:

- A normal web page
- A login page
- A bot-block page
- An error page
- A redirect landing page

Review the final URL and response diagnostics.

### XML parse error

If the response is not valid XML, the script prints a preview of the returned content.

This helps determine whether the source returned HTML or malformed XML instead of RSS.

### Article nodes found: 0

The parser could not find either:

```xml
<item>
```

or:

```xml
<entry>
```

The script prints the XML tags it did find so the feed structure can be inspected.

### Feed runs successfully but no commit is created

This is normal when the generated `docs/news-feed.xml` file is identical to the version already in Git.

The workflow uses:

```bash
git diff --cached --quiet || git commit -m "Update investor news feed"
```

If there is no difference, GitHub skips the commit.

### Feed appears stale

Check the repository version of:

```text
docs/news-feed.xml
```

Then check the public URL:

```text
https://rchern315.github.io/investor-news-feed/news-feed.xml
```

Confirm that the newest article and publication date match.

If the repository file is newer than the GitHub Pages version, check the repository's GitHub Pages deployment status.

### Date or sorting errors

The script converts dates into timezone-aware `datetime` values before sorting.

This prevents errors such as:

```text
TypeError: can't compare offset-naive and offset-aware datetimes
```

If a source introduces a new date format, inspect the `pubDate`, `published`, or `updated` value in the source XML.

## Testing changes before committing

After changing `feed.py` or `feed.yaml`:

1. Activate the local Python environment.
2. Run:

```powershell
python feed.py
```

3. Confirm every source returns the expected HTTP status.
4. Confirm articles are found.
5. Confirm the article count is reasonable.
6. Open `docs/news-feed.xml`.
7. Confirm the newest article is first.
8. Confirm titles and links are valid.
9. Confirm the XML opens without a parse error.
10. Commit the change only after the local feed looks correct.

## Tech stack

- Python 3.12
- PyYAML
- Requests
- XML ElementTree
- GitHub Actions
- GitHub Pages
- RSS 2.0
