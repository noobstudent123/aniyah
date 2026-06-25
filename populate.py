#!/usr/bin/env python3
"""
populate.py  —  fill aniyahmonae recreation with real images
-------------------------------------------------------------
Run this once on your own machine (it needs normal internet access):

    python populate.py

It fetches every gallery and project page from the live site, extracts the
real Squarespace image URLs (the ones hidden in lazy-load attributes), and
rewrites index.html in place so every gallery and lightbox is fully populated.

No third-party packages required — uses only the Python standard library.
Safe to re-run anytime the live site changes.
"""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HTML_FILE = Path(__file__).with_name("index.html")
ORIGIN = "https://www.aniyahmonae.com"
ACCOUNT = "6a14f154b22bc70393b1425b"  # Aniyah's Squarespace CDN account id

# Match real CDN image URLs wherever they appear in the page source
IMG_RE = re.compile(
    r"https://images\.squarespace-cdn\.com/content/v1/"
    + ACCOUNT
    + r"/[^\"'\s\\)<>]+?\.(?:jpe?g|png|webp|gif)",
    re.IGNORECASE,
)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Structure mirrors the SITE object in index.html
LINK_GALLERIES = {
    "installation": ["pipelineinstallation", "walkerwearinstallation", "aniyahmonaeinstallation"],
    "conceptual":   ["ninasimone", "red"],
    "costume":      ["journeystofreedom", "pipelinecostume", "this-little-light-of-mine"],
    "illustration": ["conceptual-illustration", "costumeillustration",
                     "fashion-illustration", "introspection-illustration"],
    "fashion":      ["reebokwalkerwear", "lilnasxbet"],
}
LINK_TITLES = {
    "pipelineinstallation": "Pipeline Installation",
    "walkerwearinstallation": "Walker Wear Installation",
    "aniyahmonaeinstallation": "Aniyah Monae Installation",
    "ninasimone": "Nina Simone", "red": "Red",
    "journeystofreedom": "Journeys to Freedom",
    "pipelinecostume": "Pipeline Costume Design",
    "this-little-light-of-mine": "This Little Light of Mine",
    "conceptual-illustration": "Conceptual Illustration",
    "costumeillustration": "Costume Illustration",
    "fashion-illustration": "Fashion Illustration",
    "introspection-illustration": "Introspective Illustration",
    "reebokwalkerwear": "Reebok x Walker Wear",
    "lilnasxbet": "Lil Nas X BET Awards 2021",
}
WALL_GALLERIES = {
    "exhibition": "exhibition",
    "tailoring": "tailoring",
}
EXHIBITION_HEADING = "American Dream Exhibition"


def fetch(path):
    url = path if path.startswith("http") else ORIGIN + "/" + path
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception as e:  # noqa
        print(f"   ! could not fetch {url}: {e}")
        return ""


def images_from(path):
    """Ordered, de-duplicated CDN image URLs found on a page."""
    html = fetch(path)
    seen, out = set(), []
    for m in IMG_RE.findall(html):
        if m not in seen:
            seen.add(m)
            out.append(m)
    time.sleep(0.4)  # be polite
    return out


def build_site():
    site = {}

    # --- link galleries: cover from index page, images from each project page ---
    for key, slugs in LINK_GALLERIES.items():
        print(f"• {key}")
        index_imgs = images_from(key)              # covers in project order
        projects = []
        for i, slug in enumerate(slugs):
            print(f"   - {slug}")
            imgs = images_from(slug)
            cover = imgs[0] if imgs else (index_imgs[i] if i < len(index_imgs) else "")
            projects.append({
                "title": LINK_TITLES[slug],
                "slug": slug,
                "cover": cover,
                "images": imgs,
            })
        site[key] = {"kind": "links", "projects": projects}

    # --- wall galleries: every image on the page ---
    for key, path in WALL_GALLERIES.items():
        print(f"• {key}")
        imgs = images_from(path)
        entry = {"kind": "wall", "images": imgs}
        if key == "exhibition":
            entry["heading"] = EXHIBITION_HEADING
        site[key] = entry

    # --- biography portrait ---
    print("• biography portrait")
    bio = images_from("biography")
    portrait = bio[0] if bio else ""

    return site, portrait


def js_block(site, portrait):
    site_json = json.dumps(site, indent=2, ensure_ascii=False)
    lines = [
        "/* SITE_DATA_START */",
        f'const ORIGIN = "{ORIGIN}";',
    ]
    if portrait:
        lines.append(f'const PORTRAIT = "{portrait}";')
    else:
        lines.append('const PORTRAIT = "";')
    lines.append("const SITE = " + site_json + ";")
    lines.append("/* SITE_DATA_END */")
    return "\n".join(lines)


def main():
    if not HTML_FILE.exists():
        sys.exit(f"index.html not found next to this script ({HTML_FILE}).")

    html = HTML_FILE.read_text(encoding="utf-8")
    if "/* SITE_DATA_START */" not in html or "/* SITE_DATA_END */" not in html:
        sys.exit("Could not find SITE_DATA markers in index.html.")

    print("Scraping live site for image URLs...\n")
    site, portrait = build_site()

    total = 0
    for key, g in site.items():
        if g["kind"] == "wall":
            total += len(g["images"])
        else:
            total += sum(len(p["images"]) for p in g["projects"])
    print(f"\nCollected {total} image URLs.")

    new_block = js_block(site, portrait)
    html = re.sub(
        r"/\* SITE_DATA_START \*/.*?/\* SITE_DATA_END \*/",
        lambda _: new_block,
        html,
        count=1,
        flags=re.DOTALL,
    )
    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"\nDone. Rewrote {HTML_FILE.name}. Open it in your browser.")


if __name__ == "__main__":
    main()
