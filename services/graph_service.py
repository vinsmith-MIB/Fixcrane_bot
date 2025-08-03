import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from collections import defaultdict, Counter
import logging
from matplotlib.font_manager import FontProperties
from pathlib import Path
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

class GraphService:
    def __init__(self, maintenance_service):
        self.maintenance_service = maintenance_service
        os.makedirs("output", exist_ok=True)

        # Gunakan font Mandarin agar karakter Cina tidak menjadi kotak
        font_path = Path("C:/Windows/Fonts/simsun.ttc")  # Ubah jika path berbeda
        self.chinese_font = FontProperties(fname=str(font_path))
        plt.switch_backend('Agg')
    

    def add_watermark(
        self, 
        ax, 
        watermark_path_center="assets/watermark-1.png", 
        watermark_path_bottom="assets/watermark-2.png",
        alpha=0.15, 
        scale=0.33
    ):
        """
        Menambahkan dua watermark ke grafik:
        - Watermark utama di tengah
        - Watermark sekunder di bawahnya
        """
        def add_image(path, position):
            if not os.path.exists(path):
                logging.warning(f"Watermark tidak ditemukan: {path}")
                return
            img = mpimg.imread(path)
            imagebox = OffsetImage(img, zoom=scale, alpha=alpha)
            ab = AnnotationBbox(
                imagebox,
                position,
                xycoords='axes fraction',
                frameon=False,
                box_alignment=(0.5, 0.5),
                zorder=10
            )
            ax.add_artist(ab)

        add_image(watermark_path_center, position=(0.5, 0.6))   # Tengah
        add_image(watermark_path_bottom, position=(0.5, 0.35))  # Bawah tengah




    def generate_graph(self, records, start_date=None, end_date=None, key=None):
        if not records:
            logging.warning("Tidak ada data maintenance untuk digrafikkan.")
            return None

        logging.info("Mulai membuat grafik jumlah fault per tanggal.")

        fault_per_date = defaultdict(int)
        fault_name_counter = Counter()
        

        # Konversi rentang tanggal
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Inisialisasi dictionary semua tanggal dalam rentang
        current_date = start
        while current_date <= end:
            fault_per_date[current_date] = 0
            current_date += timedelta(days=1)

        # Hitung jumlah fault per tanggal dan nama fault terpopuler
        for record in records:
            tanggal = record.tanggal
            fault_per_date[tanggal] += 1
            if hasattr(record, "fault_name") and record.fault_name:
                fault_name_counter[record.fault_name] += 1
            

        logging.debug("📊 Data Fault per Tanggal:")
        for tanggal, count in fault_per_date.items():
            logging.debug(f"{tanggal}: {count} fault(s), {key}")

        # Urutkan tanggal
        sorted_dates = sorted(fault_per_date.items(), key=lambda x: x[0])

        # Hitung grup
        total = len(sorted_dates)
        group_size = max(1, math.ceil(total / 20))
        chosen_dates = {}

        # Pilih 1 tanggal terbaik dari tiap grup
        for i in range(0, total, group_size):
            group = sorted_dates[i:i+group_size]
            if group:
                top_date = max(group, key=lambda x: x[1])
                chosen_dates[group[-1][0]] = top_date[1]
        # ...existing code...

        # Siapkan data untuk grafik
        top_dates = sorted(chosen_dates.items(), key=lambda x: x[0])
        labels = [date.strftime("%Y-%m-%d") for date, _ in top_dates]
        values = [count for _, count in top_dates]

        total_faults = sum(fault_per_date.values())
        average_per_day = total_faults / len(fault_per_date)
        most_common_fault, most_common_count = fault_name_counter.most_common(1)[0] if fault_name_counter else ("-", 0)

        logging.debug(f"Total Fault: {total_faults}")
        logging.debug(f"Rata-rata per hari: {average_per_day:.2f}")
        logging.debug(f"Fault paling sering: {most_common_fault} ({most_common_count}x)")

        try:
            plt.figure(figsize=(12, 7))
            bars = plt.bar(labels, values, color='coral')
            plt.xticks(rotation=45, ha='right', fontproperties=self.chinese_font)
            plt.xlabel('Tanggal', fontproperties=self.chinese_font)
            plt.ylabel('Jumlah Fault', fontproperties=self.chinese_font)

            title = (
                f'20 Tanggal Teratas dengan Fault "{most_common_fault}" Terbanyak\n({start_date} - {end_date})'
                if start_date and end_date else
                f'20 Tanggal Teratas dengan Fault "{most_common_fault}" Terbanyak'
            )
            plt.title(title, fontproperties=self.chinese_font)
            plt.suptitle(
                f"Crane: {records[0].crane_id}, Total: {total_faults} fault • Rata-rata: {average_per_day:.2f}/hari • Fault terbanyak: '{most_common_fault}' ({most_common_count}x)",
                fontsize=10,
                y=0.975,
                color="gray",
                fontproperties=self.chinese_font
            )

            plt.grid(axis='y', linestyle='--', alpha=0.7)

            for bar in bars:
                height = bar.get_height()
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 0.5,
                    str(height),
                    ha='center',
                    va='bottom',
                    fontsize=8,
                    fontproperties=self.chinese_font
                )

            file_path = f"output/fault_graph_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            plt.tight_layout(rect=[0, 0.03, 1, 1])
            self.add_watermark(plt.gca())
            plt.savefig(file_path, dpi=300)
            plt.close()
            logging.info(f"Grafik berhasil disimpan: {file_path}")
            return file_path

        except Exception as e:
            logging.error(f"Terjadi kesalahan saat membuat grafik: {e}")
            return None