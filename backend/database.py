import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Setup Driver
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = None
if uri and user and password:
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✅ Connected to Neo4j at {uri}")
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")

def get_drug_interactions_from_db(drug_names):
    if not driver:
        print("⚠️ Neo4j driver is not active.")
        return []

    # 1. Bersihkan input
    drugs_cleaned = [d.strip().lower() for d in drug_names if d.strip()]
    print(f"🔍 Input User (Cleaned): {drugs_cleaned}")

    # 2. QUERY CYPHER FLEKSIBEL (PARTIAL MATCH)
    # Logika: Cari node dimana properti 'name' MENGANDUNG salah satu kata dari input user.
    # COALESCE digunakan untuk menangani variasi nama kolom (name, Name, drugName) dan ID (ID, id, drugId).
    query = """
    MATCH (a)-[r]-(b)
    WHERE 
      ANY(input IN $drugs WHERE toLower(toString(coalesce(a.name, a.Name, a.drugName))) CONTAINS input)
      AND 
      ANY(input IN $drugs WHERE toLower(toString(coalesce(b.name, b.Name, b.drugName))) CONTAINS input)
    RETURN 
      coalesce(a.name, a.Name, a.drugName) AS Drug1, 
      coalesce(a.ID, a.id, a.drugId, a.Id) AS Id1, 
      coalesce(b.name, b.Name, b.drugName) AS Drug2, 
      coalesce(b.ID, b.id, b.drugId, b.Id) AS Id2, 
      r.description AS Description
    """
    
    interactions_found = []

    try:
        with driver.session() as session:
            print("⏳ Executing Cypher query...")
            result = session.run(query, drugs=drugs_cleaned)
            
            seen_pairs = set()

            for record in result:
                d1 = record["Drug1"]
                d2 = record["Drug2"]
                # Ambil ID, jika null ganti jadi "-"
                id1 = record["Id1"] if record["Id1"] else "-"
                id2 = record["Id2"] if record["Id2"] else "-"
                
                desc = record.get("Description", "No description provided.")

                # Hindari duplikat A-B vs B-A
                pair = tuple(sorted((d1, d2)))
                
                # Filter tambahan di Python untuk memastikan kita tidak mengambil relasi "A ke A" 
                # atau obat yang namanya mirip tapi sebenarnya tidak diminta (opsional, tapi aman).
                # (Untuk sekarang kita percaya pada query Cypher)

                if pair not in seen_pairs:
                    print(f"✅ MATCH FOUND: {d1} ({id1}) <-> {d2} ({id2})")
                    interactions_found.append({
                        "drug_a": d1,
                        "id_a": id1,
                        "drug_b": d2,
                        "id_b": id2,
                        "description": desc
                    })
                    seen_pairs.add(pair)
            
            if not interactions_found:
                print("❌ Query selesai, tapi TIDAK ada interaksi yang cocok ditemukan.")
                print("   -> Pastikan nama obat di database mengandung kata kunci input.")

        return interactions_found

    except Exception as e:
        print(f"❌ Error querying Neo4j: {e}")
        return []

def close_driver():
    if driver:
        driver.close()