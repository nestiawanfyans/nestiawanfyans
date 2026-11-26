#!/usr/bin/env python3
"""
Automatically fetches languages from GitHub repositories and updates
the AUTO-TECH-STACK section in README.md using skillicons.dev.
"""

import json
import os
import re
import urllib.request
from pathlib import Path

USERNAME = os.getenv("GITHUB_USERNAME", "nestiawanfyans")
TOKEN = os.getenv("GH_PAT") or os.getenv("GITHUB_TOKEN")
README_PATH = Path(__file__).resolve().parent.parent / "README.md"

# Mapping GitHub Linguist language names -> skillicons.dev icon IDs
LANG_TO_ICON = {
    "TypeScript": "ts",
    "JavaScript": "js",
    "Vue": "vue",
    "PHP": "php",
    "Blade": "laravel",
    "Java": "java",
    "Python": "python",
    "HTML": "html",
    "CSS": "css",
    "SCSS": "sass",
    "Go": "go",
    "Rust": "rust",
    "Kotlin": "kotlin",
    "Swift": "swift",
    "Dart": "dart",
    "C#": "cs",
    "C++": "cpp",
    "C": "c",
    "Ruby": "ruby",
    "Shell": "bash",
    "Dockerfile": "docker",
    "SQL": "mysql",
    "PLpgSQL": "postgres",
    "Svelte": "svelte",
    "Astro": "astro",
}

# Core tools (Software Engineering & IT Support) that GitHub Linguist does not detect as code
ALWAYS_INCLUDE_TOOLS = ["git", "linux"]


def github_get(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-tech-stack-updater",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_repos():
    # If a personal access token (GH_PAT) is provided, /user/repos includes private repos too.
    if os.getenv("GH_PAT"):
        url = "https://api.github.com/user/repos?per_page=100&affiliation=owner&sort=updated"
    else:
        url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated"
    return github_get(url)


def collect_language_totals(repos) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        langs_url = repo.get("languages_url")
        if not langs_url:
            continue
        try:
            lang_bytes = github_get(langs_url)
            for lang, count in lang_bytes.items():
                totals[lang] = totals.get(lang, 0) + int(count)
        except Exception as exc:
            print(f"Skipping {repo.get('name')}: {exc}")
    return totals


def build_icon_list(totals: dict[str, int]) -> list[str]:
    ordered_langs = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    icons: list[str] = []
    for lang, _ in ordered_langs:
        icon = LANG_TO_ICON.get(lang)
        if icon and icon not in icons:
            icons.append(icon)
    for tool in ALWAYS_INCLUDE_TOOLS:
        if tool not in icons:
            icons.append(tool)
    return icons[:12]


def update_readme(icons: list[str]) -> None:
    if not icons:
        print("No icons detected; keeping existing README.")
        return

    icon_query = ",".join(icons)
    replacement = (
        "<!-- AUTO-TECH-STACK:START -->\n"
        '<div align="center">\n'
        f'  <img src="https://skillicons.dev/icons?i={icon_query}&theme=dark" alt="Tech Stack" />\n'
        "</div>\n"
        "<!-- AUTO-TECH-STACK:END -->"
    )

    content = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"<!-- AUTO-TECH-STACK:START -->.*?<!-- AUTO-TECH-STACK:END -->",
        re.DOTALL,
    )
    if not pattern.search(content):
        raise RuntimeError("Markers AUTO-TECH-STACK not found in README.md")

    updated = pattern.sub(replacement, content, count=1)
    if updated != content:
        README_PATH.write_text(updated, encoding="utf-8")
        print(f"Updated README.md with icons: {icon_query}")
    else:
        print(f"README.md already up to date ({icon_query})")


def main() -> None:
    repos = fetch_repos()
    totals = collect_language_totals(repos)
    icons = build_icon_list(totals)
    print("Detected language bytes:", totals)
    print("Selected icons:", icons)
    update_readme(icons)


if __name__ == "__main__":
    main()
