#!/bin/bash

set -e

PASSWORD="ePb%R7XW#$"
BASE_DIR=$(cd "$(dirname "$0")" && pwd)
EXTRACT_DIR="$BASE_DIR/extract"
LIB_PATCH_DIR="$BASE_DIR/lib_patch"

# Default directories to compare (can be overridden by command line arguments)
DEFAULT_DIRS="conf lib web"

# Function to show usage
usage() {
    echo "Usage: $0 [dir1] [dir2] ..."
    echo ""
    echo "Compare upgrade packages and generate patch for differing files."
    echo ""
    echo "Arguments:"
    echo "  dir1, dir2, ...  Directories to compare (default: $DEFAULT_DIRS)"
    echo "                   Supported: conf, lib, plugin, etc."
    echo ""
    echo "Examples:"
    echo "  $0                    # Compare conf and lib"
    echo "  $0 conf lib plugin    # Compare conf, lib, and plugin"
    echo "  $0 conf               # Compare only conf"
    echo ""
    exit 1
}

# Parse arguments
if [[ $# -eq 0 ]]; then
    COMPARE_DIRS="$DEFAULT_DIRS"
else
    COMPARE_DIRS="$*"
fi

# Find all upgrade packages matching the pattern
PACKAGES=$(ls ailpha-ext-*-v*.*.*.*_* 2>/dev/null)

if [[ -z "$PACKAGES" ]]; then
    echo "Error: No upgrade packages found (ailpha-ext-*-v*.*.*.*_*)"
    exit 1
fi

# Count packages
PACKAGE_COUNT=$(echo "$PACKAGES" | wc -l)
echo "Found $PACKAGE_COUNT package(s):"
echo "$PACKAGES"
echo ""
echo "Directories to compare: $COMPARE_DIRS"
echo ""

# Function to extract version number (e.g., v1.1.0.21 -> 1,1,0,21)
extract_version() {
    local filename="$1"
    echo "$filename" | grep -oP 'v\d+\.\d+\.\d+\.\d+' | grep -oP '\d+\.\d+\.\d+\.\d+'
}

# Extract service name (first 3 segments separated by '-')
# e.g., ailpha-ext-aispl-v1.1.0.23_aisplweb_dev-... -> ailpha-ext-aispl
extract_service_name() {
    local filename="$1"
    echo "$filename" | cut -d'-' -f1-3
}

# Extract full version string
# e.g., ailpha-ext-aispl-v1.1.0.23_aisplweb_dev-... -> v1.1.0.23_aisplweb_dev
extract_version_full() {
    local filename="$1"
    echo "$filename" | grep -oP 'v\d+\.\d+\.\d+\.\d+_[a-zA-Z0-9]+'
}

# Function to compare versions: returns 1 if v1 > v2, 2 if v2 > v1, 0 if equal
compare_versions() {
    local v1="$1"
    local v2="$2"

    # Split into array by '.'
    IFS='.' read -ra V1_PARTS <<< "$v1"
    IFS='.' read -ra V2_PARTS <<< "$v2"

    # Compare each part (assuming 4 parts)
    for i in 0 1 2 3; do
        local p1="${V1_PARTS[$i]:-0}"
        local p2="${V2_PARTS[$i]:-0}"

        if [[ $p1 -gt $p2 ]]; then
            echo "1"
            return
        elif [[ $p1 -lt $p2 ]]; then
            echo "2"
            return
        fi
    done

    echo "0"
}

# Find highest and lowest version packages
HIGH_VERSION=""
HIGH_VERSION_PKG=""
LOW_VERSION=""
LOW_VERSION_PKG=""

for pkg in $PACKAGES; do
    ver=$(extract_version "$pkg")

    if [[ -z "$ver" ]]; then
        continue
    fi

    if [[ -z "$HIGH_VERSION" ]]; then
        HIGH_VERSION="$ver"
        HIGH_VERSION_PKG="$pkg"
        LOW_VERSION="$ver"
        LOW_VERSION_PKG="$pkg"
    else
        cmp=$(compare_versions "$ver" "$HIGH_VERSION")
        if [[ "$cmp" == "1" ]]; then
            HIGH_VERSION="$ver"
            HIGH_VERSION_PKG="$pkg"
        fi

        cmp=$(compare_versions "$ver" "$LOW_VERSION")
        if [[ "$cmp" == "2" ]]; then
            LOW_VERSION="$ver"
            LOW_VERSION_PKG="$pkg"
        fi
    fi
done

if [[ -z "$HIGH_VERSION_PKG" ]] || [[ -z "$LOW_VERSION_PKG" ]]; then
    echo "Error: Could not determine high/low version packages"
    exit 1
fi

echo "High version: $HIGH_VERSION_PKG (version: $HIGH_VERSION)"
echo "Low version: $LOW_VERSION_PKG (version: $LOW_VERSION)"
echo ""

# Clean previous extraction directories
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR/high"
mkdir -p "$EXTRACT_DIR/low"

# Function to extract zip with password recursively
extract_zip() {
    local zip_file="$1"
    local dest_dir="$2"
    local pwd="$3"

    mkdir -p "$dest_dir"
    cp "$zip_file" "$dest_dir/"
    cd "$dest_dir"

    local current_zip="$dest_dir/$(basename "$zip_file")"

    # Keep extracting until no more zip files
    while true; do
        # Try to extract zip file with password
        if unzip -o -P "$pwd" "$current_zip" 2>/dev/null; then
            rm -f "$current_zip"

            # Find and extract any nested zip files
            local nested_zip
            nested_zip=$(find . -name "*.zip" -type f 2>/dev/null | head -1)
            if [[ -z "$nested_zip" ]]; then
                break
            fi
            current_zip="$nested_zip"
        else
            echo "Failed to extract: $current_zip"
            break
        fi
    done

    cd "$BASE_DIR"
}

# Function to extract tar.gz recursively
extract_targz() {
    local dir="$1"

    cd "$dir"

    # Keep extracting tar.gz until no more
    while true; do
        local targz_file
        targz_file=$(find . -name "*.tar.gz" -type f 2>/dev/null | head -1)
        if [[ -z "$targz_file" ]]; then
            break
        fi

        if tar -xzf "$targz_file" 2>/dev/null; then
            rm -f "$targz_file"
        else
            echo "Failed to extract: $targz_file"
            break
        fi
    done

    cd "$BASE_DIR"
}

echo "=== Extracting high version package ==="
extract_zip "$HIGH_VERSION_PKG" "$EXTRACT_DIR/high" "$PASSWORD"
extract_targz "$EXTRACT_DIR/high"

echo ""
echo "=== Extracting low version package ==="
extract_zip "$LOW_VERSION_PKG" "$EXTRACT_DIR/low" "$PASSWORD"
extract_targz "$EXTRACT_DIR/low"

# Find content directories (top-level directories in extracted package)
find_content_dir() {
    local search_dir="$1"
    local target_dir="$2"

    local result
    result=$(find "$search_dir" -maxdepth 2 -type d -name "$target_dir" 2>/dev/null | head -1)

    if [[ -z "$result" ]] && [[ -d "$search_dir/$target_dir" ]]; then
        result="$search_dir/$target_dir"
    fi

    echo "$result"
}

# For each comparison directory, find the paths
declare -A HIGH_DIRS
declare -A LOW_DIRS

for dir_name in $COMPARE_DIRS; do
    HIGH_DIRS["$dir_name"]=$(find_content_dir "$EXTRACT_DIR/high" "$dir_name")
    LOW_DIRS["$dir_name"]=$(find_content_dir "$EXTRACT_DIR/low" "$dir_name")
done

echo ""
echo "=== Directory paths ==="
for dir_name in $COMPARE_DIRS; do
    echo "$dir_name: high=${HIGH_DIRS[$dir_name]}, low=${LOW_DIRS[$dir_name]}"
done
echo ""

# Clean lib_patch directory
rm -rf "$LIB_PATCH_DIR"
mkdir -p "$LIB_PATCH_DIR"

# Function to compare and copy differing files (including nested directories)
compare_and_copy() {
    local high_dir="$1"
    local low_dir="$2"
    local patch_dir="$3"
    local dir_name="$4"

    if [[ ! -d "$high_dir" ]] || [[ ! -d "$low_dir" ]]; then
        echo "Warning: $dir_name directory not found in one of the packages"
        return
    fi

    echo "Comparing $dir_name files..."

    # Create temp file to collect files that need copying
    local temp_file=$(mktemp)

    # Special handling for lib directory: check for ailpha-ext-*-dist.jar
    if [[ "$dir_name" == "lib" ]]; then
        find "$high_dir" -type f -name "ailpha-ext-*-dist.jar" 2>/dev/null | while IFS= read -r dist_jar; do
            relative_path="${dist_jar#$high_dir/}"
            echo "$dist_jar|$dir_name/$relative_path|DIST" >> "$temp_file"
        done
    fi

    # Special handling for web directory: copy entire web directory from high version
    if [[ "$dir_name" == "web" ]]; then
        if [[ -d "$high_dir" ]]; then
            cp -r "$high_dir" "$patch_dir/$dir_name/"
            echo "  Web directory copied entirely from high version"
        fi
        return
    fi

    # Find all files in high version directory (recursively)
    find "$high_dir" -type f 2>/dev/null | while IFS= read -r high_file; do
        # Get relative path from high_dir
        relative_path="${high_file#$high_dir/}"
        low_file="$low_dir/$relative_path"

        # Skip if this is a dist.jar (already handled above)
        if [[ "$dir_name" == "lib" ]] && [[ "$high_file" == *"ailpha-ext-*-dist.jar" ]]; then
            continue
        fi

        # If file doesn't exist in low version (new file in high version)
        if [[ ! -f "$low_file" ]]; then
            echo "$high_file|$dir_name/$relative_path|NEW" >> "$temp_file"
        # If file exists in both versions and differs
        elif ! diff -q "$high_file" "$low_file" >/dev/null 2>&1; then
            echo "$high_file|$dir_name/$relative_path|DIFF" >> "$temp_file"
        fi
    done

    # Now process the collected files (only create dirs if there are files to copy)
    if [[ -s "$temp_file" ]]; then
        while IFS='|' read -r src_file dest_path type; do
            target_dir="$patch_dir/$(dirname "$dest_path")"
            mkdir -p "$target_dir"
            cp "$src_file" "$patch_dir/$dest_path"

            case "$type" in
                DIST)  echo "  Dist jar found: $dest_path" ;;
                NEW)  echo "  New file: $dest_path" ;;
                DIFF) echo "  Diff found: $dest_path" ;;
            esac
        done < "$temp_file"
    fi

    rm -f "$temp_file"
}

