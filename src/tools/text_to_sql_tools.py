from typing import Any, Optional, List

from langchain_core.tools import BaseTool
from langchain_core.utils.pydantic import create_model
from pydantic import Field

from utils.db_utils import MyDataSourceManager,DBConfig
from utils.logger import get_logger
Logger = get_logger()


class ListTablesTool(BaseTool):
    """列出所有表的名字和描述"""
    name :str ="sql_db_list_tables"
    description :str ="列出数据库中所有的表名以及其描述信息,当需要了解数据库中有哪些表以及表的用途时候，调用此工具"
    db_manager : MyDataSourceManager

    def _run(self, **kwargs: Any) ->str:
        try:
            tables_info = self.db_manager.get_table_comments()
            result = f"数据库中共有 {len(tables_info)}个表：\n\n"
            for i, table_info in enumerate(tables_info):
                table_name = table_info['table_name']
                table_comment = table_info['table_comment']
                if not table_comment or table_comment.isspace():
                    desc = " (暂无描述) "
                else:
                    desc = table_comment
                result += f"{i+1}. 表名：{table_name}\n"
                result += f"  描述: {desc}\n\n"
            return result
        except Exception as e:
            Logger.error(str(e))
            return f"异常信息：{str(e)}"

    async def _arun(self) -> str:
        return  self._run()



class TableSchemaTool(BaseTool):
    """列出所有表的名字和描述"""
    name :str ="sql_db_schema"
    description :str ="获取数据库中指定表的详细模式信息，包含列定义，主键，外键等，输入为表名列表"
    db_manager : MyDataSourceManager

    def __init__(self, db_manager: MyDataSourceManager) -> None:
        super().__init__(db_manager=db_manager)
        self.db_manager = db_manager
        self.args_schema = create_model("TableSchemaToolArgs",table_name=(Optional[List[str]], Field(default=None, description="表名列表")))

    def _run(self, table_name: Optional[List[str]]) ->str:
        try:
            schema = self.db_manager.get_table_schema(table_name)
            return str(schema)
        except Exception as e:
            Logger.error(str(e))
            return f"异常信息：{str(e)}"
    async def _arun(self) -> str:
        return self._run()



class SQLTableQueryTool(BaseTool):

    """执行SQL 查询"""

    name :str ="sql_db_query"
    description: str = "在数据库中执行安全的 SELECT查询并返回结果，输入有效的SQL SELECT 语句"
    db_manager : MyDataSourceManager

    def __init__(self, db_manager: MyDataSourceManager) -> None:
        super().__init__(db_manager=db_manager)
        self.db_manager = db_manager
        self.args_schema = create_model("SQLTableQueryToolArgs",
                                        query=(str, Field(..., description="有效的sql查询语句")))
    def _run(self, query: str) ->str:

        try:
            result = self.db_manager.execute_query(query)
            return str(result) if result else "查询结果为空"
        except Exception as e:
            Logger.error(str(e))
            return f"异常信息：{str(e)}"

    async def _arun(self) -> str:
        return self._run()







if __name__ == "__main__":
    pg_config = DBConfig(
        host="10.20.183.11",
        port=45432,
        database="postgres",
        user="dbapp",
        password="MlvItsVu97Lgt4AU",
        db_type="postgresql",
        schema="aispl_monitor"
    )


    db = MyDataSourceManager(pg_config)
   # tool = ListTablesTool(db_manager=db)
   # print(tool.invoke({}))


    tool = SQLTableQueryTool(db_manager=db)
    print(tool.invoke({"query": "SELECT rule_id, rule_name FROM t_batch_strategy LIMIT 1"}))
