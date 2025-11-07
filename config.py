import os

token = os.getenv("token")

if not token:
    print("⚠️ Token tapılmadı! Railway Variables hissəsini yoxla.")
else:
    print("✅ Token uğurla tapıldı!")
'
DATABASE = 'db.db'
DB_FILE = "photoandvideo.db"
