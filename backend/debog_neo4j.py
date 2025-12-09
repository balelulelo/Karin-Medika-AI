import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

print("="*50)
print("🕵️  DIAGNOSA ISI DATABASE NEO4J")
print("="*50)

if not uri or not user or not password:
    print("❌ ERROR: File .env tidak lengkap!")
    exit()

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # 1. AMBIL SATU SAMPLE NODE
        # Kita ambil 1 node apa saja untuk melihat dia punya kolom (keys) apa saja.
        print("\n[1] MENGINTIP STRUKTUR DATA...")
        result = session.run("MATCH (n) RETURN labels(n) AS Label, keys(n) AS Kolom, properties(n) AS Data LIMIT 1")
        record = result.single()
        
        if record:
            print(f"   🏷️  Label Node: {record['Label']}")
            print(f"   🔑  Daftar Kolom: {record['Kolom']}")
            print(f"   📄  Contoh Data: {record['Data']}")
            
            # Analisis cepat
            keys = record['Kolom']
            possible_names = ['name', 'Name', 'drugName', 'title', 'drug', 'nama']
            match = [k for k in keys if k in possible_names]
            
            if match:
                print(f"\n✅ Kolom Nama Obat yang mungkin: {match}")
            else:
                print(f"\n⚠️ WARNING: Tidak ditemukan kolom umum seperti 'name'. Harap periksa 'Daftar Kolom' di atas.")
        else:
            print("   ⚠️  Database Kosong! Tidak ada node sama sekali.")

        # 2. CARI OBAT SPESIFIK (Misal: Paclitaxel)
        # Kita cari 'Paclitaxel' di SEMUA kolom untuk melihat dia sembunyi dimana
        target = "Paclitaxel" 
        print(f"\n[2] MENCARI '{target}' SECARA MANUAL...")
        
        # Query ini mencari value yang mengandung kata target di properti manapun
        query = f"""
        MATCH (n)
        WHERE 
            ANY(key IN keys(n) WHERE toString(n[key]) CONTAINS '{target}')
        RETURN labels(n) as Label, properties(n) as Data LIMIT 1
        """
        result = session.run(query)
        record = result.single()
        
        if record:
            print(f"   ✅ DITEMUKAN!")
            print(f"   📄 Data Node: {record['Data']}")
        else:
            print(f"   ❌ TIDAK DITEMUKAN. Obat '{target}' tidak ada di database ini.")

    driver.close()

except Exception as e:
    print(f"\n❌ ERROR KONEKSI: {e}")