import json
import os

import yaml


class _Platform:
    def __init__(self, operating_system: str, architecture: str):
        self.operating_system = operating_system
        self.architecture = architecture

    @classmethod
    def from_str(cls, platform_str: str):
        operating_system, architecture = platform_str.split("/")
        return cls(
            operating_system=operating_system,
            architecture=architecture,
        )

    def __repr__(self) -> str:
        return f"_Platform(operating_system={self.operating_system}, architecture={self.architecture})"


class _Image:
    def __init__(self, tag: str, context: str | None, platforms: list[_Platform], extra_args: list[str]):
        self.tag = tag
        self.context = context
        self.platforms = platforms
        self.extra_args = extra_args

    @classmethod
    def from_dict(cls, data):
        return cls(
            tag=data.get("tag"),
            context=data.get("context", None),
            platforms=[_Platform.from_str(p) for p in data.get("platforms", [])],
            extra_args=data.get("extraArgs", []),
        )

    @property
    def architectures(self) -> str:
        return ",".join(platform.architecture for platform in self.platforms)

    def __repr__(self) -> str:
        return f"_Image(tag={self.tag}, context={self.context}, platforms={self.platforms}, extra_args={self.extra_args})"


class _EcrRepository:
    def __init__(self, name: str, branches: list[str], aws_region: str, aws_profile: str, aws_account_id: str):
        self.name = name
        self.branches = branches
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.aws_account_id = aws_account_id

    @classmethod
    def from_dict(cls, data):
        aws_data = data.get("aws", {})
        return cls(
            name=data.get("name"),
            branches=data.get("branches", []),
            aws_region=aws_data.get("region"),
            aws_profile=aws_data.get("profile"),
            aws_account_id=aws_data.get("accountId"),
        )

    @property
    def registry(self) -> str:
        return f"{self.aws_account_id}.dkr.ecr.{self.aws_region}.amazonaws.com"

    def __repr__(self) -> str:
        return (f"_EcrRepository(name={self.name}, branches={self.branches}, aws_region={self.aws_region}, "
                f"aws_profile={self.aws_profile}, aws_account_id={self.aws_account_id})")


class Config:
    def __init__(self, image: _Image, ecr_repositories: list[_EcrRepository]):
        self.image = image
        self.ecr_repositories = ecr_repositories

    @classmethod
    def from_yaml(cls, yaml_path):
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        return cls(
            image=_Image.from_dict(data.get("image", {})),
            ecr_repositories=[_EcrRepository.from_dict(repo) for repo in data.get("ecrRepositories", [])],
        )

    def __repr__(self) -> str:
        return f"Config(image={self.image}, ecr_repositories={self.ecr_repositories})"


def get_all_repos_no_platforms(folders: list[str], branch: str) -> list[dict]:
    tag_suffix = branch.replace("/", "-").strip()
    configs = [(folder, Config.from_yaml(f"./{folder}/config.yaml")) for folder in folders]
    return [
        {
            "name": r.name,
            "folder": folder,
            "tag": f"{config.image.tag}-{tag_suffix}",
            "extra_args": " ".join(config.image.extra_args),
            "context": config.image.context or folder,
            "architecture": config.image.architectures,
            "region": r.aws_region,
            "account_id": r.aws_account_id,
            "registry": r.registry,
        }
        for folder, config in configs
        for r in config.ecr_repositories
        if branch in r.branches  # filter only for current branch
    ]


def get_all_repos(folders: list[str], branch: str) -> list[dict]:
    tag_suffix = branch.replace("/", "-").strip()
    configs = [(folder, Config.from_yaml(f"./{folder}/config.yaml")) for folder in folders]
    return [
        {
            "name": r.name,
            "folder": folder,
            "tag": f"{config.image.tag}-{tag_suffix}",
            "extra_args": " ".join(config.image.extra_args),
            "context": config.image.context or folder,
            "os": p.operating_system,
            "architecture": p.architecture,
            "region": r.aws_region,
            "account_id": r.aws_account_id,
            "registry": r.registry,
        }
        for folder, config in configs
        for r in config.ecr_repositories
        for p in config.image.platforms
        if branch in r.branches  # filter only for current branch
    ]


def main():
    folders = [f for f in os.getenv("FOLDERS", "").split(",") if f]
    branch = os.getenv("BRANCH")

    all_repos_no_platforms = get_all_repos_no_platforms(folders, branch)
    all_repos = get_all_repos(folders, branch)

    with open(os.environ["GITHUB_OUTPUT"], "a") as fd:
        fd.write(f"ECR_REPOS={json.dumps(all_repos, indent=None)}\n")
        fd.write(f"ECR_REPOS_NO_PLATFORMS={json.dumps(all_repos_no_platforms, indent=None)}\n")


if __name__ == "__main__":
    main()
    with open(os.environ["GITHUB_OUTPUT"], "r") as f:
        print(f.read())