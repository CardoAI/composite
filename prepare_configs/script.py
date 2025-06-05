import os
import yaml
import json
from collections import namedtuple

FOLDER_LIST = os.getenv('FOLDER_LIST', '').split(',')
BRANCH = os.getenv('BRANCH', "")

if not BRANCH:
    raise ValueError("BRANCH environment variable is not set.")


ALL_REPOS = []
ALL_REPOS_NO_PLATFORMS = []

Platform = namedtuple("Platform", ["os", "architecture"])

for folder in FOLDER_LIST:
    folder = folder.strip()
    branch = BRANCH.replace('/', '_')
    with open(f"./{folder}/config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    print(f"{config=}")
    
    config_image = config.get('image', {})

    tag = config_image.get('tag')
    context = config_image.get('context', f"{folder}")
    build_args = " ".join(config_image.get('build_args', []))

    platforms = [
        Platform(*platform.split('/'))
        for platform in config_image.get('platforms', [])]


    architectures = ",".join([platform.architecture for platform in platforms])


    ecr_repositories = config.get('ecrRepositories', [])
    
    # filter only for current branch
    ecr_repositories = [
        repo for repo in ecr_repositories
        if branch in repo.get('branch', [])
    ]
    
    
    for repo in ecr_repositories:
        aws = repo.get('aws', {})
        region = aws.get('region')
        account_id = aws.get('account_id')
        print(f"{repo=}")

        ALL_REPOS_NO_PLATFORMS.append({
            'name': repo.get("name"),
            "folder": folder,
            "tag": tag,
            "build_args": build_args,
            "context": context,
            "architecture": architectures,
            "region": aws.get('region'),
            "account_id": aws.get('account_id'),
            "registry": f"{account_id}.dkr.ecr.{region}.amazonaws.com"
        })
        for platform in platforms:
            ALL_REPOS.append({
                'name': repo.get("name"),
                "folder": folder,
                "tag": tag,
                "build_args": build_args,
                "context": context,
                "os": platform.os,
                "architecture": platform.architecture,
                "region": aws.get('region'),
                "account_id": aws.get('account_id'),
                "registry": f"{account_id}.dkr.ecr.{region}.amazonaws.com"
            })

with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    print(f"ALL_REPOS={json.dumps(ALL_REPOS, indent=0)}", file=f)
    print(f"ALL_REPOS_NO_PLATFORMS={json.dumps(ALL_REPOS_NO_PLATFORMS, indent=0)}", file=f)
    
with open(os.environ["GITHUB_OUTPUT"], "r") as f:
    print(f.read())