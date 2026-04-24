你的需求很明确：**最终交付给现场的是一个 zip 包，里面包含 Dockerfile 和变更文件，现场解压后执行 `docker build` 就能生成新镜像**。但底层要利用 Docker 分层缓存和写时复制机制，只传输变更部分，而不是完整的应用文件。这本质上是 **以 Docker 镜像分层思想制作增量补丁 zip**。

下面给出完整、可落地的技术方案。

---

## 一、整体架构流程图

```
发布端：
基线zip (base-v1.0.zip)             目标zip (release-v1.2.zip)
      │                                    │
      ▼                                    ▼
构建基线镜像 myapp:1.0-base           构建目标镜像 myapp:1.2-full
      │                                    │
      └────────── 提取差异 ────────────────┘
                     │
                     ▼
         制作增量补丁 zip (patch-v1.0-to-v1.2.zip)
         内含：Dockerfile + 变更文件层（按目录存放）
                     │
                     ▼
              分发至现场环境

现场端：
解压 patch-v1.0-to-v1.2.zip
      │
      ▼
执行 docker build -t myapp:1.2 .
      │
      └── Docker 会检测到 FROM myapp:1.0-base
           复用本地已有镜像层 + 添加新的变更层 → 生成新镜像
```

---

## 二、发布端：制作增量补丁 zip 的详细步骤

### 2.1 前置条件
- 拥有基线 zip 包（如 `base-v1.0.zip`）和目标版本 zip 包（如 `release-v1.2.zip`）。
- 两个 zip 包解压后具有相同的目录结构（如 `app.jar`、`config/`、`lib/` 等）。
- Docker 环境已安装。

### 2.2 构建基线镜像（需固定镜像 ID）

**目的**：生成一个纯净的、仅包含应用文件的基线镜像，其镜像 ID 在所有环境（发布端和现场）**必须完全一致**，这是增量分层成功的关键。

```dockerfile
# Dockerfile.base
FROM scratch                           # 使用空镜像，确保只有应用文件
COPY base-v1.0/ /app/                  # 将基线zip解压内容复制进去
LABEL version="1.0.0"
```

构建命令：
```bash
# 解压基线 zip
unzip base-v1.0.zip -d base-v1.0/

# 构建镜像
docker build -f Dockerfile.base -t myapp:1.0-base .

# 记录镜像 ID（用于后续校验）
docker images myapp:1.0-base --format "{{.ID}}" > base-image-id.txt
```

> **保证 ID 一致的方法**：
> - 使用 `FROM scratch` 且不包含任何可变指令（如 `RUN`、`ARG`）。
> - 确保文件内容、权限、时间戳完全一致（可在制作 zip 时用 `find . -exec touch -t 202001010000 {} \;` 固定时间戳）。
> - 发布端和现场使用相同版本的 Docker 构建（虽然理论上 `scratch` + `COPY` 的 ID 跨环境应一致，但最好验证一次）。

### 2.3 构建目标版本完整镜像（仅用于提取差异）

```dockerfile
# Dockerfile.full
FROM myapp:1.0-base AS baseline
FROM scratch
COPY --from=baseline /app/ /app/           # 先复制基线内容
COPY release-v1.2/ /app/                   # 再覆盖新版本内容
LABEL version="1.2.0"
```

构建：
```bash
unzip release-v1.2.zip -d release-v1.2/
docker build -f Dockerfile.full -t myapp:1.2-full .
```

> 注意：这里用 `COPY --from` 复用基线层，确保目标镜像的底层 ID 与基线镜像完全一致。

### 2.4 提取两个镜像之间的文件系统差异

我们需要提取 **`myapp:1.2-full` 相对于 `myapp:1.0-base` 新增或修改的文件**，并按照原目录结构放入一个文件夹 `delta/` 中。

**方法一：使用 `docker export` 和 `rsync` 比较（推荐）**

