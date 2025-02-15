from github import Issue, IssueComment, PaginatedList, Repository


def process_comments(
    issue: Issue.Issue,
    comments: PaginatedList.PaginatedList[IssueComment.IssueComment],
    repo_1: Repository.Repository,
    repo_2: Repository.Repository,
) -> None:
    pass
