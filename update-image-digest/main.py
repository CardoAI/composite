import json
import os
import re

import boto3
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


def update_yaml_file(path, repo_path, tag_path, digest_path):
    yaml_ruamel = YAML()
    with open(path) as f:
        data = yaml_ruamel.load(f)

    repository = get_by_path(data, repo_path)
    tag = get_by_path(data, tag_path)
    digest = get_latest_digest(repository, tag)

    set_by_path(data, digest_path, digest)
    with open(path, "w") as f:
        yaml_ruamel.dump(data, f)


def main():
    config = json.loads(os.environ["CONFIGURATION"])
    for target in config["targets"]:
        update_yaml_file(
            path=target["path"],
            repo_path=target["repositoryPath"],
            tag_path=target["tagPath"],
            digest_path=target["digestPath"],
        )


if __name__ == "__main__":
    main()
