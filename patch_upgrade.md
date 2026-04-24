# 增量升级方案

## 一、背景
当前项目全量包约460MB，而版本迭代核心变更内容（业务JAR、前端资源、配置）仅占少量，框架JAR等核心组件基本不变。为提升部署效率、降低传输成本，优化现有全量升级模式，设计增量升级方案。
当前全量包约 460 MB，但每次版本变化的主要内容很小：
- 业务 JAR（lib/ 中约 15-20 个）~15-20 MB
- 前端（web/）~58 MB
- 配置变更通常 <5 MB

框架 JAR（Spring、Flink、Hibernate 等）~300 MB 基本不变。
## 二、目标
- 轻量化迭代：拆分全量包，日常升级仅传输变更内容，降低包体大小。
- 兼容适配：不改动原有业务代码和运行架构，平滑对接现有部署流程。
- 安全可靠：具备版本校验、自动备份、一键回滚能力，规避升级风险。
- 可自动化：支持CI自动构建增量包，简化运维部署操作。
## 三、要求
###  包体积极致优化
- 首次安装：320MB（base 包）
- 日常迭代：最小 5MB（配置）/20MB（后端）/58MB（前端）
- 传输 / 部署效率提升 8~90 倍
### 零侵入兼容原有架构
  - 不修改代码、不改变运行目录，仅升级安装 / 构建脚本
### 全链路可追溯
  - 版本文件 + 元信息文件双校验，杜绝版本错乱
4: 安全兜底
  - 自动备份 + 一键回滚，支持单组件 / 全量回滚
## 四、核心设计思路
采用“基础包+增量包”分离模式，将稳定不变的组件与频繁变更的组件拆分，区分不同类型增量包，实现按需升级，同时配套版本管理、安装校验、

## 五、核心方案设计
### 4.1 包类型拆分
基于组件稳定性和变更频率，拆分5类包，适配不同升级场景：
- base包：包含框架JAR、基础配置、bin目录，供首次安装使用。
- lib-patch包：仅包含变更的业务JAR，适配后端小版本迭代。
- web-patch包：仅包含前端变更资源，适配UI更新。
- conf-patch包：仅包含增量配置文件，适配配置调整。
- full包：保留原有全量包，适配大版本升级或异常场景兜底。
### 4.2 版本管理设计
- 新增版本追踪文件，记录base版本及各组件（lib、web、conf）独立版本，实现版本可追溯。
- 增量包需关联对应base版本，安装前校验版本兼容性，不匹配则拦截升级，避免版本错乱。
- 所有包配套元信息文件，记录包类型、版本、构建时间等核心信息，支撑脚本自动解析。
### 4.3 安装与回滚设计
- 安装逻辑：优化安装脚本，自动识别包类型，根据包类型执行对应安装流程（全量覆盖/增量同步），安装后自动更新版本文件。
- 备份机制：升级前自动备份当前组件，留存备份文件用于回滚。
- 回滚机制：支持一键全量回滚和单组件快速回滚，恢复至升级前版本，降低升级风险。
### 4.4 自动化构建设计
优化CI构建脚本，新增增量包构建逻辑，自动识别变更文件，生成对应类型增量包及元信息文件，实现增量包自动化构建，减少人工干预。

## 六、方案思路：基础包 + 增量包分离
### 包类型定义

| 包类型 | 内容 | 典型大小 | 场景 |
|--------|------|----------|------|
| **base** | 框架 JAR + bin + 基础 conf | ~320 MB | 首次安装 |
| **lib-patch** | lib/ 下业务 JAR 变更 | ~20 MB | 后端代码小版本更新 |
| **web-patch** | web/ 前端变更 | ~58 MB | UI 更新 |
| **conf-patch** | conf/ 增量配置 | <5 MB | 配置调整 |
| **full** | 全量包（保持现状） | ~460 MB | 大版本升级 |

### 目录结构

```
# 构建输出目录
output/
├── base-v{版本}/                # 基础稳定包（首次安装）
├── lib-patch-v{版本}/           # 后端业务包增量更新
├── web-patch-v{版本}/           # 前端静态资源增量更新
├── conf-patch-v{版本}/          # 配置文件增量更新
└── full-v{版本}/                # 全量包（兼容原有流程）

增量包结构（与全量包平级）:
├── base/                    # 基础包
│   ├── lib/                 # 框架 JAR（稳定）
│   ├── bin/
│   └── conf/                # 基础配置
├── lib-patch-v5.2.2.23/     # 增量包示例
│   ├── lib/                 # 仅变更的业务 JAR
│   └── meta_info.json       # 版本信息
├── web-patch-v5.2.2.23/
│   ├── web/
│   └── meta_info.json
└── conf-patch-v5.2.2.23/
    ├── conf/
    └── meta_info.json
```

