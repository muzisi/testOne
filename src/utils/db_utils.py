from pydantic.dataclasses import dataclass
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from logger import Logger

@dataclass
class DBConfig:
    """数据库配置"""
    host: str
    port: int
    database: str
    user: str
    password: str
    db_type: str = "mysql"
    schema: str = "public"

    def get_url(self) -> str:
        """获取数据库连接 URL"""
        if self.db_type == "mysql":
            return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == "postgresql":
            url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            if self.schema:
                url += f"?options=-csearch_path%3D{self.schema}"
            return url
        else:
            raise ValueError(f"Unsupported db_type: {self.db_type}")


class MyDataSourceManager:

    def __init__(self, config: DBConfig):
        """
               初始化数据库连接

               Args:
                   config: 数据库配置
               """
        self.config = config
        self._engine: Optional[Engine] = None

    def _get_engine(self) -> Engine:
        """获取数据库引擎"""
        if self._engine is None:
            self._engine = create_engine(
                self.config.get_url(),
                pool_pre_ping=True,  # 连接前检查
                pool_size=5,
                max_overflow=10
            )
        return self._engine

    @contextmanager
    def get_session(self):
        """获取会话上下文管理器"""
        engine = self._get_engine()
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def get_table_names(self) -> List[str]:
        """获取所有表名"""
        try:
            with self.get_session() as session:
                inspector = inspect(session.bind)
                return inspector.get_table_names()
        except Exception as e:
            Logger.error(e)
            raise ValueError("获取表名失败")


    def get_table_comments(self) -> List[Dict[str, str]]:
        """获取所有表名和注释
        Returns:
            list[dict]: 一个字典列表，每个字典包含table_name和table_comment
        """
        try:
            with self.get_session() as session:
                result = session.execute(text("""
                    SELECT
                        c.relname AS table_name,
                        COALESCE(d.description, '') AS table_comment
                    FROM pg_class c
                    LEFT JOIN pg_description d ON c.oid = d.objoid
                    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relkind = 'r'
                    AND n.nspname = :schema
                    ORDER BY c.relname
                """), {"schema": self.config.schema})
                return [{"table_name": row[0], "table_comment": row[1]} for row in result]
        except Exception as e:
            Logger.error(e)
            raise ValueError("获取表注释失败")

    def get_table_schema(self, table_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """根据表名获取对应的字段名称、字段类型、表的主键/外键和其他约束信息
        Args:
            table_names: 要获取的表名列表，None 则获取所有表
        Returns:
            list[dict]: 包含表结构和约束信息的字典列表
        """
        try:
            with self.get_session() as session:
                inspector = inspect(session.bind)
                if table_names is None:
                    table_names = inspector.get_table_names(schema=self.config.schema)

                schemas = []
                for table_name in table_names:
                    # 获取列信息
                    columns = inspector.get_columns(table_name, schema=self.config.schema)

                    # 获取主键
                    pk_columns = inspector.get_pk_constraint(table_name, schema=self.config.schema).get("constrained_columns", [])

                    # 获取外键
                    fk_constraints = inspector.get_foreign_keys(table_name, schema=self.config.schema)

                    # 获取索引
                    indexes = inspector.get_indexes(table_name, schema=self.config.schema)

                    # 获取唯一约束
                    unique_constraints = inspector.get_unique_constraints(table_name, schema=self.config.schema)

                    # 获取字段注释
                    comment_result = session.execute(text("""
                        SELECT
                            a.attname AS column_name,
                            COALESCE(d.description, '') AS column_comment
                        FROM pg_attribute a
                        JOIN pg_class c ON c.oid = a.attrelid
                        LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = a.attnum
                        WHERE c.relname = :table
                            AND a.attnum > 0
                            AND NOT a.attisdropped
                        ORDER BY a.attnum
                    """), {"table": table_name})
                    comment_map = {row[0]: row[1] for row in comment_result.fetchall()}

                    # 构建外键映射
                    fk_map = {}
                    for fk in fk_constraints:
                        for col in fk["constrained_columns"]:
                            fk_map[col] = {
                                "table": fk["referred_table"],
                                "column": fk["referred_columns"][0]
                            }

                    # 构建唯一约束映射
                    unique_set = set()
                    for uc in unique_constraints:
                        for col in uc["column_names"]:
                            unique_set.add(col)

                    # 组装字段信息
                    column_defs = []
                    for col in columns:
                        col_info = {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col["nullable"],
                            "default": col.get("default"),
                            "comment": comment_map.get(col["name"], ""),
                            "primary_key": col["name"] in pk_columns,
                            "unique": col["name"] in unique_set,
                            "foreign_key": fk_map.get(col["name"])
                        }
                        column_defs.append(col_info)

                    schemas.append({
                        "table_name": table_name,
                        "columns": column_defs,
                        "primary_keys": pk_columns,
                        "foreign_keys": fk_constraints,
                        "indexes": indexes
                    })
                return schemas
        except Exception as e:
            Logger.error(e)
            raise ValueError("获取表结构失败")

    def execute_query(self, sql: str) -> Optional[tuple]:
        """查询一条记录"""
        with self.get_session() as session:
            result = session.execute(text(sql))
            return result.fetchone()

    def query_one(self, sql: str, params: dict = None) -> Optional[tuple]:
        """查询一条记录"""
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            return result.fetchone()


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
    tables = db.get_table_schema();
    print(f"Tables: {tables}")
    #tables_name = db.get_table_names();
    #print(f"tables_name:{tables_name}")
    tables_schema = db.get_table_schema();
    print(f"tables_schema:{tables_schema}")