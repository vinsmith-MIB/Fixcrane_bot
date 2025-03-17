class Problem:
    _instances = {}  # Dictionary untuk menyimpan objek dengan nama unik
    
    def __new__(cls, name):
        if name in cls._instances:
            return cls._instances[name]  # Jika sudah ada, kembalikan objek yang sama
        else:
            instance = super().__new__(cls)
            cls._instances[name] = instance  # Simpan objek baru dalam dictionary
            return instance

    def __init__(self, name, value=0):
        if not hasattr(self, 'initialized'):  # Agar __init__ hanya dipanggil sekali per objek unik
            self.name = name
            self.value = value
            self.initialized = True

    def add_value(self):
        print(f"addvalue = {self.name}   {self.value}")
        self.value += 1
    
    @classmethod
    def get_all(cls):
        """Mengembalikan semua objek yang telah dibuat dalam bentuk array/list"""
        return list(cls._instances.values())

    @classmethod
    def reset_all(cls):
        """Menghapus semua objek Problem yang sudah dibuat."""
        cls._instances.clear()  # Menghapus semua instance dari dictionary

