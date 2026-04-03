
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
      langgraph 依赖安装命令 uv add --upgrade 'langgraph-cli[inmem]'  

 #### 第三步 :配置LangSmith配置
       LANGCHAIN_TRACING_V2=true                                                                                                                        
       LANGCHAIN_API_KEY=<your_api_key>
       LANGCHAIN_PROJECT=agent-dev    # 可选，project 名称                                                                                              
       LANGCHAIN_ENDPOINT=https://api.smith.langchain.com   
 #### 第四步 :在根目录下配置langgraph.json配置
        {                                                                                                                                                
          "dependencies": ["./src"],  #必填 python的依赖路径                                                                                                                   
           "graphs": {   #必填 图名称 -> 文件路径映射                                                                                                                                  
                "agent": "./src/agent_graph.py"                                                                                                              
           },                                                                                                                                             
           "env": ".env",        #非必填 环境变量                                                                                                                         
           "storage": "langgraph.json"  # 非必填 持久化配置（默认 in-memory）
        }
 
 #### 第五步 :编写智能体代码
   


     
  
