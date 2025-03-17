import pandas as pd
from FixedCrane import FixedCrane
from datetime import datetime, timedelta
import os
from Problem import Problem

# Dictionary global untuk menyimpan tanggal dalam array 2D
date_dict = {}

class CSV:
    def __init__(self, file_to_read):
        self.file_trd = file_to_read

    def read(self):
        df = pd.read_csv(self.file_trd, encoding="utf-16", sep="\t")
        df_list = df[['TIME', 'CONTENT']]
        
        # Dictionary untuk menyimpan max_time per content
        max_time_dict = {}

        for index, (time_str, content) in enumerate(df_list.values):
            try:
                # Pastikan time_str adalah string dan memiliki format HH:MM:SS
                if not isinstance(time_str, str):
                    time_str = str(time_str).strip()
                
                if time_str.count(":") != 2:
                    print(f"SKIPPED: Baris ke-{index} tidak memiliki format HH:MM:SS → {time_str}")
                    continue  # Lewati baris jika format tidak sesuai

                # Konversi string waktu ke datetime object
                time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
                print(f"DEBUG: Parsed time → {time_obj}")

                pb = Problem(content)
                
                # Ambil max_time yang sesuai dengan content, jika belum ada, inisialisasi
                if content not in max_time_dict:
                    max_time_dict[content] = None

                if max_time_dict[content] is None:
                    # Jika belum ada max_time untuk content ini, simpan pertama kali
                    max_time_dict[content] = time_obj
                    # print(f"{content}  {time_obj} max time = {max_time_dict[content]}")
                    pb.add_value()
                elif (
                    datetime.combine(datetime.today(), time_obj) >=
                    datetime.combine(datetime.today(), max_time_dict[content]) + timedelta(minutes=1)
                ):  
                    # Jika lebih dari 1 menit dari max_time yang sudah tercatat untuk content ini
                    max_time_dict[content] = time_obj  # Update max_time untuk content
                    pb.add_value()
                    # print(f"{content}  {time_obj} max time = {max_time_dict[content]}")
                else:
                    # print(f"SKIPPED: Waktu terlalu dekat dengan sebelumnya → {time_str}")
                    # print(f"{content}  {time_obj} max time = {max_time_dict[content]}")
                    continue  # Skip iterasi jika kurang dari 1 menit

            except ValueError:
                print(f"ERROR: Format waktu tidak valid → {time_str}")  # Debugging jika ada error

            # Jika ini iterasi terakhir
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
                    raise ValueError(f"ERROR: Format nama file tidak sesuai → {file_name}")

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
