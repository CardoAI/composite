#!/usr/bin/env bash
set -euo pipefail

: "${TRIVY_VERSION:?Trivy version is required}"
: "${REPORT_DIRECTORY:?Report directory is required}"
: "${RUNNER_TEMP:?Runner temporary directory is required}"
: "${GITHUB_PATH:?GitHub path file is required}"
: "${GITHUB_ACTION_PATH:?GitHub action directory is required}"

case "${RUNNER_OS:?}" in
    Linux|macOS) release_os="$RUNNER_OS"; extension=tar.gz; executable=trivy ;;
    Windows) release_os=windows; extension=zip; executable=trivy.exe ;;
    *) echo "::error::Unsupported Trivy runner OS: $RUNNER_OS"; exit 1 ;;
esac
case "${RUNNER_ARCH:?}" in
    X64) release_arch=64bit ;;
    ARM64) release_arch=ARM64 ;;
    ARM) release_arch=ARM ;;
    X86) release_arch=32bit ;;
    *) echo "::error::Unsupported Trivy runner architecture: $RUNNER_ARCH"; exit 1 ;;
esac

asset="trivy_${TRIVY_VERSION}_${release_os}-${release_arch}.${extension}"
expected_checksum=$(awk -v asset="$asset" '$2 == asset {print $1}' "${GITHUB_ACTION_PATH}/trivy-checksums.txt")
if [[ ! "$expected_checksum" =~ ^[0-9a-f]{64}$ ]]; then
    echo "::error::No pinned checksum for Trivy release asset: $asset"
    exit 1
fi

download_directory="${RUNNER_TEMP}/frontend-trivy-download"
mkdir -p -- "$download_directory"
archive="${download_directory}/${asset}"
trap 'rm -f -- "${archive}.part"' EXIT
if [[ ! -f "$archive" ]]; then
    url="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/${asset}"
    echo "Downloading Trivy from $url"
    if curl --fail --silent --show-error --location \
        --proto '=https' --proto-redir '=https' \
        --retry 3 --retry-all-errors --retry-delay 2 --retry-max-time 180 \
        --connect-timeout 15 --max-time 120 \
        --output "${archive}.part" "$url"; then
        mv -- "${archive}.part" "$archive"
    else
        status=$?
        echo "::error::Unable to download Trivy from $url (curl exit $status)."
        exit "$status"
    fi
fi

# Verify cache hits too; never extract or execute an unverified archive.
if command -v sha256sum >/dev/null 2>&1; then
    actual_checksum=$(sha256sum < "$archive")
else
    actual_checksum=$(shasum -a 256 < "$archive")
fi
if [[ "${actual_checksum%% *}" != "$expected_checksum" ]]; then
    echo "::error::Trivy release archive checksum mismatch: $asset"
    exit 1
fi

install_directory="${REPORT_DIRECTORY}/trivy-bin"
mkdir -p -- "$install_directory"
if [[ "$extension" == zip ]]; then
    unzip -p "$archive" "$executable" > "${install_directory}/${executable}"
else
    tar -xzf "$archive" -C "$install_directory" "$executable"
fi
chmod +x "${install_directory}/${executable}"
"${install_directory}/${executable}" --version
if [[ "$RUNNER_OS" == Windows ]]; then
    install_directory=$(cygpath -w "$install_directory")
fi
printf '%s\n' "$install_directory" >> "$GITHUB_PATH"
