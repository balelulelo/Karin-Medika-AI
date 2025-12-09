try:
    import pandas as pd
    from neo4j import GraphDatabase
    from tqdm import tqdm
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install required packages:")
    print("pip install pandas neo4j tqdm")
    exit(1)

# --- CONFIGURATION ---
URI = "neo4j+s://ac8778a6.databases.neo4j.io"
AUTH = ("neo4j", "9-sWtT0Tidn-Ys6sv1OC41EC-G2ex_bCncz6u05HVQg")
FILE_PATH = "db_drug_interactions.csv"

# --- CYPHER QUERY ---
import_query = """
UNWIND $rows AS row
MERGE (d1:Drug {name: row.drug1})
SET d1.ID = toInteger(row.drug1_id)

MERGE (d2:Drug {name: row.drug2})
SET d2.ID = toInteger(row.drug2_id)

MERGE (d1)-[r:INTERACTS_WITH]->(d2)
SET r.ID = toInteger(row.interaction_id), 
    r.description = row.desc
"""

if __name__ == "__main__":
    print("1. Reading CSV file...")
    try:
        df = pd.read_csv(FILE_PATH)
    except FileNotFoundError:
        print(f"Error: Could not find '{FILE_PATH}'.")
        exit()

    print("2. Normalizing Data (Case-Insensitive)...")
    
    # --- STEP A: NORMALIZE NAMES ---
    # Convert everything to Title Case (e.g., "aspirin" -> "Aspirin")
    # .strip() removes accidental spaces like "Aspirin "
    df['Drug 1'] = df['Drug 1'].astype(str).str.strip().str.title()
    df['Drug 2'] = df['Drug 2'].astype(str).str.strip().str.title()

    # --- STEP B: GENERATE SEQUENTIAL DRUG IDs ---
    # Get unique names from both columns after normalization
    unique_drugs = pd.concat([df['Drug 1'], df['Drug 2']]).unique()
    
    print(f"   Found {len(unique_drugs)} unique drugs (normalized).")
    
    # Create mapping: Name -> Integer ID (1, 2, 3...)
    drug_map = {name: i+1 for i, name in enumerate(unique_drugs)}
    
    # Apply mapping
    df['drug1_id'] = df['Drug 1'].map(drug_map)
    df['drug2_id'] = df['Drug 2'].map(drug_map)

    # --- STEP C: GENERATE INTERACTION IDs ---
    df['interaction_id'] = range(1, len(df) + 1)

    # Prepare data for Neo4j
    data = df.rename(columns={
        'Drug 1': 'drug1', 
        'Drug 2': 'drug2', 
        'Interaction Description': 'desc'
    })[['drug1', 'drug2', 'desc', 'drug1_id', 'drug2_id', 'interaction_id']].to_dict('records')

    print(f"3. Connecting to Neo4j Aura... ({len(data)} rows)")

    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            driver.verify_connectivity()
            print("   Connection Successful!")

            with driver.session() as session:
                # 1. Create Constraints
                # We enforce uniqueness on the 'name' property. 
                # Since we pre-cleaned the data to Title Case, this effectively makes it case-insensitive.
                print("   Creating constraints...")
                session.run("CREATE CONSTRAINT FOR (d:Drug) REQUIRE d.name IS UNIQUE")
                session.run("CREATE INDEX FOR (d:Drug) ON (d.ID)")
                
                # 2. Batch Import
                batch_size = 1000 
                batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
                
                print("4. Starting Import...")
                for batch in tqdm(batches, desc="Importing", unit="batch"):
                    session.execute_write(lambda tx: tx.run(import_query, rows=batch))

        print("\nSuccess! Data normalized and imported.")

    except Exception as e:
        print(f"\nError: {e}")