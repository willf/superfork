import contextlib
import re
import time
from collections.abc import Iterator
from functools import reduce
from typing import Callable, Never

from github import Github, GithubException, RateLimitExceededException
from rich.console import Console
from rich.progress import track


def warning(msg: str) -> None:
    console = Console()
    console.print(f"[yellow]:warning: Warning: {msg}[/yellow]")


def sleep(seconds: int, message: str = "Waiting") -> None:
    if seconds <= 0:
        return
    for _ in track(range(seconds), description=message):
        time.sleep(1)


@contextlib.contextmanager
def graceful_calling(g: Github, fn: Callable, is_mutating: int, max_tries: int = 3) -> Iterator[Never]:
    for i in range(max_tries):
        if i > 0:
            print(f"Retrying {i + 1} of {max_tries}")
        try:
            result = fn()
            if is_mutating:
                sleep(is_mutating, message="A slight pause after a mutating call")
            yield result
            break
        except (RateLimitExceededException, GithubException) as e:
            print(f"Error: {e}")
            retry_after = -1
            reset_unix_time = -1
            if e.headers:
                retry_after = int(e.headers.get("Retry-After", -1))
                reset_unix_time = int(e.headers.get("X-RateLimit-Reset", -1))
            if retry_after > 0:
                sleep(retry_after, message="Rate limit exceeded; retry after")
            elif reset_unix_time > 0:
                sleep_time = int(reset_unix_time - time.time())
                sleep(sleep_time, message="Rate limit exceeded; waiting until reset")
            else:
                # exponential backoff, starting at 2**4 = 16 seconds
                n = i + 4
                sleep(2**n, message="Error, backing off")


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
