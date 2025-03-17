import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
from matplotlib.font_manager import FontProperties
from pathlib import Path
from ReadExcel import date_dict
import os


class Chart:
    def __init__(self, dictionary):
        """ Konstruktor menerima dictionary utama yang berisi data FixedCrane """
        self.dictionary = dictionary

    
    def plot_problems(self):
        for crane, problems in self.dictionary.items():
            for problem_name, date_counts in problems.items():
                # Buat folder berdasarkan nama problem
                problem_folder = f"grafik/{crane}/{problem_name}"
                os.makedirs(problem_folder, exist_ok=True)

                # Dictionary untuk menyimpan data berdasarkan bulan
                monthly_data = {}

                # Konversi tanggal yang ada di date_counts ke datetime
                dates_dt = [datetime.datetime.strptime(date, "%d-%m-%Y") for date in date_counts.keys()]
                counts = [date_counts[date] for date in date_counts.keys()]

                # Ambil semua tanggal dari date_dict sesuai crane yang sedang diproses
                if crane in date_dict:
                    all_dates = [datetime.datetime.strptime(date[0], "%d-%m-%Y") for date in date_dict[crane]]
                else:
                    all_dates = []

                # Tambahkan tanggal dari date_dict yang belum ada di dates_dt
                for dt in all_dates:
                    if dt not in dates_dt:
                        dates_dt.append(dt)
                        counts.append(0)

                # Urutkan berdasarkan tanggal setelah ditambahkan
                sorted_data = sorted(zip(dates_dt, counts))
                dates_dt, counts = zip(*sorted_data)

                # Pisahkan data berdasarkan bulan
                for date_obj, count in zip(dates_dt, counts):
                    month = int(date_obj.strftime("%Y%m"))  # Ambil bulan dalam bentuk angka (1-12)

                    if month not in monthly_data:
                        monthly_data[month] = ([], [])

                    monthly_data[month][0].append(date_obj)  # Tambahkan tanggal
                    monthly_data[month][1].append(count)     # Tambahkan jumlah

                # Path ke font Mandarin
                font_path = Path("C:/Windows/Fonts/simsun.ttc")
                ChineseFont1 = FontProperties(fname=str(font_path))

                # Buat grafik untuk setiap bulan yang tersedia
                for month, (dates_dt, counts) in monthly_data.items():
                    plt.figure(figsize=(15, 10))

                    # Plot data
                    plt.plot(dates_dt, counts, linestyle='-', label=f"{problem_name}")

                    # Tambahkan elemen visualisasi dengan font Mandarin
                    plt.title(f"Crane: {crane} - Problem: {problem_name} - Bulan {month}", fontproperties=ChineseFont1)
                    plt.xlabel("Tanggal")
                    plt.ylabel("Jumlah Problem")
                    plt.xticks(rotation=45)
                    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
                    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
                    plt.legend(title="Problem Type", prop=ChineseFont1)
                    plt.grid(True, linestyle="--", alpha=0.7)
                    
                    temp_file = datetime.datetime.strptime(str(month), "%Y%m")  # Konversi ke datetime
                    formatted_month = temp_file.strftime("%Y-%m")  # Format menjadi YYYY-MM

                    plt.savefig(f"{problem_folder}/{formatted_month}.svg", dpi=600, bbox_inches="tight")


                    plt.close()

                    print(f"📊 Grafik bulan {month} untuk problem '{problem_name}' telah disimpan di {problem_folder}/{month}.svg")
