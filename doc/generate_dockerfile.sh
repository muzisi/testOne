#!/bin/bash

set -e

TARGET_PATH="${1:-/usr/hdp/2.5.3.0-37/aispl/aisplweb}"
META_FILE="lib_patch/patch_meta_info.json"
LIB_PATCH_DIR="lib_patch"
DOCKERFILE_PATH="lib_patch/Dockerfile"

NERDCTL_CMD="nerdctl"
if [[ "${INSECURE_REGISTRY:-}" == "insecure" ]]; then
    NERDCTL_CMD="nerdctl --insecure-registry"
fi

if [[ ! -f "$META_FILE" ]]; then
    echo "Error: $META_FILE not found"
    exit 1
fi

BASE_VERSION=$(grep -oP '"baseVersion":\s*"\K[^"]+' "$META_FILE")
TARGET_VERSION=$(grep -oP '"targetVersion":\s*"\K[^"]+' "$META_FILE")

if [[ -z "$BASE_VERSION" ]]; then
    echo "Error: Could not extract baseVersion from $META_FILE"
    exit 1
fi

# Search for base image by tag
echo "Searching for base image with tag: $BASE_VERSION"
BASE_IMAGE_LINE=$(${NERDCTL_CMD} -n k8s.io images | grep "${BASE_VERSION}" | grep -v '<none>' | head -1)

if [[ -z "$BASE_IMAGE_LINE" ]]; then
    echo "Error: No image found with tag=$BASE_VERSION"
    exit 1
fi

BASE_IMAGE_NAME=$(echo "$BASE_IMAGE_LINE" | awk '{print $1}')
echo "Found base image: $BASE_IMAGE_NAME"

echo "=========================================="
echo "Base Image: $BASE_IMAGE_NAME"
echo "Base Version: $BASE_VERSION"
echo "Target Version: $TARGET_VERSION"
echo "=========================================="

echo ""
echo "Generating Dockerfile..."

DOCKERFILE_CONTENT="FROM ${BASE_IMAGE_NAME}
"

# 1. Dynamically scan lib_patch and copy files by directory
# For each directory (except patch_meta_info.json):
#   - web/: full replacement (copy entire directory)
#   - other dirs: copy each file individually (preserving structure)
for item in "$LIB_PATCH_DIR"/*; do
    [[ -d "$item" ]] || continue
    item_name=$(basename "$item")
    [[ "$item_name" != "patch_meta_info.json" ]] || continue

    if [[ "$item_name" == "web" ]]; then
        # Web directory: full replacement
        echo "  COPY $item_name/ -> $TARGET_PATH/$item_name/ (full replacement)"
        DOCKERFILE_CONTENT+="COPY $item_name/ $TARGET_PATH/$item_name/
"
    else
        # Other directories: copy each file individually
        while IFS= read -r -d '' file; do
            rel_path="${file#$item/}"
            echo "  COPY $item_name/$rel_path -> $TARGET_PATH/$item_name/$rel_path"
            DOCKERFILE_CONTENT+="COPY $item_name/$rel_path $TARGET_PATH/$item_name/$rel_path
"
        done < <(find "$item" -type f -print0)
    fi
done

# 2. Build excludes list (from patch_meta_info.json)
EXCLUDES_LIST=()
if [[ -f "$META_FILE" ]]; then
    excludes_line=$(grep '"excludes"' "$META_FILE")
    if [[ "$excludes_line" =~ \[(.*)\] ]]; then
        excludes_content="${BASH_REMATCH[1]}"
        while [[ "$excludes_content" =~ \"([^\"]+)\" ]]; do
            exclude_item="${BASH_REMATCH[1]}"
            excludes_content="${excludes_content#*\"$exclude_item\"}"

            if [[ "$exclude_item" == lib/* || "$exclude_item" == conf/* || \
                  "$exclude_item" == bin/* || "$exclude_item" == plugins/* ]]; then
                EXCLUDES_LIST+=("$TARGET_PATH/$exclude_item")
            fi
        done
    fi
fi

# 3. Add delete commands (remove duplicates)
if [[ ${#EXCLUDES_LIST[@]} -gt 0 ]]; then
    echo "  Adding ${#EXCLUDES_LIST[@]} delete commands..."

    declare -A SEEN
    UNIQUE_EXCLUDES=()
    for file_path in "${EXCLUDES_LIST[@]}"; do
        if [[ -z "${SEEN[$file_path]}" ]]; then
            SEEN[$file_path]=1
            UNIQUE_EXCLUDES+=("$file_path")
        fi
    done

    DOCKERFILE_CONTENT+="RUN rm -f"
    for file_path in "${UNIQUE_EXCLUDES[@]}"; do
        DOCKERFILE_CONTENT+=" \\
    $file_path"
    done
    DOCKERFILE_CONTENT+="
"
fi

echo "$DOCKERFILE_CONTENT" > "$DOCKERFILE_PATH"
echo ""
echo "Dockerfile generated: $DOCKERFILE_PATH"
echo ""
echo "=========================================="
echo "SUCCESS"
echo "=========================================="