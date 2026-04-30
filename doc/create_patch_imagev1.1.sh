#!/bin/bash

set -e

usage() {
    echo "Usage: $0 [target-path]"
    echo ""
    echo "Create a new patch image based on baseVersion and apply file changes."
    echo "The base image is searched using the baseVersion tag from patch_meta_info.json."
    echo ""
    echo "Arguments:"
    echo "  target-path    Target path in container (default: /usr/hdp/2.5.3.0-37/aispl/aisplweb)"
    echo ""
    echo "Example:"
    echo "  $0"
    echo "  $0 /custom/path"
    exit 1
}

TARGET_PATH="${1:-/usr/hdp/2.5.3.0-37/aispl/aisplweb}"
META_FILE="lib_patch/patch_meta_info.json"
LIB_PATCH_DIR="lib_patch"
EXTRACT_HIGH="extract/high"
EXTRACT_LOW="extract/low"

# Build nerdctl command with optional insecure flag
NERDCTL_CMD="nerdctl"
if [[ "${INSECURE_REGISTRY:-}" == "insecure" ]]; then
    NERDCTL_CMD="nerdctl --insecure-registry"
fi

# 清理残留的 nerdctl0 网络接口，避免子网冲突
if ip link show nerdctl0 &>/dev/null; then
    ip link del nerdctl0 2>/dev/null || true
fi

# Check if meta file exists
if [[ ! -f "$META_FILE" ]]; then
    echo "Error: $META_FILE not found"
    exit 1
fi

# Extract baseVersion and targetVersion
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

# Search for image with tag exactly matching baseVersion
echo ""
echo "Searching for base image with tag: $BASE_VERSION"
BASE_IMAGE_LINE=$(${NERDCTL_CMD} -n k8s.io images | grep "${BASE_VERSION}" | grep -v '<none>' | head -1)

if [[ -z "$BASE_IMAGE_LINE" ]]; then
    echo "Error: No image found with tag=$BASE_VERSION"
    exit 1
fi

# Extract image name (everything before the tag)
BASE_IMAGE_NAME=$(echo "$BASE_IMAGE_LINE" | awk '{print $1}')
echo "Found base image: $BASE_IMAGE_NAME:$BASE_VERSION"

echo "=========================================="
echo "Base Image: $BASE_IMAGE_NAME:$BASE_VERSION"
echo "Target Version: $TARGET_VERSION"
echo "Target Path: $TARGET_PATH"
echo "=========================================="

# Step 1: Pull base image
echo ""
echo "[1/6] Pulling base image..."
${NERDCTL_CMD} -n k8s.io pull "${BASE_IMAGE_NAME}:${BASE_VERSION}"

# Step 2: Create container
echo ""
echo "[2/6] Creating temporary container..."
CONTAINER_ID=$(${NERDCTL_CMD} -n k8s.io create "${BASE_IMAGE_NAME}:${BASE_VERSION}" /bin/bash)
echo "Container ID: $CONTAINER_ID"

# Step 3: Copy directories from lib_patch (auto-discovery)
# lib_patch 下有哪些目录就替换到对应位置，web 目录全量替换
echo ""
echo "[3/6] Copying lib_patch directories to container..."
for item in "$LIB_PATCH_DIR"/*; do
    item_name=$(basename "$item")

    # Skip non-directory items and patch_meta_info.json
    [[ -d "$item" && "$item_name" != "patch_meta_info.json" ]] || continue

    if [[ "$item_name" == "web" ]]; then
        # Web directory: full replacement
        echo "  Replacing web/ (full replacement)..."
        ${NERDCTL_CMD} -n k8s.io cp "$item/." "$CONTAINER_ID:$TARGET_PATH/web/"
    else
        # Other directories: merge replacement (lib, conf, bin, etc.)
        echo "  Copying $item_name/..."
        ${NERDCTL_CMD} -n k8s.io cp "$item/." "$CONTAINER_ID:$TARGET_PATH/$item_name/"
    fi
done
echo "lib_patch directories copied successfully"

# Step 4: Copy extract/high content (bin, conf, lib, plugins, web)
echo ""
echo "[4/6] Copying extract/high content to container..."
if [[ -d "$EXTRACT_HIGH" ]]; then
    EXTRACT_SUBDIR=""
    for dir in "$EXTRACT_HIGH"/*/; do
        if [[ -d "$dir" && "$dir" != */\.* ]]; then
            EXTRACT_SUBDIR="$dir"
            break
        fi
    done

    if [[ -n "$EXTRACT_SUBDIR" && -d "$EXTRACT_SUBDIR" ]]; then
        for subdir in bin conf lib plugins web; do
            if [[ -d "$EXTRACT_SUBDIR/$subdir" ]]; then
                echo "  Copying $subdir/..."
                ${NERDCTL_CMD} -n k8s.io cp "$EXTRACT_SUBDIR/$subdir/." "$CONTAINER_ID:$TARGET_PATH/$subdir/"
            fi
        done
        echo "Extract/high content copied successfully"
    else
        echo "Warning: No valid extract directory found in $EXTRACT_HIGH"
    fi
