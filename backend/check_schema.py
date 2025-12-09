import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ambil kredensial
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

# Inisialisasi Driver
driver = None
try:
    if uri and user and password:
        driver = GraphDatabase.driver(uri, auth=(user, password))
    else:
        print("❌ Error: Kredensial Neo4j (URI, USER, PASSWORD) tidak lengkap di .env")
        exit()
except Exception as e:
    print(f"❌ Gagal membuat driver: {e}")
    exit()

def check_structure():
    if not driver:
        print("Driver belum siap.")
        return

    print(f"✅ Mencoba terhubung ke {uri}...")
    
    try:
        # Gunakan session di dalam blok try
        with driver.session() as session:
            print("\n=== 1. CEK LABEL NODE ===")
            result = session.run("MATCH (n) RETURN distinct labels(n) LIMIT 5")
            found_labels = list(result)
            if found_labels:
                for r in found_labels:
                    print(f"Label ditemukan: {r['labels(n)']}")
            else:
                print("⚠️ Tidak ada label ditemukan (Database mungkin kosong).")

            print("\n=== 2. CEK PROPERTY/KOLOM (SAMPEL) ===")
            # Ambil node apapun untuk melihat strukturnya
            result = session.run("MATCH (n) RETURN labels(n) as label, keys(n) AS cols LIMIT 1")
            record = result.single()
            if record:
                print(f"Label: {record['label']}")
                print(f"Kolom (Properties): {record['cols']}")
            else:
                print("⚠️ Tidak ada data node untuk diperiksa.")

            print("\n=== 3. CEK DATA OBAT ===")
            # Cek apakah ada data obat, dan apa nama kolomnya
            # Kita cari node yang punya properti mirip 'name'
            result = session.run("""
                MATCH (n) 
                WHERE n.name IS NOT NULL OR n.Name IS NOT NULL OR n.drugName IS NOT NULL
                RETURN labels(n), properties(n) LIMIT 1
            """)
            record = result.single()
            if record:
                print(f"Contoh Node Obat Ditemukan:")
                print(f"Label: {record['labels(n)']}")
                print(f"Data: {record['properties(n)']}")
            else:
                print("⚠️ Tidak ditemukan node dengan properti 'name', 'Name', atau 'drugName'.")

    except Exception as e:
        print(f"❌ Terjadi kesalahan saat query: {e}")

if __name__ == "__main__":
    try:
        check_structure()
    finally:
        # Driver baru ditutup di sini, setelah semua fungsi selesai
        if driver:
            driver.close()
            print("\n🔒 Driver Neo4j ditutup.")