import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Setup Driver (Make sure your .env has NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

# Initialize driver only if credentials exist to prevent crash on start
driver = None
if uri and user and password:
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        print("Successfully connected to Neo4j Database!")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")

def get_drug_interactions_from_db(drug_names):
    """
    Queries the existing Neo4j database for interactions between the provided drugs.
    """
    if not driver:
        print("Neo4j driver is not active.")
        return []

    # Query to find interactions (Bidirectional)
    # Assumes Nodes have label :Drug and property 'name'
    # Assumes Relationship is :INTERACTS_WITH and has property 'description'
    query = """
    MATCH (a:Drug)-[r:INTERACTS_WITH]-(b:Drug)
    WHERE toLower(a.name) IN $drugs AND toLower(b.name) IN $drugs
    RETURN a.name AS Drug1, b.name AS Drug2, r.description AS Description
    """
    
    # Convert input list to lowercase for case-insensitive matching
    drugs_lower = [d.lower() for d in drug_names]
    interactions_found = []

    try:
        with driver.session() as session:
            result = session.run(query, drugs=drugs_lower)
            
            # Use a set to avoid duplicates (A-B and B-A)
            seen_pairs = set()

            for record in result:
                d1, d2 = record["Drug1"], record["Drug2"]
                # Create a sorted tuple to handle A-B vs B-A
                pair = tuple(sorted((d1, d2)))
                
                if pair not in seen_pairs:
                    interactions_found.append({
                        "drug_a": d1,
                        "drug_b": d2,
                        "description": record["Description"]
                    })
                    seen_pairs.add(pair)
                    
        return interactions_found

    except Exception as e:
        print(f"Error querying Neo4j: {e}")
        return []

def close_driver():
    if driver:
        driver.close()