import re


def create_markdown_links(file_path: str, output_path: str) -> None:
    # Regular expression to match the repository names
    repo_pattern = re.compile(r'Repository\(full_name="([^"]+)"\) -> Repository\(full_name="([^"]+)"\)')

    # Read the file and create Markdown links
    with open(file_path, "r") as file, open(output_path, "w") as output_file:
        current_org = None
        output_file.write("# Repository Links\n")
        for line in file:
            match = repo_pattern.match(line.strip())
            if match:
                first_repo = match.group(1)
                second_repo = match.group(2)
                first_repo_link = f"[{first_repo}](https://github.com/{first_repo})"
                second_repo_link = f"[{second_repo}](https://github.com/{second_repo})"

                org = first_repo.split("/")[0]
                if org != current_org:
                    if current_org is not None:
                        output_file.write("\n")
                    current_org = org
                    output_file.write(f"## Organization: {current_org}\n")
                    output_file.write("| Source Repository | Destination Repository |\n")
                    output_file.write("|-------------------|------------------------|\n")

                output_file.write(f"| {first_repo_link} | {second_repo_link} |\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python create_markdown_links.py <input_file_path> <output_file_path>")
        sys.exit(1)

    input_file_path = sys.argv[1]
    output_file_path = sys.argv[2]
    create_markdown_links(input_file_path, output_file_path)
