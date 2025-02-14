import os
import random
from collections.abc import Generator
from typing import Optional

import click
from dotenv import load_dotenv
from github import Auth, AuthenticatedUser, Github, Repository, UnknownObjectException
from rich import print as rich_print
from rich.progress import track

from superfork.issue import process_issue
from superfork.utils import maybe_sleep, sleep_until_reset, warning


def get_repo(nwo: str, g: Optional[Github] = None) -> Optional[Repository.Repository]:
    if not g:
        g = get_github()
    try:
        return g.get_repo(nwo)
    except UnknownObjectException:
        return None


def sync(repo: Repository.Repository, branch: Optional[str] = None) -> dict:
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
    return dict(data)


def set_has_issues(repo: Repository.Repository, has_issues: bool) -> None:
    """
    :calls: `PATCH /repos/{owner}/{repo} <https://docs.github.com/en/rest/reference/repos#update-a-repository>`_
    :param has_issues: bool
    :rtype: None
    :raises: :class:`GithubException`
    """
    patch_parameters = {"has_issues": has_issues}
    headers, data = repo._requester.requestJsonAndCheck("PATCH", repo.url, input=patch_parameters)
    rich_print(headers, data)
    return None


class RepositoryNotFoundException(Exception):
    def __init__(self, repo: str) -> None:
        super().__init__(f"Repository '{repo}' not found")


class NotAuthenticatedUserError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Not authenticated user")


class GitHubTokenNotFoundError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("GITHUB_TOKEN not found")


def get_github(token: Optional[str] = None) -> Github:
    if not token:
        load_dotenv()
        token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GitHubTokenNotFoundError()
    auth = Auth.Token(token)
    g = Github(auth=auth)
    return g


def get_authed_user(g: Optional[Github] = None, token: Optional[str] = None) -> AuthenticatedUser.AuthenticatedUser:
    if not g:
        raise NotAuthenticatedUserError()
    user = g.get_user()
    if type(user) is AuthenticatedUser.AuthenticatedUser:
        return user
    else:
        raise NotAuthenticatedUserError()


def fork_or_sync(
    from_repo: str, to_location: str, syncing: bool, dry_run: bool, branch: Optional[str] = None
) -> tuple[str, Repository.Repository, Repository.Repository]:
    """ """
    (from_user, from_name) = from_repo.split("/")
    parts = to_location.split("/")
    to_user = parts[0]
    if len(parts) == 1:
        to_location = "/".join([to_user, from_name])
    else:
        warning("igorning destination repository name")
    g = get_github()
    user = get_authed_user(g)
    user_name = user.login
    retrived_from_repo = get_repo(from_repo, g)
    if not retrived_from_repo:
        raise RepositoryNotFoundException(from_repo)
    retrieve_to_location = get_repo(to_location, g)
    if retrieve_to_location:
        if dry_run:
            return ("already exists (dry-run)", retrived_from_repo, retrieve_to_location)
        if syncing:
            sync(retrieve_to_location, branch)
            return ("synced", retrived_from_repo, retrieve_to_location)
        else:
            return ("exists", retrived_from_repo, retrieve_to_location)
    else:
        if dry_run:
            return ("would be forked (dry-run)", retrived_from_repo, None)
        if to_user == user_name:
            try:
                fork = user.create_fork(retrived_from_repo)
                return ("forked", retrived_from_repo, fork)
            except Exception as e:
                warning(f"Failed to fork {from_repo} to {to_location}: {e}")
                sleep_until_reset(g)
                fork = user.create_fork(retrived_from_repo)
                return ("forked", retrived_from_repo, fork)
        else:
            org = g.get_organization(to_user)
            try:
                fork = org.create_fork(retrived_from_repo)
                return ("forked", retrived_from_repo, fork)
            except Exception as e:
                warning(f"Failed to fork {from_repo} to {to_location}: {e}")
                sleep_until_reset(g)
                fork = org.create_fork(retrived_from_repo)
                return ("forked", retrived_from_repo, fork)


