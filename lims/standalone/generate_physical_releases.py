import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple, List

import requests

# ----------------------------
# Path setup (optional)
# ----------------------------
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

try:
    from lims.config.config import github_token
except Exception as e:
    raise RuntimeError(
        "Could not import lims.config.config.github_token. "
        "Place this script inside the repo (or adjust sys.path)."
    ) from e

OWNER = "GordonKP"
REPO = "LIMS"

# Extract semver anywhere in a tag, e.g. "v1.2.3", "release-1.2.3"
SEMVER_ANYWHERE = re.compile(r"(\d+)\.(\d+)\.(\d+)")

def gh_headers(json_mode: bool = True) -> dict:
    return {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json" if json_mode else "application/octet-stream",
        "User-Agent": "LIMS-Release-Downloader",
    }

def parse_semver_from_tag(tag: str) -> Optional[Tuple[int, int, int]]:
    """
    Returns (major, minor, patch) if a semver is found anywhere in the string.
    """
    if not tag:
        return None
    m = SEMVER_ANYWHERE.search(tag)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def fetch_all_releases(owner: str, repo: str) -> List[dict]:
    releases = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        params = {"per_page": 100, "page": page}
        r = requests.get(url, headers=gh_headers(json_mode=True), params=params, timeout=60)
        r.raise_for_status()
        items = r.json()
        if not items:
            break
        releases.extend(items)
        page += 1
    return releases

def choose_tarball_asset(rel: dict, version_str: str) -> Optional[dict]:
    """
    Prefer LIMS-x.x.x.tar.gz, else any .tar.gz. Returns the asset dict or None.
    """
    assets = rel.get("assets") or []
    if not assets:
        return None

    desired_exact = f"LIMS-{version_str}.tar.gz".lower()

    # 1) Exact name match first
    for a in assets:
        name = (a.get("name") or "").lower()
        if name == desired_exact:
            return a

    # 2) Any LIMS-*.tar.gz
    for a in assets:
        name = (a.get("name") or "").lower()
        if name.startswith("lims-") and name.endswith(".tar.gz"):
            return a

    # 3) Any .tar.gz
    for a in assets:
        name = (a.get("name") or "").lower()
        if name.endswith(".tar.gz"):
            return a

    return None

def download_asset(asset: dict, out_path: Path) -> None:
    """
    Download a release asset using its API URL with octet-stream accept header.
    """
    url = asset.get("url")  # API URL (not browser_download_url)
    if not url:
        raise RuntimeError("Asset missing 'url' field (API URL).")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, headers=gh_headers(json_mode=False), stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

def download_tarball_url(tarball_url: str, out_path: Path) -> None:
    """
    Downloads GitHub's auto-generated source tarball for a release tag.
    """
    if not tarball_url:
        raise RuntimeError("Release missing tarball_url.")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # IMPORTANT: do NOT use octet-stream Accept here; it can cause 415.
    headers = gh_headers(json_mode=True)

    with requests.get(tarball_url, headers=headers, stream=True, timeout=300, allow_redirects=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

def main():
    print("\n📦 Download LIMS releases (start version → latest)\n")

    start_input = input("Start release (e.g. 1.2.3 or v1.2.3): ").strip()
    start_ver = parse_semver_from_tag(start_input)
    if start_ver is None:
        print(f"❌ Couldn't parse a version from '{start_input}'. Expected something like 1.2.3")
        return

    dump_root_in = input("Output root folder (blank = ./releases): ").strip().strip('"')
    dump_root = Path(dump_root_in) if dump_root_in else Path.cwd() / "releases"

    print(f"\n🔍 Fetching releases for {OWNER}/{REPO} ...")
    all_releases = fetch_all_releases(OWNER, REPO)

    # Keep only releases where we can parse a semver from tag_name
    parsed = []
    for rel in all_releases:
        tag = rel.get("tag_name", "")
        v = parse_semver_from_tag(tag)
        if v is not None:
            parsed.append((v, rel))

    if not parsed:
        print("⚠️ No releases with semantic version tags were found.")
        return

    # Sort by version (not date)
    parsed.sort(key=lambda x: x[0])

    # Filter start -> latest
    targets = [(v, rel) for (v, rel) in parsed if v >= start_ver]
    if not targets:
        newest = parsed[-1][0]
        print(f"⚠️ No releases found >= {start_ver}. Newest parsed release is {newest}.")
        return

    print(f"✅ Will download {len(targets)} releases into: {dump_root}\n")

    ok = 0
    skipped = 0
    missing = 0
    failed = 0

    for v, rel in targets:
        version_str = f"{v[0]}.{v[1]}.{v[2]}"
        folder = dump_root / version_str
        out_file = folder / f"LIMS-{version_str}.tar.gz"

        if out_file.exists():
            print(f"⏭️  {version_str}: already exists -> {out_file}")
            skipped += 1
            continue

        asset = choose_tarball_asset(rel, version_str)

        if asset is not None:
            asset_name = asset.get("name") or "(unknown asset name)"
            print(f"⬇️  {version_str}: downloading asset {asset_name} -> {out_file.name}")
            try:
                download_asset(asset, out_file)
                ok += 1
                print(f"✅ {version_str}: saved")
            except Exception as e:
                failed += 1
                print(f"❌ {version_str}: failed to download asset: {e}")
            continue

        # Fallback: GitHub auto-generated "Source code (tar.gz)"
        tarball_url = rel.get("tarball_url")
        if not tarball_url:
            print(f"⚠️  {version_str}: no tar.gz asset AND no tarball_url. Skipping.")
            missing += 1
            continue

        print(f"⬇️  {version_str}: downloading source tarball_url -> {out_file.name}")
        try:
            download_tarball_url(tarball_url, out_file)
            ok += 1
            print(f"✅ {version_str}: saved")
        except Exception as e:
            failed += 1
            print(f"❌ {version_str}: failed to download tarball_url: {e}")

    print("\n==============================")
    print("Done.")
    print(f"Downloaded:       {ok}")
    print(f"Already existed:  {skipped}")
    print(f"Missing tarballs: {missing}")
    print(f"Failed:           {failed}")
    print("==============================\n")

if __name__ == "__main__":
    main()
