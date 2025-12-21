import os
from sqlalchemy import create_engine, MetaData, Table, text, inspect
from sqlalchemy.orm import sessionmaker

# --- CONFIGURATION ---
# URI MySQL Lokal Anda (Sumber Data)
SOURCE_URI = "mysql+pymysql://root:boyblanco@localhost:3306/bunda_care"

# URI PostgreSQL Neon (Target Data)
TARGET_URI = "postgresql://neondb_owner:npg_Ld6OCEHQv9PF@ep-round-credit-a199lu0f-pooler.ap-southeast-1.aws.neon.tech/bunda_care?sslmode=require&channel_binding=require"

# Urutan tabel sangat penting karena Foreign Keys!
# Parent tables harus diisi dulu sebelum Child tables.
TABLES_ORDER = [
    'roles',
    'food_ingredients',
    'food_menus',
    'users',               # Depends on roles
    'food_menu_ingredients', # Depends on menus, ingredients
    'user_preferences',    # Depends on users
    'food_meal_logs',      # Depends on users
    'food_meal_log_items'  # Depends on logs, menus
]

def migrate_data():
    print("🚀 Memulai Migrasi Data dari MySQL ke PostgreSQL Neon...")
    
    # 1. Koneksi
    try:
        source_engine = create_engine(SOURCE_URI)
        target_engine = create_engine(TARGET_URI)
        
        # Test connections
        with source_engine.connect() as c: c.execute(text("SELECT 1"))
        with target_engine.connect() as c: c.execute(text("SELECT 1"))
        print("✅ Koneksi ke kedua database berhasil.")
        
    except Exception as e:
        print(f"❌ Error koneksi: {e}")
        return

    # 2. Reflect Metadata (Membaca struktur tabel otomatis)
    print("📖 Membaca schema database...")
    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)
    
    target_meta = MetaData()
    target_meta.reflect(bind=target_engine)

    # 3. Proses Transfer
    with target_engine.connect() as target_conn:
        # Gunakan transaction agar aman
        trans = target_conn.begin()
        
        try:
            # A. Bersihkan data lama di Target (Optional tapi disarankan agar tidak duplicate key error)
            print("\n🧹 Membersihkan tabel target (TRUNCATE) agar bersih...")
            # Kita reverse order untuk delete agar tidak kena FK constraint
            for table_name in reversed(TABLES_ORDER):
                if table_name in target_meta.tables:
                    print(f"   - Emptying {table_name}...")
                    # CASCADE diperlukan di Postgres untuk handle FK
                    target_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))

            # B. Copy Data
            print("\n📦 Menyalin data...")
            for table_name in TABLES_ORDER:
                if table_name not in source_meta.tables:
                    print(f"   ⚠️ Warning: Tabel '{table_name}' tidak ditemukan di MySQL. Skip.")
                    continue
                
                if table_name not in target_meta.tables:
                    print(f"   ⚠️ Warning: Tabel '{table_name}' tidak ditemukan di PostgreSQL. Skip.")
                    continue

                # Ambil data dari Source
                source_table = source_meta.tables[table_name]
                query = source_table.select()
                
                # Eksekusi query di engine source (bukan connection target)
                with source_engine.connect() as source_conn:
                    data = source_conn.execute(query).fetchall()

                if not data:
                    print(f"   - {table_name}: 0 baris (Kosong)")
                    continue

                # Konversi hasil query ke list of dicts agar cocok untuk insert
                # Baris database (row) di SQLAlchemy biasanya bisa dikonversi ke dict atau diakses via keys
                # Kita perlu mapping manual kolom-kolomnya
                
                # Cara aman: mapping column name -> value
                target_table = target_meta.tables[table_name]
                records_to_insert = []
                
                for row in data:
                    # row._mapping converts Row to dict-like interface
                    row_dict = dict(row._mapping)
                    
                    # Fix boolean inconsistency (MySQL 0/1 -> Postgres True/False)
                    # SQLAlchemy biasanya handle ini, tapi kita pastikan jika ada masalah tipe
                    records_to_insert.append(row_dict)

                # Insert ke Target
                if records_to_insert:
                    target_conn.execute(target_table.insert(), records_to_insert)
                    print(f"   - {table_name}: ✅ {len(records_to_insert)} baris disalin.")

            trans.commit()
            print("\n🎉 Migrasi Data SELESAI! Database Neon sekarang identik dengan MySQL lokal.")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ TERJADI ERROR saat migrasi: {e}")
            print("   (Rollback dilakukan, database target kembali seperti semula)")

if __name__ == "__main__":
    migrate_data()