def filter_repos(
    repos: list[Repository.Repository],
    include_private: bool = True,
    include_forks: bool = False,
    include_dot_github: bool = False,
) -> Generator[tuple[str, Repository.Repository], None, None]:
    for repo in repos:
        if repo.fork and not include_forks:
            yield ("Skipping forked repository", repo)
        elif repo.size == 0:
            yield ("Skipping empty repository", repo)
        elif repo.private and not include_private:
            yield ("Skipping private repository", repo)
        elif repo.name == ".github" and not include_dot_github:
            yield ("Skipping .github repository", repo)
        else:
            yield ("keep", repo)


def user_clone(
    user: str,
    to_location: str,
    include_issues: bool = False,
    include_private: bool = True,
    include_forks: bool = False,
    include_dot_github: bool = False,
    syncing: bool = True,
    dry_run: bool = False,
) -> None:
    g = get_github()
    try:
        source_user = g.get_user(user)
    except UnknownObjectException:
        warning(f"User or organization `{user}` not found; skipping")
        return ("ignore", None, None)
    rich_print(f"Cloning from {source_user.login}")
    repositories = []
    for repo in track(source_user.get_repos(), description="Fetching repositories..."):
        repositories.append(repo)
    rich_print(f"Found {len(repositories)} repositories")
    repos = filter_repos(repositories, include_private, include_forks, include_dot_github)
    filtered_repos = []
    for repo in repos:
        if repo[0] != "keep":
            rich_print(f"{repo[0]}: {repo[1].full_name}")
        else:
            filtered_repos.append(repo[1])
    rich_print(f"Filtered to {len(filtered_repos)} repositories")
    random.shuffle(filtered_repos)
    for repo in filtered_repos:
        kind, old_repo, new_repo = fork_or_sync(repo.full_name, to_location, syncing, dry_run, branch=None)  # type: ignore  # noqa: PGH003
        rich_print(f"{kind}: {old_repo} -> {new_repo}")
        maybe_sleep(g, kind, dry_run)
        if include_issues and not dry_run:
            rich_print("TODO: clone issues")


# I want a command line interface for this code
# super-clone --include-private --include-forks --include-dot-github <to> <from>+
# use click for the cli
@click.command()
@click.option(
    "--include-issues",
    is_flag=True,
    default=False,
    show_default=True,
    help="Include issues, pull requests, and comments",
)
@click.option(
    "--sync/--no-sync", is_flag=True, default=True, show_default=True, help="Sync when repository already exists"
)
@click.option("--include-private", is_flag=True, default=False, show_default=True, help="Include private repositories")
@click.option(
    "--include-forks",
    is_flag=True,
    default=False,
    show_default=True,
    help="Include repositories which were originally forked",
)
@click.option(
    "--include-dot-github", is_flag=True, default=False, show_default=True, help="Include .github repository if found"
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    show_default=True,
    help="Don't actually do anything, but check status of repositories",
)
@click.argument("to")
@click.argument("source", nargs=-1)
def main(
    to: str,
    source: str,
    sync: bool,
    include_issues: bool,
    include_private: bool,
    include_forks: bool,
    include_dot_github: bool,
    dry_run: bool,
) -> None:
    """
    [TO]: destination user or organization\n
    [SOURCE]: source user or organization, or repository (one or more)

    A valid GITHUB_TOKEN must be set in the environment,
    or in a .env file in the current directory,
    or in a .env file in the user's home directory.

    To get a GITHUB_TOKEN, see https://docs.github.com/en/authentication
    """
    g = get_github()
    for frommy in source:
        if "/" in frommy:
            kind, old_repo, new_repo = fork_or_sync(frommy, to, sync, dry_run, branch=None)
            rich_print(f"{kind}: {old_repo} -> {new_repo}")
            maybe_sleep(g, kind, dry_run)
            if include_issues and kind == "forked" and not dry_run:
                set_has_issues(new_repo, True)
                frommy_repo = get_repo(frommy)
                issues = frommy_repo.get_issues(state="all")
                for issue in issues:
                    process_issue(issue, frommy_repo, new_repo)
                    # rich_print(f"TODO: transfer{issue}")
        else:
            user_clone(frommy, to, include_issues, include_private, include_forks, include_dot_github, sync, dry_run)


if __name__ == "__main__":
    main()
