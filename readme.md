
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





 #### 备注 :命令
     1： 查看pig是否虚拟环境 Get-Command pip
     既然虚拟环境没有 pip，但系统 Python 有 pip，你可以用系统 pip 给虚拟环境安装 pip：
     方法 1：使用 ensurepip（推荐）
     python -m ensurepip --default-pip
     python -m pip install -U "langgraph-cli[inmem]"



   


     
  
