import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

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
    if not driver or not drug_names:
        return []

    # Bersihkan input user
    drugs_cleaned = [d.strip().lower() for d in drug_names if d.strip()]
    if not drugs_cleaned:
        return []
        
    print(f"🔍 Searching Neo4j for: {drugs_cleaned}")

    # QUERY CYPHER KHUSUS SCHEMA KAMU
    # Label: :Drug
    # Properties: .name, .ID
    # Relasi: asumsi arah tidak masalah ((a)-[r]-(b))
    query = """
    MATCH (a:Drug)-[r]-(b:Drug)
    WHERE 
      ANY(input IN $drugs WHERE toLower(toString(a.name)) CONTAINS input)
      AND 
      ANY(input IN $drugs WHERE toLower(toString(b.name)) CONTAINS input)
    RETURN 
      a.name AS Drug1, a.ID AS Id1, 
      b.name AS Drug2, b.ID AS Id2, 
      r.description AS Description
    """
    
    interactions_found = []

    try:
        with driver.session() as session:
            result = session.run(query, drugs=drugs_cleaned)
            seen_pairs = set()

            for record in result:
                d1 = record["Drug1"]
                d2 = record["Drug2"]
                # Ambil ID, jika null kasih tanda tanya
                id1 = record["Id1"] if record["Id1"] is not None else "?"
                id2 = record["Id2"] if record["Id2"] is not None else "?"
                desc = record.get("Description", "Interaction found.")

                # Hindari duplikat A-B vs B-A
                pair = tuple(sorted((d1, d2)))
                
                if pair not in seen_pairs:
                    print(f"✅ FOUND: {d1}({id1}) <-> {d2}({id2})")
                    interactions_found.append({
                        "drug_a": d1,
                        "id_a": id1,
                        "drug_b": d2,
                        "id_b": id2,
                        "description": desc
                    })
                    seen_pairs.add(pair)
            
            if not interactions_found:
                print("ℹ️ Query sukses, tapi tidak ada interaksi yang cocok dengan input.")
                    
        return interactions_found

    except Exception as e:
        print(f"❌ Neo4j Error: {e}")
        return []

def close_driver():
    if driver:
        driver.close()