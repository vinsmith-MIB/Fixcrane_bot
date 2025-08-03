from datetime import datetime

class MaintenanceDataRequestValidator:
    def __init__(self, maintenance_service):
        self.maintenance_service = maintenance_service
        self.errors = []
        self.start_date_dt = None
        self.end_date_dt = None

    def validate(self, start_date: str, end_date: str, id_crane: str, fault: str) -> bool:
        self.errors.clear()
        self.start_date_dt = self._parse_date(start_date, label="mulai")
        self.end_date_dt = self._parse_date(end_date, label="akhir")

        if self.start_date_dt and self.end_date_dt:
            if self.start_date_dt > self.end_date_dt:
                self.errors.append("📅 Tanggal mulai tidak boleh lebih besar dari tanggal akhir.")

        if not id_crane.isdigit():
            self.errors.append(f"🚧 ID crane harus berupa angka: {id_crane}")

        if not self._validate_fault(fault):
            self.errors.append(f"⚠️ Fault `{fault}` tidak ditemukan.")

        return not self.errors

    def _parse_date(self, date_str: str, label="") -> datetime:
        try:
            return datetime.strptime(date_str, "%d-%m-%Y")
        except ValueError:
            self.errors.append(f"📅 Tanggal {label} tidak valid: {date_str}")
            return None

    def _validate_fault(self, fault: str) -> bool:
        if fault.isdigit():
            return self.maintenance_service.get_fault_by_id(int(fault)) is not None
        else:
            return bool(self.maintenance_service.search_faults_by_keyword(fault))

    def get_errors(self) -> list:
        return self.errors
