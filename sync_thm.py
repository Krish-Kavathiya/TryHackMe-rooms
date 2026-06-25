#!/usr/bin/env python3
import re
import sys
import time
import cloudscraper # type: ignore
    
User_name = "D4741"
API = "https://tryhackme.com/api/v2/public-profile/completed-rooms"
README = "README.md"


def fetch_completed_rooms(User_name):
    codes = set()
    page = 1
    scraper = cloudscraper.create_scraper()
    while True:
        for attempt in range(3):
            try:
                resp = scraper.get(
                    API,
                    params={"username": User_name, "limit": 200, "page": page},
                    timeout=30,
                )
            except Exception as e:
                print(f"  Request failed: {e}")
                time.sleep(5)
                continue
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        else:
            resp.raise_for_status()
        data = resp.json()
        for room in data.get("data", {}).get("docs", []):
            codes.add(room["code"])
        pagination = data.get("data", {})
        if page >= pagination.get("totalPages", 1):
            break
        page += 1
    return codes


def room_code_from_url(url):
    return url.rstrip("/").rsplit("/room/", 1)[-1] if "/room/" in url else None


def sync_readme(completed_codes):
    with open(README, "r") as f:
        content = f.read()
        lines = content.split("\n")

    changes = 0
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*-\s)\[[ x]\](\s.*)", line)
        if not m:
            continue
        url_match = re.search(r"https://tryhackme\.com/room/[\w-]+", line)
        if not url_match:
            continue
        code = room_code_from_url(url_match.group(0))
        if not code:
            continue
        should_check = code in completed_codes
        is_checked = "[x]" in line
        if should_check and not is_checked:
            lines[i] = f"{m.group(1)}[x]{m.group(2)}"
            changes += 1
        elif not should_check and is_checked:
            lines[i] = f"{m.group(1)}[ ]{m.group(2)}"
            changes += 1

    if changes == 0:
        print("No checkbox changes needed")
    else:
        print(f"Updated {changes} room(s)")

    update_table(lines)
    with open(README, "w") as f:
        f.write("\n".join(lines))


def anchorize(text):
    return "#" + re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")


def normalize(h):
    return re.sub(r"-+", "-", h)


def update_table(lines):
    table_start = None
    table_end = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("| 🔐"):
            table_start = i
        if table_start is not None and s.startswith("| **Total"):
            table_end = i

    if table_start is None or table_end is None:
        print("Warning: could not find TOC table")
        return

    cat_rows = []
    for i in range(table_start + 2, table_end):
        line = lines[i]
        m = re.match(r"\|(\s*\*\*\[.+?\]\(#.+?\)\*\*\s*)\|", line)
        if not m:
            continue
        anchor_m = re.search(r"\((#.+?)\)", m.group(1))
        if anchor_m:
            cat_rows.append((i, anchor_m.group(1)))

    headings = {}
    heading_re = re.compile(r"^##\s+(.+)$")
    for i, line in enumerate(lines):
        m = heading_re.match(line)
        if m:
            h = normalize(anchorize(m.group(1)))
            headings[h] = i

    total_all = 0
    completed_all = 0
    for row_idx, anchor in cat_rows:
        key = normalize(anchor)
        if key not in headings:
            print(f"Warning: no heading found for {anchor}")
            continue
        start = headings[key] + 1
        end = len(lines)
        for j in range(start, len(lines)):
            if heading_re.match(lines[j]):
                end = j
                break

        total = 0
        completed = 0
        for j in range(start, end):
            line = lines[j].strip()
            if line.startswith("- [ ]"):
                total += 1
            elif line.startswith("- [x]"):
                total += 1
                completed += 1

        total_all += total
        completed_all += completed

        parts = lines[row_idx].split("|")
        parts[2] = re.sub(r"\d+", str(total), parts[2])
        parts[3] = re.sub(r"\d+", str(completed), parts[3])
        lines[row_idx] = "|".join(parts)

    parts = lines[table_end].split("|")
    parts[2] = re.sub(r"\d+", str(total_all), parts[2])
    parts[3] = re.sub(r"\d+", str(completed_all), parts[3])
    lines[table_end] = "|".join(parts)

    print(f"Table stats: {completed_all}/{total_all} rooms completed")


if __name__ == "__main__":
    print("Fetching completed rooms from TryHackMe...")
    try:
        completed = fetch_completed_rooms(User_name=User_name)
        print(f"Found {len(completed)} completed rooms on TryHackMe")
        sync_readme(completed)
    except Exception as e:
        print(f"Error fetching from TryHackMe API: {e}")
        sys.exit(1)
