class MaintenanceRecord:
    def __init__(self, tanggal, waktu, act, fault_name, crane_id, fault_reference=None):
        self.tanggal = tanggal
        self.waktu = waktu
        self.act = act
        self.fault_name = fault_name
        self.crane_id = crane_id
        self.fault_reference = fault_reference  # Objek FaultReference

    @property
    def fault_id(self):
        return self.fault_reference.fault_id if self.fault_reference else None

    def to_tuple(self):
        return (
            self.tanggal,
            self.waktu,
            self.act,
            self.fault_name,
            self.crane_id,
            self.fault_id 
        )

    def __repr__(self):
        return (f"MaintenanceRecord(tanggal='{self.tanggal}', waktu='{self.waktu}', "
                f"act='{self.act}', fault_name='{self.fault_name}', "
                f"crane_id='{self.crane_id}', fault_id={self.fault_id})")

    
class FaultReference:
    def __init__(self,fault_id, code_fault, fault_name):
        self.fault_id = fault_id
        self.code_fault = code_fault
        self.fault_name = fault_name
        
    def to_tuple(self):
        return (self.fault_id, self.code_fault, self.fault_name)
    
    def __repr__(self):
        return (f"FaultReference(fault_id='{self.fault_id}', code_fault='{self.code_fault}', fault_name='{self.fault_name}')")
