import zipfile
import csv
import os
import re
from datetime import datetime
import io
from database.models import MaintenanceRecord


class ZipParserService:
    def __init__(self, maintenance_service, folder_pattern=None):
        self.maintenance_service = maintenance_service
        # Default pattern: any folder containing fc (case insensitive)
        self.folder_pattern = folder_pattern or r'.*fc.*'

    def parse_zip(self, zip_path: str):
        print(f"Membuka file ZIP: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for file_info in zf.infolist():
                print(f"Ditemukan file: {file_info.filename}")

                # Hanya proses file CSV
                if not file_info.filename.endswith('.csv'):
                    continue
                    
                folder, filename = os.path.split(file_info.filename)
                folder_lower = folder.lower()
                
                # Cek apakah folder sesuai dengan pattern yang ditentukan
                pattern_match = re.search(self.folder_pattern.lower(), folder_lower)
                if not pattern_match:
                    print(f"Lewati file {file_info.filename} karena tidak sesuai pattern '{self.folder_pattern}'")
                    continue

                # Ekstrak crane_id dari nama folder - berbagai format
                # Pattern 1: fc01, fc02, dll (tanpa spasi)
                crane_match = re.search(r'fc\s*(\d+)', folder_lower)
                
                # Pattern 2: fc 01, fc 02, dll (dengan spasi)
                if not crane_match:
                    crane_match = re.search(r'fc\s+(\d+)', folder_lower)
                
                # Pattern 3: untuk folder seperti "FC 01", "FC01" dengan leading zero
                if not crane_match:
                    crane_match = re.search(r'fc\s*0*(\d+)', folder_lower)
                
                if not crane_match:
                    print(f"Gagal mengekstrak crane ID dari {folder}")
                    continue
                crane_id = int(crane_match.group(1))
                print(f"Crane ID: {crane_id}")

                # Ambil tanggal dari nama file
                tanggal_str = os.path.splitext(filename)[0]
                try:
                    tanggal = datetime.strptime(tanggal_str, "%Y%m%d").date().isoformat()
                    print(f"Tanggal dari file: {tanggal}")
                except ValueError:
                    print(f"Format tanggal tidak sesuai: {tanggal_str}")
                    tanggal = tanggal_str

                # Baca dan parse isi CSV
                with zf.open(file_info) as f:
                    try:
                        decoded_text = f.read().decode('utf-16')
                        print("Contoh isi file:", repr(decoded_text[:200]))
                    except UnicodeDecodeError as e:
                        print(f"Gagal decode file {filename}: {e}")
                        continue

                decoded_file = io.StringIO(decoded_text, newline=None)

                # Coba baca preview untuk deteksi header
                try:
                    preview = list(csv.reader(decoded_file, delimiter="\t"))
                    print(f"Jumlah baris di preview: {len(preview)}")
                except Exception as e:
                    print(f"Gagal membaca CSV: {e}")
                    continue

                if not preview:
                    print("File CSV kosong, lewati.")
                    continue

                first_row = preview[0]
                header = "waktu" in first_row and "act" in first_row and "fault_name" in first_row
                print(f"Header CSV: {first_row} | Menggunakan DictReader: {header}")

                # Reset pointer ke awal
                decoded_file.seek(0)
                reader = csv.DictReader(decoded_file, delimiter='\t') if header else csv.reader(decoded_file, delimiter='\t')

                if not header:
                    next(reader, None)  # Lewati header jika bukan DictReader

                for row in reader:
                    try:
                        fault_name = ''
                        if header:
                            waktu = row.get('waktu', '').strip()
                            act = int(row.get('act', 0))
                            fault_name = row.get('fault_name', '').strip()
                        else:
                            if len(row) >= 3:
                                waktu = row[0].strip()
                                act = int(row[1])
                                fault_name = row[2].strip()
                            else:
                                print(f"Baris tidak valid (kurang kolom): {row}")
                                continue

                        fault_ref = self.maintenance_service.get_fault_reference_by_name(fault_name)
                        print(f"Menambahkan record: {waktu}, {act}, {fault_name}, {crane_id}, {fault_ref.fault_id}")
                        record = MaintenanceRecord(tanggal, waktu, act, fault_name, crane_id, fault_ref)
                        self.maintenance_service.add_record(record)

                    except Exception as e:
                        print(f"Kesalahan parsing baris: {row} - {e}")


# Contoh penggunaan dengan berbagai pattern dinamis
"""
Contoh penggunaan:

# 1. Pattern default: any folder containing fc
parser = ZipParserService(maintenance_service)

# 2. Pattern untuk folder load/fc
parser = ZipParserService(maintenance_service, r'load/fc')

# 3. Pattern untuk folder yang mengandung fc di mana saja
parser = ZipParserService(maintenance_service, r'.*fc.*')

# 4. Pattern untuk folder dengan format bulan/FC
parser = ZipParserService(maintenance_service, r'.*\w+/fc.*')

# 5. Pattern untuk folder dengan nomor bulan/FC
parser = ZipParserService(maintenance_service, r'.*\d+\..*fc.*')

# Contoh struktur folder yang akan match:
# - load/fc01/  ✓
# - data/fc02/  ✓
# - 3. Maret/FC 01/  ✓
# - 1. Januari/FC01/  ✓
# - March/FC 05/  ✓
# - backup/load/fc04/  ✓
# - temp/FC 10/  ✓
# - maintenance/fc 06/  ✓
# - 12. Desember/FC 20/  ✓

# Crane ID yang bisa diekstrak:
# - fc01 → 1
# - fc 01 → 1
# - FC 01 → 1
# - fc001 → 1
# - FC 10 → 10
# - fc 20 → 20
"""