### 增量包元信息 (meta_info.json)

```json
{
    "code": "baas",
    "type": "lib-patch",
    "baseVersion": "v5.2.2.22",
    "targetVersion": "v5.2.2.23",
    "description": "修复XXX问题",
    "timestamp": "2604100129",
    "includes": [
        "lib/ailpha-ext-baas-*.jar",
        "lib/baas-aiql-*.jar"
    ]
}
```
### 流程概要设计

```
pod 不能改变的
补丁升级流程一：挂载方法【适用于频繁更改】
   1： 根据包名来区别是否为全量包还是补丁包 补丁包命令需要带上 patch [备注“cicd流水线改造”]
   2: 若是补丁版本，检查目前版本和目标版本号，确保补丁版和原版本兼容
   3: 若兼容，准备升级；检查升级包中lib-patch、conf-patch、web-patch内是否有文件，若满足升级条件
   把在运行的文件相应挂载出来，用补丁文件替换原先文件
补丁升级流程二：重打镜像
   1：一开始全量包的服务器安装包，安装或者升级后不能删掉
   2：调用升级平台，升级流程中判断是否为补丁包和版本校验
   3：若满足增量升级条件，把补丁包中文件覆盖原先文件后，走原先的打镜像升级逻辑
首次安装 (base 包):
  base包 → 安装全部组件 → 生成 .version
  

小版本升级 (lib-patch):
  lib-patch包 → 检查base版本 → rsync lib/ → 更新 .version

UI 更新 (web-patch):
  web-patch包 → 检查base版本 → rsync web/ → 更新 .version

配置更新 (conf-patch):
  conf-patch包 → rsync --compare-dest → 更新 .version

全量升级 (full 包):
  full包 → 全量覆盖 → 更新 .version
```
### 安装逻辑 (ext-install.sh 修改点)

```bash
# 1. 检测包类型
detect_package_type() {
    if [ -f "$current_path/meta_info.json" ]; then
        cat "$current_path/meta_info.json" | grep '"type"' | awk -F'"' '{print $4}'
    else
        echo "full"
    fi
}

# 2. 获取当前版本
get_current_version() {
    if [ -f "$ext_home/conf/.version" ]; then
        grep "^baseVersion=" "$ext_home/conf/.version" | cut -d= -f2
    else
        echo "none"
    fi
}

# 3. 版本兼容性检查
check_version_compatible() {
    local package_base=$1
    local current_base=$2

    if [ "$package_base" == "$current_base" ]; then
        return 0
    fi
    # 可扩展：检查版本大小、依赖关系等
    return 1
}

# 4. 安装基础包
install_base_package() {
    echo "Installing base package..."
    \cp -rpf $current_path/bin $ext_home
    \cp -rpf $current_path/lib $ext_home
    \cp -rpf $current_path/conf $ext_home
    \cp -rpf $current_path/input $ext_home
    \cp -rpf $current_path/elk $ext_home
    \cp -rpf $current_path/plugins $ext_home
    [ -d $current_path/web ] && \cp -rpf $current_path/web $ext_home

    # 写入版本文件
    echo "baseVersion=$target_version" > $ext_home/conf/.version
    echo "libVersion=$target_version" >> $ext_home/conf/.version
    echo "webVersion=$target_version" >> $ext_home/conf/.version
    echo "confVersion=$target_version" >> $ext_home/conf/.version
}

# 5. 安装增量包
install_patch_package() {
    local patch_type=$1
    local package_base=$2
    local current_base=$(get_current_version)

    # 版本兼容性检查
    if [ "$package_base" != "$current_base" ]; then
        echo "ERROR: Base version mismatch. Package requires $package_base, current is $current_base"
        return 1
    fi

    case $patch_type in
        lib-patch)
            echo "Installing lib patch..."
            rsync -avP $current_path/lib/ $ext_home/lib/
            # 更新版本
            sed -i "s/^libVersion=.*/libVersion=$target_version/" $ext_home/conf/.version
            ;;
        web-patch)
            echo "Installing web patch..."
            rsync -avP $current_path/web/ $ext_home/web/
            sed -i "s/^webVersion=.*/webVersion=$target_version/" $ext_home/conf/.version
            ;;
        conf-patch)
            echo "Installing conf patch..."
            rsync -avP --compare-dest=$ext_home/conf/ $current_path/conf/ $ext_home/conf/
            sed -i "s/^confVersion=.*/confVersion=$target_version/" $ext_home/conf/.version
            ;;
        *)
            echo "Unknown patch type: $patch_type"
            return 1
            ;;
    esac
}
```

