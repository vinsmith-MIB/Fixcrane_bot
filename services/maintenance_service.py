# services/maintenance_service.py
from database.db_manager import DBManager
from database.models import MaintenanceRecord, FaultReference
from datetime import datetime, timedelta, date
from typing import List, Optional
import logging
import re
import csv
import calendar

logger = logging.getLogger(__name__)

class MaintenanceService:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager
        self.create_table()
        
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS maintenance_records (
            id SERIAL PRIMARY KEY,
            tanggal DATE,
            waktu TIME,
            act INTEGER,
            fault_name TEXT,
            crane_id INTEGER,
            fault_id INTEGER
        );
        """
        self.db_manager.execute(query)
        
    def add_record(self, record: MaintenanceRecord):
        query = """
        INSERT INTO maintenance_records (tanggal, waktu, act, fault_name, crane_id, fault_id)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        self.db_manager.execute(query, record.to_tuple())
    
    def get_all_records(self):
        query = "SELECT * FROM maintenance_records;"
        return self.db_manager.fetchall_dict(query)

    # ======================= METODE BARU UNTUK BULK OPERATIONS =======================
    def get_all_records_by_date_range(self, start_date: str, end_date: str) -> List[MaintenanceRecord]:
        """Mengambil semua record dalam rentang tanggal tertentu"""
        query = """
        SELECT mr.*, fr.code_fault, fr.fault_name AS fault_ref_name
        FROM maintenance_records mr
        LEFT JOIN fault_references fr ON mr.fault_id = fr.fault_id
        WHERE mr.tanggal BETWEEN %s AND %s;
        """
        rows = self.db_manager.fetchall_dict(query, (start_date, end_date))
        return [self._row_to_maintenance_record(row) for row in rows]

    def get_all_records_by_date_and_fault(self, start_date: str, end_date: str, fault_id: int) -> List[MaintenanceRecord]:
        """Mengambil semua record dalam rentang tanggal untuk fault tertentu"""
        query = """
        SELECT mr.*, fr.code_fault, fr.fault_name AS fault_ref_name
        FROM maintenance_records mr
        LEFT JOIN fault_references fr ON mr.fault_id = fr.fault_id
        WHERE mr.tanggal BETWEEN %s AND %s AND mr.fault_id = %s;
        """
        rows = self.db_manager.fetchall_dict(query, (start_date, end_date, fault_id))
        return [self._row_to_maintenance_record(row) for row in rows]

    def get_all_records_by_date_and_crane(self, start_date: str, end_date: str, crane_id: int) -> List[MaintenanceRecord]:
        """Mengambil semua record dalam rentang tanggal untuk crane tertentu"""
        query = """
        SELECT mr.*, fr.code_fault, fr.fault_name AS fault_ref_name
        FROM maintenance_records mr
        LEFT JOIN fault_references fr ON mr.fault_id = fr.fault_id
        WHERE mr.tanggal BETWEEN %s AND %s AND mr.crane_id = %s;
        """
        rows = self.db_manager.fetchall_dict(query, (start_date, end_date, crane_id))
        return [self._row_to_maintenance_record(row) for row in rows]

    def _row_to_maintenance_record(self, row: dict) -> MaintenanceRecord:
        """Helper untuk mengkonversi row database ke objek MaintenanceRecord"""
        fault_ref = FaultReference(
            fault_id=row['fault_id'],
            code_fault=row.get('code_fault'),
            fault_name=row.get('fault_ref_name') or row['fault_name']
        )
        
        return MaintenanceRecord(
            tanggal=row['tanggal'],
            waktu=row['waktu'],
            act=row['act'],
            fault_name=row['fault_name'],
            crane_id=row['crane_id'],
            fault_reference=fault_ref
        )

    # ======================= METODE DELETE BULK =======================
    def delete_all_records_by_date_range(self, start_date: str, end_date: str) -> int:
        """Menghapus semua record dalam rentang tanggal"""
        query = "DELETE FROM maintenance_records WHERE tanggal BETWEEN %s AND %s;"
        return self.db_manager.execute(query, (start_date, end_date)).rowcount

    def delete_all_records_by_date_and_fault(self, start_date: str, end_date: str, fault_id: int) -> int:
        """Menghapus semua record dalam rentang tanggal untuk fault tertentu"""
        query = "DELETE FROM maintenance_records WHERE tanggal BETWEEN %s AND %s AND fault_id = %s;"
        return self.db_manager.execute(query, (start_date, end_date, fault_id)).rowcount

    def delete_all_records_by_crane_and_date_range(self, crane_id: int, start_date: str, end_date: str) -> int:
        """Menghapus semua record dalam rentang tanggal untuk crane tertentu"""
        query = "DELETE FROM maintenance_records WHERE crane_id = %s AND tanggal BETWEEN %s AND %s;"
        return self.db_manager.execute(query, (crane_id, start_date, end_date)).rowcount

    # ======================= METODE LAINNYA =======================
    def get_records_by_date_and_id_crane_and_id_fault(
        self, 
        start_date: str, 
        end_date: str, 
        crane_id: int, 
        fault_id: int
    ) -> List[MaintenanceRecord]:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        query = """
        SELECT mr.*, fr.code_fault, fr.fault_name AS fault_ref_name
        FROM maintenance_records mr
        LEFT JOIN fault_references fr ON mr.fault_id = fr.fault_id
        WHERE mr.tanggal BETWEEN %s AND %s
            AND mr.crane_id = %s 
            AND mr.fault_id = %s
        ORDER BY mr.tanggal, mr.waktu ASC;
        """
        rows = self.db_manager.fetchall_dict(query, (start_date_obj, end_date_obj, crane_id, fault_id))

        filtered_data = []
        last_seen = {}

        for row in rows:
            timestamp_str = f"{row['tanggal']} {row['waktu']}"
            current_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

            last_time = last_seen.get(row['fault_name'])
            if last_time and (current_time - last_time) <= timedelta(minutes=1):
                continue

            record = self._row_to_maintenance_record(row)
            filtered_data.append(record)
            last_seen[row['fault_name']] = current_time

        return filtered_data

    def get_all_year(self, crane_id: int) -> List[dict]:
        query = """
        SELECT DISTINCT EXTRACT(YEAR FROM tanggal)::INT AS tahun
        FROM maintenance_records
        WHERE crane_id = %s
        ORDER BY tahun;
        """
        return self.db_manager.fetchall_dict(query, (crane_id,))
    
    def get_all_crane_id(self) -> List[dict]:
        query = "SELECT DISTINCT crane_id FROM maintenance_records ORDER BY crane_id;"
        return self.db_manager.fetchall_dict(query)

    def add_fault(self, filename: str):
        datas = []
        with open(filename, 'r', encoding='utf-16') as file:
            reader = csv.reader(file, delimiter='\t')
            for i, row in enumerate(reader):
                if i >= 2 and len(row) > 6:
                    datas.append(row[6].strip())

        for data in datas:
            match = re.match(r"\((.*?)\)(.+)", data)
            if match:
                kode_fault = match.group(1).strip()
                fault_name = match.group(2).strip()
            else:
                kode_fault = "Nan"
                fault_name = data

            query = """
            INSERT INTO fault_references (code_fault, fault_name)
            VALUES (%s, %s)
            ON CONFLICT (code_fault, fault_name) DO NOTHING;
            """
            self.db_manager.execute(query, (kode_fault, fault_name))
        
    def get_all_faults(self, crane_id, start_date, end_date) -> List[FaultReference]:

        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        query = """
        SELECT DISTINCT fault_id, fault_name 
        FROM maintenance_records
        WHERE tanggal BETWEEN %s AND %s
        AND crane_id = %s
        """
        rows = self.db_manager.fetchall_dict(query, [start_date_obj, end_date_obj, crane_id])
        return [
            FaultReference(
                fault_id=row['fault_id'],
                code_fault=None, 
                fault_name=row['fault_name']
            ) for row in rows
        ]
        
    def search_faults_by_keyword(self, keyword: str) -> List[FaultReference]:
        if not keyword:
            return []
        
        sql = """
        SELECT fault_id, code_fault, fault_name
        FROM fault_references
        WHERE code_fault ILIKE %s
            OR fault_name ILIKE %s
            OR CAST(fault_id AS TEXT) ILIKE %s
        LIMIT 50;
        """
        kw = f"%{keyword}%"
        rows = self.db_manager.fetchall_dict(sql, (kw, kw, kw))
        return [FaultReference(**row) for row in rows]

    def delete_records_by_ids(self, record_ids: List[int]) -> int:
        if not record_ids:
            return 0

        placeholders = ','.join(['%s'] * len(record_ids))
        query = f"DELETE FROM maintenance_records WHERE id IN ({placeholders});"
        return self.db_manager.execute(query, record_ids).rowcount

    def delete_records_by_date_and_id_crane_and_id_fault(self, start_date: str, end_date: str, crane_id: int, fault_id: int) -> int:
        """
        Menghapus records maintenance berdasarkan tanggal, crane_id, dan fault_id
        Args:
            start_date (str): Tanggal mulai dalam format 'YYYY-MM-DD'
            end_date (str): Tanggal akhir dalam format 'YYYY-MM-DD'
            crane_id (int): ID crane
            fault_id (int): ID fault
        Returns:
            int: Jumlah record yang berhasil dihapus
        """
        query = """
            DELETE FROM maintenance_records 
            WHERE tanggal BETWEEN %s AND %s 
            AND crane_id = %s 
            AND fault_id = %s;
        """
        return self.db_manager.execute(query, (start_date, end_date, crane_id, fault_id)).rowcount
    
    
    """ FAULT DATABASE """
    
    def get_fault_reference_by_name(self, fault_name: str) -> Optional[FaultReference]:
        """
        Mengambil satu objek FaultReference dari database berdasarkan fault_name.
        Jika tidak ditemukan, akan mengembalikan None.
        """
        fault_query = re.sub(r"\(.*?\)", "", fault_name).strip()
        
        query = """
            SELECT fault_id, code_fault, fault_name
            FROM fault_references
            WHERE fault_name = %s
            LIMIT 1
        """
        results = self.db_manager.fetchall(query, (fault_query.strip(),))
        logging.info(f"Query results: {results} string preferences: {fault_query.strip()}")
        if results:
            fault_id, code_fault, fault_query = results[0]
            return FaultReference(
                fault_id=fault_id,
                code_fault=code_fault,
                fault_name=fault_query,
            )
        return None