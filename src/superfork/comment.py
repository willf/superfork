from github import Issue, IssueComment, PaginatedList, Repository

from superfork.utils import (
    create_repo_replace_function,
    create_source_function,
    replace_at_mentions,
    text_pipeline,
)


def process_comments(
    issue: Issue.Issue,
    comments: PaginatedList.PaginatedList[IssueComment.IssueComment],
    repo_1: Repository.Repository,
    repo_2: Repository.Repository,
) -> None:
    pass
