import os
import re

import boto3
import yaml
from ruamel.yaml import YAML

OVERRIDES_PATH = ".ci/tag-validation-overrides.yaml"


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
        imageIds=[{"imageTag": tag}],
    )
    return response["imageDetails"][0]["imageDigest"]


def branch_to_tag_suffix(branch):
    if branch is None:
        raise ValueError("Branch validation failed: current branch is empty")

    normalized_branch = branch.strip()
    if not normalized_branch:
        raise ValueError("Branch validation failed: current branch is empty")

    return normalized_branch.replace("/", "-")


def load_tag_validation_overrides(path=OVERRIDES_PATH):
    if not os.path.exists(path):
        return {}

    try:
        with open(path) as f:
            parsed = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed tag validation overrides file '{path}': {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Malformed tag validation overrides file '{path}': expected top-level mapping"
        )

    branches = parsed.get("branches")
    if branches is None:
        return {}

    if not isinstance(branches, dict):
        raise ValueError(
            f"Malformed tag validation overrides file '{path}': 'branches' must be a mapping"
        )

    overrides = {}
    for branch_name, suffixes in branches.items():
        if not isinstance(branch_name, str):
            raise ValueError(
                f"Malformed tag validation overrides file '{path}': branch keys must be strings"
            )

        normalized_branch_name = branch_name.strip()
        if not normalized_branch_name:
            raise ValueError(
                f"Malformed tag validation overrides file '{path}': branch names cannot be empty"
            )

        if not isinstance(suffixes, list):
            raise ValueError(
                f"Malformed tag validation overrides file '{path}': branch '{normalized_branch_name}' must map to a list"
            )

        cleaned_suffixes = []
        for suffix in suffixes:
            if not isinstance(suffix, str):
                raise ValueError(
                    f"Malformed tag validation overrides file '{path}': branch '{normalized_branch_name}' has non-string suffix"
                )

            normalized_suffix = suffix.strip().replace("/", "-").lstrip("-")
            if not normalized_suffix:
                raise ValueError(
                    f"Malformed tag validation overrides file '{path}': branch '{normalized_branch_name}' has empty suffix"
                )

            cleaned_suffixes.append(normalized_suffix)

        overrides[normalized_branch_name] = cleaned_suffixes

    print(f"Loaded tag validation overrides from '{path}'")
    return overrides


def validate_tag_for_branch(tag, branch, override_suffixes_by_branch=None):
    normalized_branch_suffix = branch_to_tag_suffix(branch)
    allowed_suffixes = [normalized_branch_suffix]

    if override_suffixes_by_branch:
        current_branch = branch.strip()
        extra_suffixes = override_suffixes_by_branch.get(current_branch, [])
        if extra_suffixes:
            print(
                f"Tag validation override active for branch '{current_branch}': "
                f"additional allowed suffixes={extra_suffixes}"
            )
            allowed_suffixes.extend(extra_suffixes)

    if any(tag.endswith(f"-{suffix}") for suffix in allowed_suffixes):
        return

    expected = [f"-{suffix}" for suffix in allowed_suffixes]
    raise ValueError(
        f"Tag validation failed for branch '{branch}': expected tag ending with one of {expected}, found '{tag}'"
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


def update_yaml_file(
    path,
    repo_path,
    tag_path,
    digest_path,
    current_branch,
    override_suffixes_by_branch=None,
):
    yaml_ruamel = YAML()
    with open(path) as f:
        data = yaml_ruamel.load(f)

    repository = get_by_path(data, repo_path)
    tag = get_by_path(data, tag_path)
    validate_tag_for_branch(tag, current_branch, override_suffixes_by_branch)
    digest = get_latest_digest(repository, tag)

    set_by_path(data, digest_path, digest)
    with open(path, "w") as f:
        yaml_ruamel.dump(data, f)


def main():
    current_branch = os.environ.get("GITHUB_BRANCH")
    overrides = load_tag_validation_overrides()
    config = yaml.safe_load(os.environ["CONFIGURATION"])

    for c in config:
        if c["branch"] != current_branch:
            continue
        print(f"Updating configuration {c['name']} for branch: {c['branch']}")
        for target in c["targets"]:
            update_yaml_file(
                path=target["path"],
                repo_path=target["repositoryPath"],
                tag_path=target["tagPath"],
                digest_path=target["digestPath"],
                current_branch=current_branch,
                override_suffixes_by_branch=overrides,
            )


if __name__ == "__main__":
    main()
