# Bunda Care Server

Backend API untuk aplikasi Bunda Care dibangun menggunakan Flask.

## Prasyarat

- Python 3.8+
- MySQL atau PostgreSQL (sesuaikan di `.env`)
- Virtual Environment (direkomendasikan)

## Cara Instalasi

1. **Clone repository ini** (jika belum):
   ```bash
   git clone <repository-url>
   cd bunda_care_server
   ```

2. **Buat dan aktifkan Virtual Environment**:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instal dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

## Konfigurasi

1. Salin file `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```
2. Sesuaikan variabel di dalam `.env` (Database URI, Google Client ID, Secret Key, dll).

## Database Migration

Meskipun menggunakan database cloud (seperti Neon atau RDS), Anda tetap perlu membuat struktur tabel pada database yang masih kosong:

```bash
# Menjalankan migrasi untuk membuat/memperbarui tabel
flask db upgrade
```

**Catatan**: Pastikan `SQLALCHEMY_DATABASE_URI` di file `.env` sudah mengarah ke URL database cloud Anda.

## Membuat Akun Admin (Opsional)

Untuk membuat user admin pertama kali, jalankan script berikut setelah konfigurasi `.env` lengkap:
```bash
python create_admin.py
```

## Menjalankan Aplikasi

Jalankan server dalam mode development:

```bash
python app.py
```

Server akan berjalan di `http://localhost:5000`.

## Fitur Utama

- **Autentikasi**: Login tradisional dan Google OAuth.
- **Meal Tracking**: Pencatatan riwayat makan (Meal Log).
- **Food Scanning**: Deteksi makanan menggunakan AI (Ultralytics/YOLO).
- **Rekomendasi**: Sistem rekomendasi makanan sehat.
- **Admin Panel**: Manajemen menu dan user untuk administrator.

## Struktur Folder Utama

- `app/`: Source code utama aplikasi.
- `app/models/`: Definisi skema database (SQLAlchemy).
- `app/routes/`: Definisi endpoint API.
- `migrations/`: File migrasi database.
- `requirements.txt`: Daftar package Python yang dibutuhkan.
- `config.py`: Konfigurasi aplikasi.