```bash
# 创建临时容器并导出文件系统
docker create --name base_container myapp:1.0-base
docker export base_container | tar -x -C base_fs/

docker create --name full_container myapp:1.2-full
docker export full_container | tar -x -C full_fs/

# 使用 rsync 对比差异，只复制新增/修改的文件到 delta/ 目录
mkdir delta/
rsync -av --compare-dest=../base_fs/ full_fs/ delta/ --exclude='*.wh.*'   # 排除 overlay 特有文件

# 清理临时容器和目录
docker rm base_container full_container
rm -rf base_fs/ full_fs/
```

**方法二：利用 `docker save` 分析层差异（更底层）**

若你希望更精确地控制层内容，可以导出镜像的 tar 包，解析 `manifest.json` 找到最上层新增的 layer.tar，直接将其内容作为 `delta/`。但这需要对 Docker 镜像格式有深入了解，这里推荐方法一，更直观可靠。

> **注意**：`delta/` 中应只包含有变化的文件（包括新增和修改），且路径相对于 `/app/`（如 `delta/app.jar`、`delta/config/application.yml`）。删除操作无法通过文件覆盖实现，需借助元数据或脚本处理（见后文）。

### 2.5 制作增量补丁 zip 包结构

```
patch-v1.0-to-v1.2.zip
├── Dockerfile                # 用于现场构建新镜像
├── delta/                    # 变更文件（相对于 /app/ 目录）
│   ├── app.jar
│   ├── config/
│   │   └── application.yml
│   └── lib/
│       └── new-dep.jar
├── metadata.json             # 元数据（版本信息、删除列表等）
└── scripts/                  # 可选：升级前后钩子脚本
    ├── pre-build.sh
    └── post-build.sh
```

**Dockerfile 内容（关键）**：
```dockerfile
# Dockerfile (现场用)
ARG BASE_IMAGE=myapp:1.0-base   # 可被现场覆盖，默认与补丁匹配
FROM ${BASE_IMAGE}

# 复制变更文件到镜像，覆盖旧文件（Docker 会自动创建新层）
COPY delta/ /app/

# 可选：执行删除操作（通过 RUN 命令删除不需要的文件）
# 这里的删除列表由 metadata.json 提供，可以在构建时用脚本生成 RUN 指令
ARG DELETE_FILES=""
RUN if [ -n "$DELETE_FILES" ]; then rm -rf $DELETE_FILES; fi

LABEL version="1.2.0"
CMD ["java", "-jar", "/app/app.jar"]   # 或其他启动命令
```

**metadata.json 示例**：
```json
{
  "baseImage": "myapp:1.0-base",
  "baseImageId": "sha256:abcd1234...",
  "targetVersion": "1.2.0",
  "deleteFiles": [
    "/app/lib/old-dep.jar",
    "/app/config/legacy.properties"
  ]
}
```

**注意**：`deleteFiles` 路径为容器内的绝对路径。

### 2.6 打包补丁 zip

```bash
zip -r patch-v1.0-to-v1.2.zip Dockerfile delta/ metadata.json scripts/
```

此时补丁包体积只包含变更文件，远小于完整 zip。

---

## 三、现场端：使用补丁 zip 升级

现场环境已存在基线镜像 `myapp:1.0-base`（必须与发布端 ID 一致）。升级步骤如下：

### 3.1 解压补丁包

```bash
unzip patch-v1.0-to-v1.2.zip -d patch/
cd patch/
```

### 3.2 校验基线镜像是否存在且 ID 匹配

```bash
REQUIRED_ID=$(jq -r '.baseImageId' metadata.json)
CURRENT_ID=$(docker images -q myapp:1.0-base)
if [ "$REQUIRED_ID" != "$CURRENT_ID" ]; then
    echo "错误：基线镜像不匹配，升级终止。"
    exit 1
fi
```

### 3.3 执行 Docker 构建（自动分层增量）

