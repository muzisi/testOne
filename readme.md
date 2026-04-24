
### 创建Agent项目和本地测试环境
 #### 第一步 :创建项目
     项目结构
      agent
         |-src
         |-|-agent.py
         |-.env
         |-.langgraph.json
         |-.pyproject.toml
 #### 第二步 :导包依赖创建
      langchain 依赖安装命令 uv add langchain langchain-openai python-dotenv
      langgraph 依赖安装命令 uv add --upgrade 'langgraph-cli[inmem]'  pig install --upgrade 'langgraph-cli[inmem]'
      uv add langchain langchain-openai
      pip install --upgrade "langgraph-cli[inmem]"
      # Python >= 3.11 is required.
      pip install --upgrade "langgraph-cli[inmem]"

 #### 第三步 :配置LangSmith配置
       LANGCHAIN_TRACING_V2=true                                                                                                                        
       LANGCHAIN_API_KEY=<your_api_key>
       LANGCHAIN_PROJECT=agent-dev    # 可选，project 名称                                                                                              
       LANGCHAIN_ENDPOINT=https://api.smith.langchain.com   
 #### 第四步 :在根目录下配置langgraph.json配置
        {                                                                                                                                                
          "dependencies": ["."],  #必填 python的依赖路径                                                                                                                   
           "graphs": {   #必填 图名称 -> 文件路径映射                                                                                                                                  
                "agent": "./src/agent_graph.py:agent1"    #agent1为agent名称                                                                                                        
           },                                                                                                                                             
           "env": ".env",        #非必填 环境变量                                                                                                                         
           "storage": "langgraph.json"  # 非必填 持久化配置（默认 in-memory）
        }
 
 #### 第五步 :编写智能体代码

 #### 第六步 :安装依赖项
      在新的langGraph应用的根目录下，安装依赖项
      1:先拷贝pyproject.toml到项目目录下
 #### 第七步 :检查依赖
      命令pip install -e .


### 创建langgraph项目




 #### 备注 :命令
     1： 查看pig是否虚拟环境 Get-Command pip
     既然虚拟环境没有 pip，但系统 Python 有 pip，你可以用系统 pip 给虚拟环境安装 pip：
     方法 1：使用 ensurepip（推荐）
     python -m ensurepip --default-pip
     python -m pip install -U "langgraph-cli[inmem]"









### LangChain知识点

 #### 一：tool中核心概念
 ###### state【状态】  短短期记忆 / 对话上下文
      里面存内容：
         聊天消息列表 messages
         工具调用次数
         中间思考结果
         临时变量
     人话类比：= 你和机器人聊天的当前聊天记录纸聊完就丢，只存这一轮对话。
     作用：让 Agent 知道刚才聊了什么。
 ######  Context（上下文）= 固定配置 / 不可变信息
      里面存内容：
           user_id
           session_id
           语言（zh/en）
           场景（客服 / 助手 / 游戏）
      人话类比：= 这轮聊天的固定身份信息，中途不能改。
      作用：根据谁在聊天来个性化回答
 ######  Store（持久存储）= 长期记忆 / 数据库    
      里面存内容：
        用户偏好
        历史设置
        知识库
        长期统计
      人话类比：= 用户档案本今天聊完关掉，明天打开还在。
      作用：跨对话记住用户。
 ###### Stream Writer（流写入器）= 实时发消息
      用途：
      长任务实时显示进度
      打字机效果
      中间步骤推送前端
 ###### Config（执行配置）= 运行时参数
       人话类比：= 这次运行的调试 / 追踪设置
       用途：
        LangSmith 监控追踪
        打标签
        传回调函数
 ###### Tool Call ID（工具调用 ID）= 工具唯一标识
        人话类比：= 给每次工具调用一个身份证号
        用途：追踪哪个 LLM 调用触发了哪个工具 日志关联


#### 二 短期记录
     短期记忆 = 当前对话（thread）内的临时记忆
     只在当前会话有效
     基于 State 存储
     靠 Checkpointer 持久化
     重启服务 / 切换 thread 就清空（除非存数据库）
     作用：让 Agent 记住本轮聊天历史，实现多轮对话。
#### 三 内置中间建
    一、整体作用
      中间件 = 给 Agent 加装 “插件”不用改核心代码，就能实现：安全、限流、容错、记忆、审核、上下文管理等能力。
     二、通用中间件（所有模型都能用）
         1. SummarizationMiddleware（上下文总结）
          快超 Token 时自动压缩旧消息，保留最近 N 条，防止上下文溢出；配置：trigger 触发条件、keep 保留条数
         2. HumanInTheLoopMiddleware（人在循环）
         工具执行前暂停 → 人工审核 / 编辑 / 拒绝 必须配合 checkpointer 记忆 配置：interrupt_on 指定哪些工具需要审核
         3. ModelCallLimitMiddleware（模型调用次数限制）
         限制模型调用次数，防死循环、控成本 ；thread_limit：会话总次数；run_limit：单次调用次数
         4. ToolCallLimitMiddleware（工具调用次数限制）
         限制全局 / 单个工具调用次数 ；可配置超限行为：继续 / 报错 / 停止
         5. ModelFallbackMiddleware（模型故障转移）
         主模型挂了，自动切备用模型；提高可用性、降成本
         6. PIIMiddleware（隐私信息检测）
         自动识别并处理隐私信息（手机号、邮箱、身份证等）策略：遮蔽、掩码、拦截、哈希支持自定义正则 / 函数检测
         7. TodoListMiddleware（任务清单）
         给 Agent 自动加任务规划与追踪能力
         8. LLMToolSelectorMiddleware（工具智能筛选）
           工具很多时，先用小模型挑出最相关的；减少 Token、提升准确率
         9. ToolRetryMiddleware（工具自动重试）
           工具失败自动指数退避重试 处理网络 / 接口波动
         10. LLMToolEmulatorMiddleware（工具模拟器）
           用 LLM 模拟工具返回 开发调试、无真实工具环境用
         11. ContextEditingMiddleware（上下文编辑）
           超 Token 时清理旧工具结果 ；保留最近 N 条工具返回
         12. ShellToolMiddleware（Shell 执行）
            给 Agent 开命令行权限
            支持 Docker 安全沙箱
         13. FilesystemFileSearchMiddleware（文件搜索）
            提供文件搜索、内容检索工具
           适合代码项目、文档检索
#### 四 自定义中间件
     在 Agent 执行流程的关键点插入自定义逻辑，不用改主流程。用途：日志、重试、缓存、校验、限流、动态切换模型 / 工具、异常拦截。
######  二、两种核心 Hook 风格
     1. Node-style hooks（节点式）
        按顺序在固定节点运行适合：日志、校验、状态更新。
        可用：
        before_agent：Agent 启动前（一次）
        before_model：每次调用模型前
        after_model：每次模型返回后
        after_agent：Agent 结束后（一次）
    2. Wrap-style hooks（包裹式）
       包裹模型 / 工具调用，控制执行次数适合：重试、降级、缓存、改写请求 / 响应。
       可用：
       wrap_model_call：包裹每次模型调用
       wrap_tool_call：包裹每次工具调用