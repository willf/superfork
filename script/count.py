import re
from collections import Counter


def count_repos(file_path: str) -> None:
    # Regular expression to match the repository names
    repo_pattern = re.compile(r'Repository\(full_name="([^"]+)"\) -> Repository\(full_name="([^"]+)"\)')

    # Counter to keep track of the occurrences of each repository name
    repo_counter = Counter()

    # Read the file and count the occurrences of each repository name
    with open(file_path) as file:
        for line in file:
            match = repo_pattern.match(line.strip())
            if match:
                first_repo = match.group(1)
                user, fname = first_repo.split("/")
                repo_counter[fname.lower()] += 1

    # Print the repository names that occur more than once
    for repo, count in repo_counter.items():
        if count > 1:
            print(f"{repo}: {count}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python count_repos.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    count_repos(file_path)