# Compare each directory
for dir_name in $COMPARE_DIRS; do
    if [[ -n "${HIGH_DIRS[$dir_name]}" ]] && [[ -n "${LOW_DIRS[$dir_name]}" ]]; then
        compare_and_copy "${HIGH_DIRS[$dir_name]}" "${LOW_DIRS[$dir_name]}" "$LIB_PATCH_DIR" "$dir_name"
    else
        echo "Warning: $dir_name directory not found in both packages, skipping"
    fi
done

echo ""
echo "=== Generating meta info ==="

# Extract service name and versions
SERVICE_NAME=$(extract_service_name "$HIGH_VERSION_PKG")
BASE_VERSION=$(extract_version_full "$LOW_VERSION_PKG")
TARGET_VERSION=$(extract_version_full "$HIGH_VERSION_PKG")
TIMESTAMP=$(date +%y%m%d%H%M)

# Generate patch_meta_info.json
META_JSON="$LIB_PATCH_DIR/patch_meta_info.json"
cat > "$META_JSON" << EOF
{
  "code": "$SERVICE_NAME",
  "type": "lib-patch",
  "baseVersion": "$BASE_VERSION",
  "targetVersion": "$TARGET_VERSION",
  "description": "修复bug问题",
  "timestamp": "$TIMESTAMP"
}
EOF

echo "Meta info generated: $META_JSON"
echo ""

echo "=== Done ==="
if [[ -d "$LIB_PATCH_DIR" ]] && [[ -n "$(ls -A "$LIB_PATCH_DIR" 2>/dev/null)" ]]; then
    echo "Changed files have been copied to: $LIB_PATCH_DIR"
    echo ""
    echo "Files:"
    find "$LIB_PATCH_DIR" -type f | sed "s|$LIB_PATCH_DIR/||" | sort
else
    echo "No differing files found in specified directories."
fi
