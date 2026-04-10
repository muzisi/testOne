"""
数据库工具类 - 基于 SQLAlchemy 2.0
支持 MySQL 和 PostgreSQL
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


@dataclass
class DBConfig:
    """数据库配置"""
    host: str
    port: int
    database: str
    user: str
    password: str
    db_type: str = "mysql"  # "mysql" or "postgresql"

    def get_url(self) -> str:
        """获取数据库连接 URL"""
        if self.db_type == "mysql":
            return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == "postgresql":
            return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported db_type: {self.db_type}")


class MyDataSourceUtils:
    """数据库工具类，基于 SQLAlchemy 2.0"""

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

    def execute(self, sql: str, params: dict = None) -> int:
        """
        执行 SQL（增删改）

        Args:
            sql: SQL 语句（使用命名参数如 :name）
            params: 参数字典

        Returns:
            影响行数
        """
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            return result.rowcount

    def query_one(self, sql: str, params: dict = None) -> Optional[tuple]:
        """查询一条记录"""
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            return result.fetchone()

    def query_all(self, sql: str, params: dict = None) -> List[tuple]:
        """查询所有记录"""
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            return result.fetchall()

    def query_dict(self, sql: str, params: dict = None) -> List[Dict[str, Any]]:
        """查询所有记录（字典格式）"""
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

    # ============ 表信息相关操作 ============

    def get_tables(self) -> List[str]:
        """获取所有表名"""
        with self.get_session() as session:
            inspector = inspect(session.bind)
            return inspector.get_table_names()

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表字段信息"""
        with self.get_session() as session:
            inspector = inspect(session.bind)
            columns = inspector.get_columns(table_name)

            result = []
            for col in columns:
                result.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": col.get("default"),
                    "autoincrement": col.get("autoincrement", False),
                })
            return result

    def get_table_pk(self, table_name: str) -> List[str]:
        """获取表主键"""
        with self.get_session() as session:
            inspector = inspect(session.bind)
            pks = inspector.get_pk_constraint(table_name)
            return pks.get("constrained_columns", [])

    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表索引"""
        with self.get_session() as session:
            inspector = inspect(session.bind)
            indexes = inspector.get_indexes(table_name)

            result = []
            for idx in indexes:
                result.append({
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx["unique"],
                })
            return result

    def get_table_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表外键"""
        with self.get_session() as session:
            inspector = inspect(session.bind)
            fks = inspector.get_foreign_keys(table_name)

            result = []
            for fk in fks:
                result.append({
                    "name": fk.get("name"),
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"],
                })
            return result

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表完整信息（字段、主键、索引、外键）"""
        return {
            "table_name": table_name,
            "columns": self.get_table_columns(table_name),
            "primary_keys": self.get_table_pk(table_name),
            "indexes": self.get_table_indexes(table_name),
            "foreign_keys": self.get_table_foreign_keys(table_name),
        }

    def describe_table(self, table_name: str) -> List[Dict[str, Any]]:
        """描述表结构（类似 MySQL DESCRIBE 或 PgSQL \\d）"""
        return self.get_table_columns(table_name)

    def get_table_records(
        self,
        table_name: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取表记录"""
        sql = f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset"
        return self.query_dict(sql, {"limit": limit, "offset": offset})

    def get_table_count(self, table_name: str) -> int:
        """获取表记录数"""
        result = self.query_one(f"SELECT COUNT(*) FROM {table_name}")
        return result[0] if result else 0

    def close(self):
        """关闭引擎"""
        if self._engine:
            self._engine.dispose()
            self._engine = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        engine = self._get_engine()
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


# ============ 使用示例 ============
if __name__ == "__main__":
    # MySQL 配置
    mysql_config = DBConfig(
        host="localhost",
        port=3306,
        database="test_db",
        user="root",
        password="123456",
        db_type="mysql"
    )

    # PostgreSQL 配置
    pg_config = DBConfig(
        host="localhost",
        port=5432,
        database="test_db",
        user="postgres",
        password="123456",
        db_type="postgresql"
    )

    # 使用 PostgreSQL 示例
    print("=== PostgreSQL 示例 ===")
    with MyDataSourceUtils(pg_config) as db:
        # 查看所有表
        tables = db.get_tables()
        print(f"Tables: {tables}")

        if tables:
            table_name = tables[0]

            # 描述表结构
            print(f"\n--- Describe {table_name} ---")
            desc = db.describe_table(table_name)
            for col in desc:
                print(f"  {col['name']}: {col['type']} (nullable: {col['nullable']})")

            # 查看完整表信息
            print(f"\n--- Table Info: {table_name} ---")
            info = db.get_table_info(table_name)
            print(f"Primary Keys: {info['primary_keys']}")
            print(f"Indexes: {info['indexes']}")
            print(f"Foreign Keys: {info['foreign_keys']}")

            # 查看记录数
            count = db.get_table_count(table_name)
            print(f"\nRecord count: {count}")
