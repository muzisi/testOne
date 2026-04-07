from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, create_model


class MyTestTool (BaseTool):
    name = "my_test_tool"
    description = "获取test"

    def __int__(self,**kwargs):
        super().__init__(**kwargs)
        self.args_schema=create_model("search",name=(str,...))

    def _run(self, name: str, **kwargs: Any) -> str:
        return f"方法测试：{name}"


tool = MyTestTool()
print(tool.run({"name": "张三"}))