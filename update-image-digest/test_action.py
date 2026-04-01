import yaml
from main import update_yaml_file
import os

CONFIGURATION = """
  - name: ag
    branch: main
    targets:
      - name: global
        path: test/clusters/staging-cluster/equalizer/ag/image-values.yaml
        repositoryPath: global.image.repository
        tagPath: global.image.tag
        digestPath: global.image.digest
      - name: backend
        path: test/clusters/staging-cluster/equalizer/ag/image-values.yaml
        repositoryPath: backend.image.repository
        tagPath: backend.image.tag
        digestPath: backend.image.digest

  - name: kkr
    branch: test
    targets:
      - name: backend
        path: test/clusters/staging-cluster/equalizer/kkr/kustomization.yaml
        repositoryPath: images[0].newName
        tagPath: images[0].newTag
        digestPath: images[0].digest

  - name: opyn
    branch: main
    targets:
      - name: backend
        path: test/clusters/staging-cluster/equalizer/opyn/kustomization.yaml
        repositoryPath: images[0].newName
        tagPath: images[0].newTag
        digestPath: images[0].digest
      - name: frontend
        path: test/clusters/staging-cluster/equalizer/opyn/kustomization.yaml
        repositoryPath: images[1].newName
        tagPath: images[1].newTag
        digestPath: images[1].digest
      - name: backend
        path: test/clusters/staging-cluster/equalizer/opyn/kustomization.yaml
        repositoryPath: images[2].newName
        tagPath: images[2].newTag
        digestPath: images[2].digest
"""


def test_update_yaml_file():
    config = yaml.safe_load(CONFIGURATION)
    current_branch = "main"
    os.environ["AWS_PROFILE"] = "cardoai-eu-swe"
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
            )
