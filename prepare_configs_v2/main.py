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


def get_all_configs(folders: list[str], branch: str) -> list[dict]:
    tag_suffix = branch.replace("/", "-").strip()
    configs = [(folder, Config.from_yaml(f"./{folder}/config.yaml")) for folder in folders]
    return [
        {
            "name": r.name,
            "folder": folder,
            "tag": f"{config.image.tag}-{tag_suffix}",
            "extra_args": " ".join(config.image.extra_args),
            "context": config.image.context or folder,
            "platforms": config.image.platforms,
            "region": r.aws_region,
            "account_id": r.aws_account_id,
            "registry": r.registry,
        }
        for folder, config in configs
        for r in config.ecr_repositories
        if branch in r.branches  # filter only for current branch
    ]


def get_all_images(repo_configs: list[dict]) -> list[dict]:
    return [
        {k: v for k, v in c.items() if k != "platforms"} | {
            "os": p.operating_system,
            "architecture": p.architecture,
        } for c in repo_configs for p in c["platforms"]
    ]

def get_all_manifests(repo_configs: list[dict]) -> list[dict]:
    return [
        {k: v for k, v in c.items() if k != "platforms"} | {
            "tag_suffixes": ",".join(p.architecture for p in c["platforms"])
        }
        for c in repo_configs
    ]


def main():
    folders = [folder for folder in os.getenv("FOLDERS", "").split(",") if folder]
    branch = os.getenv("BRANCH")
    repo_configs = get_all_configs(folders, branch)
    all_images = get_all_images(repo_configs)
    all_manifests = get_all_manifests(repo_configs)

    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_output:
        gh_output.write(f"ECR_IMAGES={json.dumps(all_images, indent=None)}\n")
        gh_output.write(f"ECR_IMAGE_MANIFESTS={json.dumps(all_manifests, indent=None)}\n")
    with open(os.environ["GITHUB_OUTPUT"], "r") as gh_output:
        print(gh_output.read())


if __name__ == "__main__":
    main()
