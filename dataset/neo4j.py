import csv
from neo4j import GraphDatabase
import logging

# --- UPDATE THESE ---
# Set these to match your Neo4j database connection details
NEO4J_URI = "neo4j://127.0.0.1:7687"  # Or "bolt://...", "neo4j+s://..."
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "balelulelo30"  # Update this
# --------------------

# The path to your CSV file
CSV_FILE_PATH = "db_drug_interactions.csv"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def create_constraints(tx):
    """
    Creates a unique constraint on the 'name' property of Drug nodes.
    This speeds up MERGE operations and ensures no duplicate drugs are created.
    """
    logging.info("Attempting to create uniqueness constraint for :Drug(name)...")
    query = "CREATE CONSTRAINT drug_name_unique IF NOT EXISTS FOR (d:Drug) REQUIRE d.name IS UNIQUE"
    tx.run(query)
    logging.info("Constraint check/creation complete.")

def import_interactions(tx, csv_path):
    """
    Imports drug interactions from the CSV file into Neo4j.
    """
    logging.info(f"Starting import from {csv_path}...")

    query = """
    MERGE (d1:Drug {name: $drug1_name})
    MERGE (d2:Drug {name: $drug2_name})
    MERGE (d1)-[r:INTERACTS_WITH {description: $description}]->(d2)
    RETURN count(r) AS interactions_created
    """

    total_rows = 0
    with open(csv_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                drug1 = row['Drug 1']
                drug2 = row['Drug 2']
                description = row['Interaction Description']

                if not drug1 or not drug2:
                    logging.warning(f"Skipping row {total_rows + 1}: missing drug name.")
                    continue

                tx.run(query, drug1_name=drug1, drug2_name=drug2, description=description)
                total_rows += 1

                if total_rows % 1000 == 0:
                    logging.info(f"Processed {total_rows} rows...")

            except KeyError:
                logging.error("CSV headers 'Drug 1', 'Drug 2', or 'Interaction Description' not found. Please check your CSV file.")
                raise
            except Exception as e:
                logging.error(f"Error processing row {total_rows + 1}: {e}")
                logging.error(f"Row data: {row}")

    logging.info(f"Successfully processed {total_rows} interaction rows from the CSV.")

def main():
    """
    Main function to connect to Neo4j and run the import.
    """
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        logging.info(f"Connected to Neo4j at {NEO4J_URI}")
    except Exception as e:
        logging.error(f"Failed to connect to Neo4j: {e}")
        logging.error("Please check your NEO4J_URI, USER, and PASSWORD settings.")
        return

    try:
        # Create constraints first (in a separate session/transaction)
        with driver.session(database="neo4j") as session: # Specify db if not default
            session.execute_write(create_constraints)

        # Run the main data import
        with driver.session(database="neo4j") as session: # Specify db if not default
            session.execute_write(import_interactions, CSV_FILE_PATH)

        logging.info("Import complete!")

    except FileNotFoundError:
        logging.error(f"Error: The file '{CSV_FILE_PATH}' was not found.")
        logging.error("Please make sure the CSV file is in the same directory as the script.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        driver.close()
        logging.info("Connection to Neo4j closed.")

if __name__ == "_main_":
    main()