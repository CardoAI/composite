from main import get_all_configs, get_all_images, get_all_manifests


def test_get_all_repos_no_platforms_main():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "main")
    result = get_all_manifests(repo_configs)
    expected = [
        {
            "name": "cardoai-us-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "tag_suffixes": "amd64,arm64",
            "region": "us-east-2",
            "account_id": "980921757922",
            "registry": "980921757922.dkr.ecr.us-east-2.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "tag_suffixes": "amd64,arm64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
        {
            "name": "cardoai-us-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "tag_suffixes": "amd64,arm64",
            "region": "us-east-2",
            "account_id": "980921757922",
            "registry": "980921757922.dkr.ecr.us-east-2.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "tag_suffixes": "amd64,arm64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        }
    ]
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_repos_no_platforms_feat_test():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "feat/test")
    result = get_all_manifests(repo_configs)
    expected = [
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-feat-test",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "tag_suffixes": "amd64,arm64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-feat-test",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "tag_suffixes": "amd64,arm64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        }
    ]
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_repos_no_platforms_no_match():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "no-match")
    result = get_all_manifests(repo_configs)
    expected = []
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_repos_main():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "main")
    result = get_all_images(repo_configs)
    expected = [
        {
            "name": "cardoai-us-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "os": "linux",
            "architecture": "amd64",
            "region": "us-east-2",
            "account_id": "980921757922",
            "registry": "980921757922.dkr.ecr.us-east-2.amazonaws.com"
        },
        {
            "name": "cardoai-us-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "os": "linux",
            "architecture": "arm64",
            "region": "us-east-2",
            "account_id": "980921757922",
            "registry": "980921757922.dkr.ecr.us-east-2.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "os": "linux",
            "architecture": "amd64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "os": "linux",
            "architecture": "arm64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
        {
            "name": "cardoai-us-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "os": "linux",
            "architecture": "amd64",
            "region": "us-east-2",
            "account_id": "980921757922",
            "registry": "980921757922.dkr.ecr.us-east-2.amazonaws.com"
        },
        {
            "name": "cardoai-us-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "os": "linux",
            "architecture": "arm64",
            "region": "us-east-2",
            "account_id": "980921757922",
            "registry": "980921757922.dkr.ecr.us-east-2.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "os": "linux",
            "architecture": "amd64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-main",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "os": "linux",
            "architecture": "arm64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
    ]
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_repos_feat_test():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "feat/test")
    result = get_all_images(repo_configs)
    expected = [
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-feat-test",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "os": "linux",
            "architecture": "amd64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/backend",
            "tag": "backend-feat-test",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/backend",
            "os": "linux",
            "architecture": "arm64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-feat-test",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "os": "linux",
            "architecture": "amd64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
        {
            "name": "cardoai-eu-ar-ecr-repository-test",
            "folder": "test/celery",
            "tag": "backend-feat-test",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": "test/celery",
            "os": "linux",
            "architecture": "arm64",
            "region": "eu-central-1",
            "account_id": "861208160487",
            "registry": "861208160487.dkr.ecr.eu-central-1.amazonaws.com"
        },
    ]
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_repos_no_match():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "no-match")
    result = get_all_images(repo_configs)
    expected = []
    assert result == expected, f"Expected {expected}, but got {result}"
