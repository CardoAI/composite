from main import get_all_configs, get_all_images, get_all_manifests


def test_get_all_manifests_main():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "main")
    result = get_all_manifests(repo_configs)
    expected = [
        {
            "account_id": "980921757922",
            "region": "us-east-2",
            "repository": "cardoai-us-ar-ecr-repository-test",
            "tag": "backend-main",
            "tag_suffixes": ["amd64", "arm64"]
        },
        {
            "account_id": "861208160487",
            "region": "eu-central-1",
            "repository": "cardoai-eu-ar-ecr-repository-test",
            "tag": "backend-main",
            "tag_suffixes": ["amd64", "arm64"]
        },
        {
            "account_id": "980921757922",
            "region": "us-east-2",
            "repository": "cardoai-us-ar-ecr-repository-test",
            "tag": "celery-main",
            "tag_suffixes": ["amd64", "arm64"]
        },
        {
            "account_id": "861208160487",
            "region": "eu-central-1",
            "repository": "cardoai-eu-ar-ecr-repository-test",
            "tag": "celery-main",
            "tag_suffixes": ["amd64", "arm64"]
        },
    ]
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_manifests_feat_test():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "feat/test")
    result = get_all_manifests(repo_configs)
    expected = [
        {
            "account_id": "861208160487",
            "region": "eu-central-1",
            "repository": "cardoai-eu-ar-ecr-repository-test",
            "tag": "backend-feat-test",
            "tag_suffixes": ["amd64", "arm64"]
        },
        {
            "account_id": "861208160487",
            "region": "eu-central-1",
            "repository": "cardoai-eu-ar-ecr-repository-test",
            "tag": "celery-feat-test",
            "tag_suffixes": ["amd64", "arm64"]
        },
    ]
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_manifests_no_match():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "no-match")
    result = get_all_manifests(repo_configs)
    expected = []
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_images_main():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "main")
    result = get_all_images(repo_configs)
    expected = [
        {
            "folder": "test/backend",
            "context": ".",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "platform": "linux/amd64",
            "architecture": "amd64",
            "tag": "backend-main-amd64",
            "repositories": [
                {
                    "name": "cardoai-us-ar-ecr-repository-test",
                    "region": "us-east-2",
                    "account_id": "980921757922",
                },
                {
                    "name": "cardoai-eu-ar-ecr-repository-test",
                    "region": "eu-central-1",
                    "account_id": "861208160487",
                }
            ]
        },
        {
            "folder": "test/backend",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": ".",
            "platform": "linux/arm64",
            "architecture": "arm64",
            "tag": "backend-main-arm64",
            "repositories": [
                {
                    "name": "cardoai-us-ar-ecr-repository-test",
                    "region": "us-east-2",
                    "account_id": "980921757922",
                },
                {
                    "name": "cardoai-eu-ar-ecr-repository-test",
                    "region": "eu-central-1",
                    "account_id": "861208160487",
                }
            ]
        },
        {
            "folder": "test/celery",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": ".",
            "platform": "linux/amd64",
            "architecture": "amd64",
            "tag": "celery-main-amd64",
            "repositories": [
                {
                    "name": "cardoai-us-ar-ecr-repository-test",
                    "region": "us-east-2",
                    "account_id": "980921757922",
                },
                {
                    "name": "cardoai-eu-ar-ecr-repository-test",
                    "region": "eu-central-1",
                    "account_id": "861208160487",
                }
            ]
        },
        {
            "folder": "test/celery",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": ".",
            "platform": "linux/arm64",
            "architecture": "arm64",
            "tag": "celery-main-arm64",
            "repositories": [
                {
                    "name": "cardoai-us-ar-ecr-repository-test",
                    "region": "us-east-2",
                    "account_id": "980921757922",
                },
                {
                    "name": "cardoai-eu-ar-ecr-repository-test",
                    "region": "eu-central-1",
                    "account_id": "861208160487",
                }
            ]
        },
    ]
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_images_feat_test():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "feat/test")
    result = get_all_images(repo_configs)
    expected = [
        {
            "folder": "test/backend",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": ".",
            "platform": "linux/amd64",
            "architecture": "amd64",
            "tag": "backend-feat-test-amd64",
            "repositories": [
                {
                    "name": "cardoai-eu-ar-ecr-repository-test",
                    "region": "eu-central-1",
                    "account_id": "861208160487",
                }
            ]
        },
        {
            "folder": "test/backend",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": ".",
            "platform": "linux/arm64",
            "architecture": "arm64",
            "tag": "backend-feat-test-arm64",
            "repositories": [
                {
                    "name": "cardoai-eu-ar-ecr-repository-test",
                    "region": "eu-central-1",
                    "account_id": "861208160487",
                }
            ]
        },
        {
            "folder": "test/celery",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": ".",
            "platform": "linux/amd64",
            "architecture": "amd64",
            "tag": "celery-feat-test-amd64",
            "repositories": [
                {
                    "name": "cardoai-eu-ar-ecr-repository-test",
                    "region": "eu-central-1",
                    "account_id": "861208160487",
                }
            ]
        },
        {
            "folder": "test/celery",
            "extra_args": "--build-arg BASE_IMAGE=861208160487.dkr.ecr.eu-central-1.amazonaws.com/cardoai-eu-ar-ecr-repository-test:1.0.0-base",
            "context": ".",
            "platform": "linux/arm64",
            "architecture": "arm64",
            "tag": "celery-feat-test-arm64",
            "repositories": [
                {
                    "name": "cardoai-eu-ar-ecr-repository-test",
                    "region": "eu-central-1",
                    "account_id": "861208160487",
                }
            ]
        },
    ]
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_all_images_no_match():
    folders = ["test/backend", "test/celery"]
    repo_configs = get_all_configs(folders, "no-match")
    result = get_all_images(repo_configs)
    expected = []
    assert result == expected, f"Expected {expected}, but got {result}"
