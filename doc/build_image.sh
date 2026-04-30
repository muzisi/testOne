#!/bin/bash

set -e

DOCKERFILE_PATH="lib_patch/Dockerfile"
META_FILE="lib_patch/patch_meta_info.json"

if [[ "${INSECURE_REGISTRY:-}" == "insecure" ]]; then
    export BUILDKIT_INSECURE_PULL=true
    NERDCTL_CMD="nerdctl --insecure-registry"
else
    NERDCTL_CMD="nerdctl"
fi

if [[ ! -f "$META_FILE" ]]; then
    echo "Error: $META_FILE not found"
    exit 1
fi

if [[ ! -f "$DOCKERFILE_PATH" ]]; then
    echo "Error: $DOCKERFILE_PATH not found, please run generate_dockerfile.sh first"
    exit 1
fi

# Extract versions from patch_meta_info.json
BASE_VERSION=$(grep -oP '"baseVersion":\s*"\K[^"]+' "$META_FILE")
TARGET_VERSION=$(grep -oP '"targetVersion":\s*"\K[^"]+' "$META_FILE")

if [[ -z "$BASE_VERSION" ]]; then
    echo "Error: Could not extract baseVersion from $META_FILE"
    exit 1
fi

if [[ -z "$TARGET_VERSION" ]]; then
    echo "Error: Could not extract targetVersion from $META_FILE"
    exit 1
fi

# Search for base image with tag exactly matching baseVersion
echo "Searching for base image with tag: $BASE_VERSION"
BASE_IMAGE_LINE=$(${NERDCTL_CMD} -n k8s.io images | grep "${BASE_VERSION}" | grep -v '<none>' | head -1)

if [[ -z "$BASE_IMAGE_LINE" ]]; then
    echo "Error: No image found with tag=$BASE_VERSION"
    exit 1
fi

# Extract image name and use targetVersion as new tag
BASE_IMAGE_NAME=$(echo "$BASE_IMAGE_LINE" | awk '{print $1}')
FULL_IMAGE_NAME="${BASE_IMAGE_NAME}:${TARGET_VERSION}"

echo "=========================================="
echo "Base Image: $BASE_IMAGE_NAME:$BASE_VERSION"
echo "Building image: $FULL_IMAGE_NAME"
echo "Dockerfile: $DOCKERFILE_PATH"
echo "=========================================="

${NERDCTL_CMD} -n k8s.io build \
    --insecure-registry \
    -t "$FULL_IMAGE_NAME" \
    -f "$DOCKERFILE_PATH" .

echo ""
echo "=========================================="
echo "SUCCESS: Image built"
echo "Image: $FULL_IMAGE_NAME"
echo "=========================================="
