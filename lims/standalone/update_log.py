import sys
import os

# Get the absolute path of the parent directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Add the parent directory to sys.path
sys.path.append(project_root)

from lims.config.file_paths import logbook_directory

def github_get_release_notes(owner, repo, out_path, start_date=None, end_date=None):
    import requests
    from datetime import datetime
    from lims.config.config import github_token

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Python-Updater"
    }

    # Convert date strings to datetime objects
    def parse_date(date_str):
        if not date_str:
            return None
        return datetime.strptime(date_str, "%m-%d-%Y")

    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)

    all_releases = []
    page = 1

    print("\n🔍 Fetching ALL releases from GitHub...")

    while True:
        releases_url = (
            f"https://api.github.com/repos/{owner}/{repo}/releases"
            f"?per_page=100&page={page}"
        )
        print(f"➡️ Fetch page {page}: {releases_url}")

        r = requests.get(releases_url, headers=headers)
        print("⬅️ Status:", r.status_code)
        r.raise_for_status()

        page_items = r.json()
        if not page_items:
            break

        all_releases.extend(page_items)
        page += 1

    print(f"📦 Total releases fetched: {len(all_releases)}")

    # Apply date filtering
    def is_in_range(published_at):
        if not published_at:
            return False

        dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")

        if start_dt and dt < start_dt:
            return False
        if end_dt and dt > end_dt:
            return False

        return True

    filtered = [rel for rel in all_releases if is_in_range(rel.get("published_at"))]

    print(f"📘 Releases in date range: {len(filtered)}")
    if not filtered:
        print("⚠️ No releases found in that date range.")

    # → ALSO WRITE THE RANGE TO THE FILE
    print(f"📝 Writing release history to: {out_path}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("Date Range:\n")
        f.write(f"Start: {start_date or 'ALL'}\n")
        f.write(f"End: {end_date or 'ALL'}\n\n")

        for rel in filtered:
            tag = rel.get("tag_name", "UNKNOWN_TAG")
            date = rel.get("published_at", "UNKNOWN_DATE")
            notes = rel.get("body", "").strip()

            f.write(f"--- RELEASE: {tag} ---\n")
            f.write(f"Date: {date}\n")
            f.write("Notes:\n")
            f.write((notes or "[No release notes]") + "\n\n")

    print("✅ Release notes saved successfully!")


# --------------------------
# PROMPT USER FOR DATE RANGE
# --------------------------

def ask_for_date(prompt_text):
    from datetime import datetime
    while True:
        value = input(prompt_text).strip()
        if value == "":
            return None
        try:
            datetime.strptime(value, "%m-%d-%Y")
            return value
        except ValueError:
            print("❌ Invalid date format! Please use MM-DD-YYYY.\n")


print("\n🗓 Enter release date range (press ENTER for no limit):\n")

start_date = ask_for_date("Start date (MM-DD-YYYY or blank): ")
end_date   = ask_for_date("End date   (MM-DD-YYYY or blank): ")

if start_date is None or end_date is None:
    out_path = os.path.join(logbook_directory, f"All_LIMS_Releases.txt")
else:
    out_path = os.path.join(logbook_directory, f"LIMS_Releases_{start_date}_{end_date}.txt")

# CALL MAIN FUNCTION
github_get_release_notes(
    owner="GordonKP",
    repo="LIMS",
    out_path=out_path,
    start_date=start_date,
    end_date=end_date
)
