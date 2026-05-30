from __future__ import annotations

import webbrowser
from collections.abc import Sequence

from .launcher import LaunchResult


def open_url(url: str) -> LaunchResult:
    webbrowser.open_new_tab(url)
    return LaunchResult(True, f"Opened {url}", target=url)


def open_tabs(urls: Sequence[str]) -> LaunchResult:
    opened = 0
    opened_urls: list[str] = []
    for url in urls:
        if not url.strip():
            continue
        webbrowser.open_new_tab(url)
        opened += 1
        opened_urls.append(url)
    return LaunchResult(True, f"Opened {opened} browser tab(s).", target="; ".join(opened_urls))
