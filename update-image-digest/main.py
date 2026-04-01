import os
import re

import boto3
import yaml
from ruamel.yaml import YAML


def get_latest_digest(repository, tag):
    pattern = r"(?P<account_id>\d+)\.dkr\.ecr\.(?P<region>[a-z0-9-]+)\.amazonaws\.com/(?P<repo_name>.+)"
    match = re.match(pattern, repository)
    if not match:
        raise ValueError("Invalid ECR repository URI format")

    account_id = match.group("account_id")
    region = match.group("region")
    repo_name = match.group("repo_name")

    ecr = boto3.client("ecr", region_name=region)
    response = ecr.describe_images(
        registryId=account_id,
        repositoryName=repo_name,
        imageIds=[{"imageTag": tag}]
    )
    return response["imageDetails"][0]["imageDigest"]


def branch_to_tag_suffix(branch):
    if branch is None:
        raise ValueError("Branch validation failed: current branch is empty")

    normalized_branch = branch.strip()
    if not normalized_branch:
        raise ValueError("Branch validation failed: current branch is empty")

    return normalized_branch.replace("/", "-")


def validate_tag_for_branch(tag, branch):
    normalized_branch_suffix = branch_to_tag_suffix(branch)

    if not tag.endswith(f"-{normalized_branch_suffix}"):
        raise ValueError(
            f"Tag validation failed for branch '{branch}': expected tag ending with "
            f"'-{normalized_branch_suffix}', found '{tag}'"
        )


# Traverse to repository, tag, and digest
def get_by_path(obj, path):
    for part in path.split("."):
        if part.endswith("]"):
            key, idx = part[:-1].split("[")
            obj = obj[key][int(idx)]
        else:
            obj = obj[part]
    return obj


# Set digest
def set_by_path(obj, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        if part.endswith("]"):
            key, idx = part[:-1].split("[")
            obj = obj[key][int(idx)]
        else:
            obj = obj[part]
    last = parts[-1]
    if last.endswith("]"):
        key, idx = last[:-1].split("[")
        obj[key][int(idx)] = value
    else:
        obj[last] = value


def update_yaml_file(path, repo_path, tag_path, digest_path, current_branch):
    yaml_ruamel = YAML()
    with open(path) as f:
        data = yaml_ruamel.load(f)

    repository = get_by_path(data, repo_path)
    tag = get_by_path(data, tag_path)
    validate_tag_for_branch(tag, current_branch)
    digest = get_latest_digest(repository, tag)

    set_by_path(data, digest_path, digest)
    with open(path, "w") as f:
        yaml_ruamel.dump(data, f)


def main():
    current_branch = os.environ.get("GITHUB_BRANCH")
    config = yaml.safe_load(os.environ["CONFIGURATION"])
    processed = False
    for c in config:
        if c["branch"] != current_branch:
            continue
        processed = True
        print(f"Updating configuration {c['name']} for branch: {c['branch']}")
        for target in c["targets"]:
            update_yaml_file(
                path=target["path"],
                repo_path=target["repositoryPath"],
                tag_path=target["tagPath"],
                digest_path=target["digestPath"],
                current_branch=current_branch,
            )
    if not processed:
        raise ValueError(
            f"No configuration entry matched the current branch '{current_branch}'. "
            "Check your workflow configuration."
        )


if __name__ == "__main__":
    main()
