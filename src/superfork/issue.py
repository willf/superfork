from github import Issue, Repository, Github

from superfork.comment import process_comments
from superfork.utils import (
    create_repo_replace_function,
    create_source_function,
    maybe_sleep,
    replace_at_mentions,
    text_pipeline,
)

# Text processing


# Issue processing


def process_issue(issue: Issue.Issue, repo_1: Repository.Repository, repo_2: Repository.Repository) -> Issue.Issue:
    old_title = issue.title or ""
    old_body = issue.body or ""
    title_fns = [
        create_repo_replace_function(repo_1.full_name, repo_2.full_name),
    ]
    created_at_str = issue.created_at.strftime("%Y-%m-%d")
    body_fns = [
        *title_fns,
        replace_at_mentions,
        create_source_function(old_body, repo_1.owner.login, created_at_str, issue.html_url),
    ]
    print(f"Processing issue: {old_title} with {old_body}")
    new_title = text_pipeline(old_title, title_fns)
    new_body = text_pipeline(old_body, body_fns)
    new_issue = repo_2.create_issue(
        title=new_title,
        body=new_body,
        labels=issue.labels,
    )
    # maybe_sleep(repo_1._requester, "issue")

    process_comments(new_issue, issue.get_comments(), repo_1, repo_2)
    return new_issue