else
    echo "Warning: $EXTRACT_HIGH directory not found, skipping"
fi

# Step 5: Delete files based on excludes and sync low->high deletions
echo ""
echo "[5/6] Deleting files based on excludes and low->high diff..."
# A. Delete based on excludes list
if [[ -f "$META_FILE" ]]; then
    excludes_line=$(grep '"excludes"' "$META_FILE")
    if [[ "$excludes_line" =~ \[(.*)\] ]]; then
        excludes_content="${BASH_REMATCH[1]}"
        while [[ "$excludes_content" =~ \"([^\"]+)\" ]]; do
            exclude_item="${BASH_REMATCH[1]}"
            excludes_content="${excludes_content#*\"$exclude_item\"}"

            if [[ "$exclude_item" == lib/* || "$exclude_item" == conf/* || "$exclude_item" == bin/* || "$exclude_item" == plugins/* ]]; then
                file_path="$TARGET_PATH/$exclude_item"
                echo "  Deleting (excludes): $file_path"
                ${NERDCTL_CMD} -n k8s.io exec "$CONTAINER_ID" rm -f "$file_path" 2>/dev/null || true
            fi
        done
    fi
fi

# B. Sync deletions: files in extract/low but not in extract/high
if [[ -d "$EXTRACT_LOW" && -d "$EXTRACT_HIGH" ]]; then
    LOW_SUBDIR=""
    for dir in "$EXTRACT_LOW"/*/; do
        if [[ -d "$dir" && "$dir" != */\.* ]]; then
            LOW_SUBDIR="$dir"
            break
        fi
    done

    HIGH_SUBDIR=""
    for dir in "$EXTRACT_HIGH"/*/; do
        if [[ -d "$dir" && "$dir" != */\.* ]]; then
            HIGH_SUBDIR="$dir"
            break
        fi
    done

    if [[ -n "$LOW_SUBDIR" && -n "$HIGH_SUBDIR" ]]; then
        for subdir in lib conf bin plugins web; do
            if [[ -d "$LOW_SUBDIR/$subdir" && -d "$HIGH_SUBDIR/$subdir" ]]; then
                while IFS= read -r file; do
                    rel_path="${file#$LOW_SUBDIR/$subdir/}"
                    target_path="$TARGET_PATH/$subdir/$rel_path"
                    if [[ ! -f "$HIGH_SUBDIR/$subdir/$rel_path" ]]; then
                        echo "  Deleting (not in high): $target_path"
                        ${NERDCTL_CMD} -n k8s.io exec "$CONTAINER_ID" rm -f "$target_path" 2>/dev/null || true
                    fi
                done < <(find "$LOW_SUBDIR/$subdir" -type f 2>/dev/null)
            fi
        done
    fi
fi

# Step 6: Commit new image and cleanup
echo ""
echo "[6/6] Committing new image..."
# Ensure container is in a valid state for commit
${NERDCTL_CMD} -n k8s.io start "$CONTAINER_ID" 2>/dev/null || true
sleep 1
${NERDCTL_CMD} -n k8s.io commit "$CONTAINER_ID" "${BASE_IMAGE_NAME}:${TARGET_VERSION}"

echo ""
echo "Removing temporary container..."
${NERDCTL_CMD} -n k8s.io rm -f "$CONTAINER_ID" 2>/dev/null || true

echo ""
echo "=========================================="
echo "SUCCESS: New image created"
echo "Image: ${BASE_IMAGE_NAME}:${TARGET_VERSION}"
echo "=========================================="