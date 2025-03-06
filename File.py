import rarfile
import os
from ReadExcel import CSV
from FixedCrane import FixedCrane,dictionary
from Chart import Chart



class File:
    
    @staticmethod
    def extract_rar(rar_path="downloads/load.rar", extract_path="hasil_ekstrak"):
        """Ekstrak file RAR ke folder tujuan."""
        if not os.path.exists(rar_path):
            print(f"File RAR tidak ditemukan: {rar_path}")
            return
        
        try:
            # Pastikan unrar tersedia
            if not rarfile.is_rarfile(rar_path):
                print(f"File bukan RAR yang valid: {rar_path}")
                return

            # Membuka file RAR
            with rarfile.RarFile(rar_path) as rar:
                os.makedirs(extract_path, exist_ok=True)  # Buat folder jika belum ada
                rar.extractall(path=extract_path)
                print(f"File berhasil diekstrak ke: {extract_path}")

        except rarfile.Error as e:
            print(f"Terjadi kesalahan saat mengekstrak: {e}")\
    
    def folder_iteration():
        folder_path = "hasil_ekstrak"  # Ganti dengan path folder utama

        for root, dirs, files in os.walk(folder_path, topdown=True):
            # Hanya cetak nama folder jika tidak berada di root utama
            if root != folder_path:
                os.path.basename(root)
                
            # Cetak nama file dalam folder
            for file_name in sorted(files): 
                csv = CSV(f'{root}/{file_name}')
                csv.read()
        
        Chart.plot_problems(Chart(dictionary))
        
File.extract_rar()   
File.folder_iteration()