```bash
# 读取删除列表并构建
DELETE_LIST=$(jq -r '.deleteFiles | join(" ")' metadata.json)
docker build \
    --build-arg BASE_IMAGE=myapp:1.0-base \
    --build-arg DELETE_FILES="$DELETE_LIST" \
    -t myapp:1.2 .
```

构建过程：
- `FROM myapp:1.0-base` 复用本地镜像的所有层。
- `COPY delta/ /app/` 只添加一个薄层（几十 MB），覆盖变化文件。
- `RUN rm -rf ...` 添加一个标记删除的层（极小）。

总构建时间很短，且不依赖网络。

### 3.4 验证并切换服务

```bash
docker run --rm myapp:1.2 java -version   # 或其他健康检查
# 停止旧容器，启动新容器
docker stop app_container
docker rm app_container
docker run -d --name app_container ... myapp:1.2
```

---

## 四、关键问题与应对

### 4.1 文件删除如何处理？

Docker 的 `COPY` 层无法直接删除下层文件。解决方案有两种：

**方案 A（推荐）**：在 Dockerfile 中用 `RUN rm -rf` 删除，生成一个新层（白层）。虽然被删文件仍存在于下层，但容器运行时看不到，镜像体积也不会缩小，但**增量传输体积不受影响**，因为旧层已存在于本地。

**方案 B**：在补丁应用时，现场先基于基线镜像运行一个临时容器，手动删除文件后 `docker commit` 生成中间镜像，再在其上 `COPY` 新文件。此方案会破坏镜像层历史，且不利于回滚，不推荐。

### 4.2 如何确保基线镜像 ID 完全一致？

- **构建环境标准化**：使用相同的 Docker 版本、相同的构建上下文（文件时间戳、权限）。
- **固定文件时间戳**：解压 zip 后，执行 `find . -exec touch -t 202501010000.00 {} \;`。
- **使用 `FROM scratch`**：避免基础镜像差异。
- **验证机制**：发布端生成基线镜像后，输出 `docker image inspect myapp:1.0-base | jq '.[0].RootFS'` 作为指纹，现场部署基线时同样生成指纹对比。

### 4.3 现场没有基线镜像怎么办？

若现场丢失了基线镜像（比如从未部署过 1.0），则无法使用此增量补丁。此时有两种备选方案：
- 提供**完整镜像 tar 包**（回退方案）。
- 在补丁 zip 中附带一个 **base-image.tar**（仅首次部署时需要），现场先 `docker load` 加载基线镜像。

### 4.4 配置文件的覆盖与合并

如果配置文件在现场有定制修改，全量覆盖会丢失修改。建议：
- 将配置文件外置为环境变量或 ConfigMap（Docker 层面），补丁中不包含配置文件。
- 若必须包含，可在 Dockerfile 中使用 `COPY --chown` 或 `RUN` 指令做智能合并，但复杂度高。

---

## 五、方案总结对比

| 对比项               | 传统 zip 全量分发 + 构建 | 本方案：Docker 镜像层增量 zip |
|----------------------|-------------------------|-------------------------------|
| 传输体积             | 完整 zip（几百 MB）     | 仅变更文件（几十 MB）         |
| 现场构建时间         | 重新复制所有文件         | 复用基线层，仅添加一层        |
| 对基线依赖           | 需要保留基线 zip         | 需要保留基线镜像（ID 一致）   |
| 文件删除实现         | 直接删除文件             | 用 `RUN rm` 白层覆盖          |
| 实施复杂度           | 低                       | 中等（需处理 ID 一致性问题）  |
| 与 Dockerfile 兼容性 | 高                       | 高（最终仍用 Dockerfile）     |

此方案完美契合你最初的想法：**交付物是包含 Dockerfile 的 zip，但内部只含增量层**，现场升级如同 `FROM baseline` 后添加一个 `COPY` 层，既快速又节省带宽。