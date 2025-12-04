# we dont actually need this file anymore, but keeping it for reference


import os
import csv
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Driver Neo4j
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def import_csv_to_neo4j(csv_file_path):
    print(f"Mulai import data dari {csv_file_path}...")
    
    query = """
    MERGE (d1:Drug {name: $drug1})
    MERGE (d2:Drug {name: $drug2})
    MERGE (d1)-[r:INTERACTS_WITH]->(d2)
    SET r.description = $description
    """
    
    count = 0
    with driver.session() as session:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Sesuaikan nama key dengan header CSV kamu
                # CSV: Drug 1, Drug 2, Interaction Description
                session.run(query, 
                            drug1=row['Drug 1'], 
                            drug2=row['Drug 2'], 
                            description=row['Interaction Description'])
                count += 1
                if count % 100 == 0:
                    print(f"Sudah memproses {count} data...")
                    
    print(f"Selesai! Total {count} interaksi berhasil diimport.")
    driver.close()

if __name__ == "__main__":
    # Pastikan path file CSV benar
    # Kita asumsikan file ada di folder 'dataset' di root project
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    csv_path = os.path.join(project_root, 'dataset', 'interactions.csv')
    
    import_csv_to_neo4j(csv_path)