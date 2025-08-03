#db_manager.py
import psycopg2
from psycopg2 import pool
from typing import Any, List, Tuple
from psycopg2.extras import RealDictCursor

class DBManager:
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.pool: pool.SimpleConnectionPool = None
        self.initialize_pool()
    
    def initialize_pool(self) -> None:
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(1, 10, **self.db_config)
            if not self.pool:
                print("Gagal membuat connection pool")
                self.pool = None
        except Exception as e:
            print(f"Error initializing connection pool: {e}")
            self.pool = None

    def get_conn(self):
        # Coba inisialisasi pool jika belum ada
        if self.pool is None:
            self.initialize_pool()
            if self.pool is None:
                raise Exception("Database connection pool is not available. Pastikan database sudah berjalan.")
        return self.pool.getconn()
    
    def put_conn(self, conn) -> None:
        self.pool.putconn(conn)
        
    def execute(self, query: str, params: Tuple[Any, ...] = ()) -> Any:
        conn = self.get_conn()
        try: 
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.put_conn(conn)

    def fetchone(self, query: str, params: Tuple[Any, ...] = ()) -> Tuple[Any, ...] | None:
        cursor = self.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        return result
            
    def fetchall(self, query: str,params: Tuple[Any, ...] = ()) -> List[Tuple[Any, ...]]:
        cursor = self.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        return results
    

    def fetchall_dict(self, query: str, params: Tuple[Any, ...] = ()) -> List[dict]:
        conn = self.get_conn()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.put_conn(conn)

    
    def close_all(self) -> None:
        if self.pool:
            self.pool.closeall()


