from collections import defaultdict

# Dictionary utama untuk menyimpan data
dictionary = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

class FixedCrane:
    def __init__(self, fixedCraneIndex, date, problem):
        self.fixedCraneIndex = fixedCraneIndex
        self.date = date
        self.problem = problem

    @staticmethod
    def add_to_dict(obj):
        """ Menambahkan objek FixedCrane ke dictionary """
        
        for problem in obj.problem:
            dictionary[obj.fixedCraneIndex][problem.name][obj.date] += problem.value  # Pastikan += agar tidak overwrite
        

    @staticmethod
    def sort_object():
        """ Mengurutkan dictionary berdasarkan FixedCraneIndex → Problem → Tanggal dengan format yang benar """
        for index, problems in dictionary.items():  # Iterasi berdasarkan FixedCraneIndex
            for problem, dates in problems.items():  # Iterasi berdasarkan problem dalam FixedCraneIndex
                for date in sorted(dates.keys(), key=lambda d: tuple(map(int, d.split('-')))):  # Urutkan tanggal numerik
                    print(f"Crane: {index}, Problem: {problem}, Date: {date}, Count: {dates[date]}")




        
    
    
        
    
        
        
    
    
        