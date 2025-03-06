import pandas as pd
from FixedCrane import FixedCrane
from datetime import datetime
import os
from Problem import Problem

# Dictionary global untuk menyimpan tanggal dalam array 2D
date_dict = {}

class CSV:
    def __init__(self, file_to_read):
        self.file_trd = file_to_read

    def read(self):
        df = pd.read_csv(self.file_trd, encoding="utf-16", sep="\t")
        df_list = df['CONTENT']

        for index, i in enumerate(df_list):
            pb = Problem(i)
            pb.add_value()
            
            if index == len(df_list) - 1:  
                pb_list = pb.get_all()

                # Ambil nama file tanpa ekstensi
                file_name = os.path.basename(self.file_trd)  # Misalnya: "20241115.csv"
                date_str, ext = os.path.splitext(file_name)  # date_str = "20241115"

                try:
                    # Konversi string tanggal ke format datetime
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    formatted_date = date_obj.strftime("%d-%m-%Y")  # Format menjadi "DD-MM-YYYY"
                except ValueError:
                    raise ValueError(f"Format nama file tidak sesuai: {file_name}")

                # Ambil direktori tempat file berada
                dir_path = os.path.dirname(self.file_trd)  

                # Ambil bagian terakhir dari path (nama folder sebelum file)
                folder_name = os.path.basename(dir_path)

                # Tambahkan ke dictionary global
                if folder_name not in date_dict:
                    date_dict[folder_name] = []  # Inisialisasi jika belum ada
                
                date_dict[folder_name].append([formatted_date])  # Tambahkan dalam format array 2D

                # Tambahkan ke FixedCrane
                FixedCrane.add_to_dict(FixedCrane(folder_name, formatted_date, pb_list))
                
                pb.reset_all()
