import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Setup Driver (Make sure your .env has NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

# Initialize driver only if credentials exist to prevent crash on start
driver = None
if uri and user and password:
    try:
        # Use the corrected Neo4j Aura connection string
        connection_uri = uri
        
        print(f"🔗 Attempting to connect to Neo4j Aura...")
        print(f"   URI: {connection_uri}")
        print(f"   Instance: {os.getenv('AURA_INSTANCEID', 'Unknown')}")
        
        driver = GraphDatabase.driver(connection_uri, auth=(user, password))
        
        # Test the connection with a simpler query
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            if result.single()["test"] == 1:
                print("✅ Successfully connected to Neo4j Database!")
                print("🎉 Database is online and ready!")
            else:
                print("❌ Database connection test failed!")
                driver = None
                
    except Exception as e:
        error_str = str(e)
        print(f"❌ Failed to connect to Neo4j: {error_str}")
        
        if "Unable to retrieve routing information" in error_str:
            print("\n" + "!"*60)
            print("🛑 CONNECTION ERROR: UNABLE TO CONNECT")
            print("!"*60)
            print("The app cannot connect to your Neo4j Aura database.")
            print("Possible causes:")
            print("1. 📋 Database is PAUSED (Check https://console.neo4j.io/)")
            print("2. 🔐 SSL/Network issues (Try using 'neo4j+ssc://' in .env)")
            print("3. 🌐 Firewall blocking port 7687")
            print("\n👉 ACTION REQUIRED:")
            print("• Check if database is 'Running' in Neo4j Console")
            print("• If running, check your network connection")
            print("!"*60 + "\n")
            print("✅ The app will continue using MOCK DATA until the connection is fixed.")
        else:
            print(f"   • Check your Neo4j Aura dashboard")
            print(f"   • Verify credentials are correct")
        
        driver = None
else:
    print("❌ Missing Neo4j credentials in environment variables!")
    print(f"URI: {'✓' if uri else '✗'}")
    print(f"Username: {'✓' if user else '✗'}")
    print(f"Password: {'✓' if password else '✗'}")

def get_drug_interactions_from_db(drug_names):
    """
    Queries the existing Neo4j database for interactions between the provided drugs.
    Returns empty list if database connection fails.
    """
    interactions_found = []
    
    # Try database first
    if driver:
        try:
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
                        
        except Exception as e:
            print(f"Database interaction query failed, using fallback data: {e}")
    
    # Fallback to mock data if no database interactions found
    if not interactions_found:
        drugs_lower = [d.lower() for d in drug_names]
        for interaction in MOCK_INTERACTIONS:
            drug_a_lower = interaction["drug_a"].lower()
            drug_b_lower = interaction["drug_b"].lower()
            
            if (drug_a_lower in drugs_lower and drug_b_lower in drugs_lower) or \
               (drug_b_lower in drugs_lower and drug_a_lower in drugs_lower):
                interactions_found.append(interaction)
    
    return interactions_found

def get_drug_by_name(drug_name):
    """
    Retrieves information about a single drug by name.
    Returns a dictionary with drug details or None if not found.
    Follows actual database schema: only name and ID properties.
    """
    # Handle None or empty input
    if not drug_name or not isinstance(drug_name, str):
        return None
    
    # Try database first
    if driver:
        try:
            query = """
            MATCH (d:Drug)
            WHERE toLower(d.name) = toLower($name)
            RETURN d.ID AS id, d.name AS name
            """

            with driver.session() as session:
                result = session.run(query, name=drug_name)
                record = result.single()
                
                if record:
                    return {
                        "id": record.get("id"),
                        "name": record.get("name")
                    }
        except Exception as e:
            print(f"Database query failed, using fallback data: {e}")
    
    # Fallback to mock data
    drug_name_lower = drug_name.lower()
    for mock_name, mock_data in MOCK_DRUGS.items():
        if drug_name_lower in mock_name.lower() or mock_name.lower() in drug_name_lower:
            return mock_data.copy()
    
    return None

def get_drug_ingredients(drug_name):
    """
    Retrieves all ingredients for a given drug.
    Returns a list of ingredients with their dosages.
    """
    if not driver:
        print("Neo4j driver is not active.")
        return []

    # Since the current database doesn't have ingredient data,
    # return a message indicating this
    print(f"No ingredient data available for {drug_name} in current database structure")
    return []

def get_brand_drugs(drug_name):
    """
    Retrieves all active ingredients in a drug.
    Returns a list of ingredients with their details.
    """
    if not driver:
        print("Neo4j driver is not active.")
        return []

    # Since the current database doesn't have ingredient/brand data,
    # return a message indicating this
    print(f"No brand/ingredient data available for {drug_name} in current database structure")
    return []

def search_drugs_by_keyword(keyword):
    """
    Searches for drugs by keyword (fuzzy matching).
    Useful when exact drug name doesn't match but similar drugs exist.
    Returns list of drugs with only name and ID properties (following actual schema).
    """
    # Handle None or empty input
    if not keyword or not isinstance(keyword, str):
        return []
    
    results = []
    
    # Try database first
    if driver:
        try:
            query = """
            MATCH (d:Drug)
            WHERE toLower(d.name) CONTAINS toLower($keyword)
            RETURN d.ID AS id, d.name AS name
            LIMIT 10
            """

            with driver.session() as session:
                result = session.run(query, keyword=keyword)
                
                for record in result:
                    results.append({
                        "id": record.get("id"),
                        "name": record.get("name")
                    })
                    
        except Exception as e:
            print(f"Database search failed, using fallback data: {e}")
    
    # Fallback to mock data
    if not results:
        keyword_lower = keyword.lower()
        for mock_name, mock_data in MOCK_DRUGS.items():
            if keyword_lower in mock_name.lower():
                results.append(mock_data.copy())
                if len(results) >= 5:  # Limit results
                    break
    
    return results

def close_driver():
    if driver:
        driver.close()
# Mock drug data for fallback when database is unavailable
# Note: This uses generic drug names and follows actual database structure (ID: integer, only name and ID properties)
MOCK_DRUGS = {
    "Drug001": {"id": 1, "name": "Drug001"},
    "Drug002": {"id": 2, "name": "Drug002"},
    "Drug003": {"id": 3, "name": "Drug003"},
    "Drug004": {"id": 4, "name": "Drug004"},
    "Drug005": {"id": 5, "name": "Drug005"},
    "Drug006": {"id": 6, "name": "Drug006"},
    "Drug007": {"id": 7, "name": "Drug007"},
    "Drug008": {"id": 8, "name": "Drug008"},
    "Drug009": {"id": 9, "name": "Drug009"},
    "Drug010": {"id": 10, "name": "Drug010"}
}

# Mock interaction data (following actual schema: relationship has ID and description)
MOCK_INTERACTIONS = [
    {"drug_a": "Drug001", "drug_b": "Drug002", "description": "Interaction description 1"},
    {"drug_a": "Drug003", "drug_b": "Drug004", "description": "Interaction description 2"},
    {"drug_a": "Drug005", "drug_b": "Drug006", "description": "Interaction description 3"}
]