import re
import time
from functools import reduce
from typing import Callable

from github import Github
from rich.console import Console
from rich.progress import track


def warning(msg: str) -> None:
    console = Console()
    console.print(f"[yellow]:warning: Warning: {msg}[/yellow]")


def sleep(seconds: int) -> None:
    if seconds <= 0:
        return
    for _ in track(range(seconds), description="Waiting..."):
        time.sleep(1)


def maybe_sleep(g: Github, action: str, dry_run: bool, without_sleeping: bool) -> None:
    rl = g.get_rate_limit()
    retry_after = int(rl.raw_headers.get("retry-after", -1))
    # convert reset to number of seconds remaining between now and reset
    current_unix_time = time.time()
    reset_unix_time = int(rl.raw_headers["x-ratelimit-reset"])
    sleep_time = int(reset_unix_time - current_unix_time)
    if retry_after > 0:
        sleep(retry_after)
    elif rl.core.remaining < 10:
        sleep(sleep_time)
    elif action == "forked" and not dry_run and not without_sleeping:
        sleep(30)


def sleep_until_reset(g: Github) -> None:
    rl = g.get_rate_limit()
    current_unix_time = time.time()
    reset_unix_time = int(rl.raw_headers["x-ratelimit-reset"])
    sleep_time = int(reset_unix_time - current_unix_time)
    sleep(sleep_time)


USER_NAME_REGEX = re.compile(r"@[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}", re.IGNORECASE)


def text_pipeline(text: str, fns: list[Callable[[str], str]]) -> str:
    """
    Run all the text processing functions in a non-destructive way using functools.reduce
    """
    return reduce(lambda acc, fn: fn(acc), fns, text)


def replace_references(ref_a: str, ref_b: str) -> Callable[[str], str]:
    """
    Returns a function that changes all references from ref_a to ref_b.
    """
    pattern_a = re.compile(ref_a)

    def replacer(text: str) -> str:
        return pattern_a.sub(ref_b, text)

    return replacer


def replace_at_mentions(text: str) -> str:
    """
    Replaces all at-mentions in the text with a `@<username>` string.
    """
    return USER_NAME_REGEX.sub(r"`\g<0>`", text)


def create_repo_replace_function(repo_1: str, repo_2: str) -> Callable[[str], str]:
    """
    Returns a function that changes all references from repo_1 to repo_2.
    """
    pattern_a = rf"\b{repo_1}\b"
    return replace_references(pattern_a, repo_2)


def create_source_function(text: str, source: str, datestring: str, url: str) -> Callable[[str], str]:
    """
    Returns a function that adds a source reference to the text.
    """

    def replacer(text: str) -> str:
        github_profile = f"https://github.com/{source}"
        return text.rstrip() + f"\n\n<sub>Source: [`{source}`]({github_profile}) on [{datestring}]({url}).</sub>"

    return replacer
