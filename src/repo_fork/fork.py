import os
import random
import time
from typing import Optional

import click
from dotenv import load_dotenv
from github import Auth, Github, Repository, UnknownObjectException
from rich import print
from rich.progress import track


def warning(msg: str) -> None:
    print(f"[yellow]:warning: {msg}[/yellow]")


def sleep(seconds: int) -> None:
    if seconds <= 0:
        return
    for _ in track(range(seconds), description="Waiting..."):
        time.sleep(1)


def maybe_sleep(g: Github, action: Optional[str] = None) -> None:
    rl = g.get_rate_limit()
    retry_after = int(rl.raw_headers.get("retry-after", -1))
    # convert reset to number of seconds remaining between now and reset
    current_unix_time = time.time()
    reset_unix_time = int(rl.raw_headers["x-ratelimit-reset"])
    sleep_time = reset_unix_time - current_unix_time
    if retry_after > 0:
        sleep(retry_after)
    elif rl.core.remaining < 10:
        sleep(sleep_time)
    elif action == "forked":
        sleep(15)


def get_repo(nwo: str, g: Optional[Github]) -> Repository:
    if not g:
        g = get_github()
    try:
        return g.get_repo(nwo)
    except UnknownObjectException:
        return None


def sync(repo: Repository, branch: Optional[str] = None) -> dict:
    """
    :calls: `POST /repos/{owner}/{repo}/merge-upstream <https://docs.github.com/en/rest/branches/branches#sync-a-fork-branch-with-the-upstream-repository>`_
    :param branch: string
    :rtype: :class: dict
    :raises: :class:`GithubException` for error status codes
    """
    if not branch:
        branch = repo.default_branch
    post_parameters = {"branch": branch}
    headers, data = repo._requester.requestJsonAndCheck("POST", f"{repo.url}/merge-upstream", input=post_parameters)
    return data


def get_github(token: Optional[str] = None) -> Github:
    if not token:
        load_dotenv()
        token = os.getenv("GITHUB_TOKEN")
    auth = Auth.Token(token)
    g = Github(auth=auth)
    return g


def get_user(g: Optional[Github] = None, token: Optional[str] = None) -> str:
    if not g:
        g = get_github(token)
    return g.get_user()


def fork_or_sync(from_repo: str, to_location: str, branch: Optional[str] = None) -> Repository:
    """ """
    (from_user, from_name) = from_repo.split("/")
    parts = to_location.split("/")
    to_user = parts[0]
    if len(parts) == 1:
        to_location = "/".join([to_user, from_name])
    else:
        warning("igorning destination repository name")
    g = get_github()
    user = get_user(g)
    user_name = user.login
    from_repo = get_repo(from_repo, g)
    if not from_repo:
        raise UnknownObjectException(from_repo)
    to_location = get_repo(to_location, g)
    if to_location:
        sync(to_location, branch)
        return ("synced", to_location)
    else:
        if to_user == user_name:
            return ("forked", user.create_fork(from_repo))
        else:
            org = g.get_organization(to_user)
            return ("forked", org.create_fork(from_repo))


def filter_repos(repos, include_private: bool = True, include_forks: bool = False, include_dot_github: bool = False):
    for repo in repos:
        if repo.fork and not include_forks:
            continue
        if repo.size == 0:
            continue
        if repo.private and not include_private:
            continue
        if repo.name == ".github" and not include_dot_github:
            continue
        yield repo


def user_clone(
    user: str,
    to_location: str,
    include_private: bool = True,
    include_forks: bool = False,
    include_dot_github: bool = False,
) -> str:
    g = get_github()
    source_user = g.get_user(user)
    print("Getting repositories :star:")
    repositories = source_user.get_repos()
    repos = list(filter_repos(repositories, include_private, include_forks, include_dot_github))
    random.shuffle(repos)
    for repo in repos:
        kind, repo = fork_or_sync(repo.full_name, to_location, branch=None)
        print(f"{kind}: {repo.full_name}")
        maybe_sleep(g, kind)


# I want a command line interface for this code
# super-clone --include-private --include-forks --include-dot-github <to> <from>+
# use click for the cli
@click.command()
@click.option("--include-private", is_flag=True, default=False)
@click.option("--include-forks", is_flag=True, default=False)
@click.option("--include-dot-github", is_flag=True, default=False)
@click.argument("to")
@click.argument("dest", nargs=-1)
def main(to, dest, include_private, include_forks, include_dot_github):
    g = get_github()
    for frommy in dest:
        if "/" in frommy:
            kind, repo = fork_or_sync(frommy, to, branch=None)
            print(f"{kind}: {repo.full_name}")
            maybe_sleep(g, kind)
        else:
            user_clone(frommy, to, include_private, include_forks, include_dot_github)


if __name__ == "__main__":
    main()
