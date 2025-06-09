import json
import os

import yaml


class _Image:
    def __init__(self, tag: str, context: str | None, platforms: list[str], extra_args: list[str]):
        self.tag = tag
        self.context = context
        self.platforms = platforms
        self.extra_args = extra_args

    @classmethod
    def from_dict(cls, data):
        return cls(
            tag=data.get("tag"),
            context=data.get("context", "."),
            platforms=data.get("platforms", []),
            extra_args=data.get("extraArgs", []),
        )

    def __repr__(self) -> str:
        return f"_Image(tag={self.tag}, context={self.context}, platforms={self.platforms}, extra_args={self.extra_args})"


class _EcrRepository:
    def __init__(self, name: str, branches: list[str], aws_region: str, aws_account_id: str):
        self.name = name
        self.branches = branches
        self.aws_region = aws_region
        self.aws_account_id = aws_account_id

    @classmethod
    def from_dict(cls, data):
        aws_data = data.get("aws", {})
        return cls(
            name=data.get("name"),
            branches=data.get("branches", []),
            aws_region=aws_data.get("region"),
            aws_account_id=aws_data.get("accountId"),
        )

    def __repr__(self) -> str:
        return (f"_EcrRepository(name={self.name}, branches={self.branches}, aws_region={self.aws_region}, "
                f"aws_account_id={self.aws_account_id})")


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
    all_configs = [
        {
            "folder": folder,
            "tag": f"{config.image.tag}-{tag_suffix}",
            "extra_args": " ".join(config.image.extra_args),
            "context": config.image.context or folder,
            "platforms": config.image.platforms,
            "ecr_repositories": [r for r in config.ecr_repositories if branch in r.branches], # filter only for current branch
        }
        for folder, config in configs
    ]
    return [c for c in all_configs if c["ecr_repositories"]]


def get_all_images(configs: list[dict]) -> list[dict]:
    return [
        {
            "folder": c["folder"],
            "tag": f"{c['tag']}-{p.split('/')[-1]}",
            "extra_args": c["extra_args"],
            "context": c["context"],
            "platform": p,
            "architecture": p.split("/")[-1],
            "repositories": [{
                "name": r.name,
                "region": r.aws_region,
                "account_id": r.aws_account_id,
            } for r in c["ecr_repositories"]],
        }
        for c in configs
        for p in c["platforms"]
    ]

def get_all_manifests(configs: list[dict]) -> list[dict]:
    return [
        {
            "account_id": r.aws_account_id,
            "region": r.aws_region,
            "repository": r.name,
            "tag": c["tag"],
            "tag_suffixes": [p.split("/")[-1] for p in c["platforms"]],
        }
        for c in configs
        for r in c["ecr_repositories"]
    ]


def main():
    folders = [folder for folder in os.getenv("FOLDERS", "").split(",") if folder]
    branch = os.getenv("BRANCH")
    configs = get_all_configs(folders, branch)
    all_images = get_all_images(configs)
    all_manifests = get_all_manifests(configs)

    with open(os.environ["GITHUB_OUTPUT"], "a") as gh_output:
        gh_output.write(f"IMAGES={json.dumps(all_images, indent=None)}\n")
        gh_output.write(f"IMAGE_MANIFESTS={json.dumps(all_manifests, indent=None)}\n")
    with open(os.environ["GITHUB_OUTPUT"], "r") as gh_output:
        print(gh_output.read())


if __name__ == "__main__":
    main()
