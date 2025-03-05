import os
import random
from collections.abc import Generator
from typing import Optional

import click
from dotenv import load_dotenv
from github import Auth, AuthenticatedUser, Github, Repository, UnknownObjectException
from rich import print as rich_print
from rich.progress import track

from superfork.utils import graceful_calling, warning


def get_repo(nwo: str, g: Optional[Github] = None) -> Optional[Repository.Repository]:
    if not g:
        g = get_github()
    try:
        return g.get_repo(nwo)
    except UnknownObjectException:
        return None


def sync(g: Github, repo: Repository.Repository, without_sleeping: bool, branch: Optional[str] = None) -> dict:
    """
    :calls: `POST /repos/{owner}/{repo}/merge-upstream <https://docs.github.com/en/rest/branches/branches#sync-a-fork-branch-with-the-upstream-repository>`_
    :param branch: string
    :rtype: :class: dict
    :raises: :class:`GithubException` for error status codes
    """
    sleep_time = 0 if without_sleeping else 1
    if not branch:
        branch = repo.default_branch
    post_parameters = {"branch": branch}
    fn = lambda: repo._requester.requestJsonAndCheck("POST", f"{repo.url}/merge-upstream", input=post_parameters)
    with graceful_calling(g, fn, is_mutating=sleep_time):
        headers, data = fn()
        return dict(data)


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
    from_repo: str, to_location: str, syncing: bool, dry_run: bool, without_sleeping: bool, branch: Optional[str] = None
) -> tuple[str, Repository.Repository, Optional[Repository.Repository]]:
    """ """
    (from_user, from_name) = from_repo.split("/")
    parts = to_location.split("/")
    to_user = parts[0]
    if len(parts) == 1:
        to_location = "/".join([to_user, from_name])
    else:
        warning("igorning destination repository name")
    sleep_time = 0 if without_sleeping else 30
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
            sync(g, retrieve_to_location, without_sleeping, branch)
            return ("synced", retrived_from_repo, retrieve_to_location)
        else:
            return ("exists", retrived_from_repo, retrieve_to_location)
    else:
        if dry_run:
            return ("would be forked (dry-run)", retrived_from_repo, None)
        if to_user == user_name:
            fn = lambda: user.create_fork(retrived_from_repo)
            with graceful_calling(g, fn, is_mutating=sleep_time):
                fork = fn()
                return ("forked", retrived_from_repo, fork)
        else:
            org = g.get_organization(to_user)
            fn = lambda: org.create_fork(retrived_from_repo)
            with graceful_calling(g, fn, is_mutating=sleep_time):
                fork = fn()
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
    include_private: bool = True,
    include_forks: bool = False,
    include_dot_github: bool = False,
    syncing: bool = True,
    dry_run: bool = False,
    without_sleeping: bool = False,
) -> None:
    g = get_github()
    try:
        source_user = g.get_user(user)
    except UnknownObjectException:
        warning(f"User or organization `{user}` not found; skipping")
        return
    rich_print(f"Cloning from {source_user.login}")
    repositories = []
    for repo in track(source_user.get_repos(), description="Fetching repositories..."):
        repositories.append(repo)
    rich_print(f"Found {len(repositories)} repositories")
    repos = filter_repos(repositories, include_private, include_forks, include_dot_github)
    filtered_repos = []
    for kind, repo in repos:
        if kind != "keep":
            rich_print(f"{kind}: {repo.full_name}")
        else:
            filtered_repos.append(repo)
    n_repos = len(filtered_repos)
    rich_print(f"Filtered to {n_repos} repositories")
    random.shuffle(filtered_repos)
    for i, repo in enumerate(filtered_repos):
        kind, old_repo, new_repo = fork_or_sync(
            repo.full_name, to_location, syncing, dry_run, without_sleeping, branch=None
        )
        rich_print(f"{i + 1} of {n_repos}. {kind}: {old_repo} -> {new_repo}")


@click.command()
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
@click.option(
    "--without-sleeping",
    is_flag=True,
    default=False,
    show_default=True,
    help="Don't sleep between requests",
)
@click.argument("to")
@click.argument("source", nargs=-1)
def main(
    to: str,
    source: str,
    sync: bool,
    include_private: bool,
    include_forks: bool,
    include_dot_github: bool,
    dry_run: bool,
    without_sleeping: bool = False,
) -> None:
    """
    [TO]: destination user or organization\n
    [SOURCE]: source user or organization, or repository (one or more)

    A valid GITHUB_TOKEN must be set in the environment,
    or in a .env file in the current directory,
    or in a .env file in the user's home directory.

    To get a GITHUB_TOKEN, see https://docs.github.com/en/authentication
    """
    for frommy in source:
        if "/" in frommy:
            kind, old_repo, new_repo = fork_or_sync(frommy, to, sync, dry_run, without_sleeping, branch=None)
            rich_print(f"{kind}: {old_repo} -> {new_repo}")
        else:
            user_clone(
                frommy,
                to,
                include_private,
                include_forks,
                include_dot_github,
                sync,
                dry_run,
                without_sleeping,
            )


if __name__ == "__main__":
    main()