### 版本文件格式 ($EXT_HOME/conf/.version)

```
baseVersion=v5.2.2.22
libVersion=v5.2.2.23
webVersion=v5.2.2.22
confVersion=v5.2.2.22
```

### 部署流程

```
首次安装 (base 包):
  base包 → 安装全部组件 → 生成 .version

小版本升级 (lib-patch):
  lib-patch包 → 检查base版本 → rsync lib/ → 更新 .version

UI 更新 (web-patch):
  web-patch包 → 检查base版本 → rsync web/ → 更新 .version

配置更新 (conf-patch):
  conf-patch包 → rsync --compare-dest → 更新 .version

全量升级 (full 包):
  full包 → 全量覆盖 → 更新 .version
```

### CI 构建修改点 (mgmtPackageDasCi.sh)

```bash
# 在构建流程中新增增量包生成逻辑

# 1. 构建 base 包（仅框架 JAR）
build_base_package() {
    # 复制稳定依赖到一个 base 目录
    mkdir -p $OUTPUT/base
    cp -r $BUILD_DIR/bin $OUTPUT/base/
    cp $STABLE_LIBS/* $OUTPUT/base/lib/
    cp -r $BUILD_DIR/conf $OUTPUT/base/

    # 生成 base meta_info.json
    cat > $OUTPUT/base/meta_info.json <<EOF
    {
        "type": "base",
        "targetVersion": "$VERSION",
        "timestamp": "$TIMESTAMP"
    }
    EOF
}

# 2. 构建 lib-patch（仅业务 JAR 变更）
build_lib_patch() {
    mkdir -p $OUTPUT/lib-patch-$VERSION
    cp $CHANGED_LIBS/* $OUTPUT/lib-patch-$VERSION/lib/

    cat > $OUTPUT/lib-patch-$VERSION/meta_info.json <<EOF
    {
        "type": "lib-patch",
        "baseVersion": "$BASE_VERSION",
        "targetVersion": "$VERSION",
        "includes": ["lib/ailpha-ext-baas-*.jar", "lib/baas-*.jar"]
    }
    EOF
}

# 3. 构建 web-patch
build_web_patch() {
    mkdir -p $OUTPUT/web-patch-$VERSION
    cp -r $WEB_BUILD/* $OUTPUT/web-patch-$VERSION/web/

    cat > $OUTPUT/web-patch-$VERSION/meta_info.json <<EOF
    {
        "type": "web-patch",
        "baseVersion": "$BASE_VERSION",
        "targetVersion": "$VERSION"
    }
    EOF
}
```

### 回滚策略

1. **自动备份**：升级前备份当前 `lib/`、`web/`、`conf/` 到 `/data/backup/`
2. **版本回滚**：
   ```bash
   # 回滚到指定版本
   ext-install.sh --rollback /data/backup/baas/v5.2.2.22/20240101/
   ```
3. **快速回滚**：
   ```bash
   # 回滚单个组件
   rsync -avP /data/backup/lib/ $ext_home/lib/
   sed -i "s/^libVersion=.*/libVersion=$previous_version/" $ext_home/conf/.version
   ```

### 需要修改的文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `bin/ext-install.sh` | 修改 | 新增 patch 安装逻辑 |
| `conf/.version` | 新增 | 版本追踪文件 |
| `lib-patch*/meta_info.json` | 新增 | 增量包元信息 |
| `web-patch*/meta_info.json` | 新增 | 增量包元信息 |
| `bin/mgmtPackageDasCi.sh` | 修改 | 新增增量包构建逻辑 |

### 验证方案

1. **本地测试**:
   - 安装 base 包
   - 应用 lib-patch，观察 JAR 更新
   - 检查 .version 文件版本号

2. **K8S 部署测试**:
   - 通过 kubectl 手动触发更新流程
   - 验证 Pod 重启后新版本生效

3. **回滚测试**:
   - 升级后执行回滚脚本
   - 验证恢复到正确版本
