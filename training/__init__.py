import sqlite3
import pymongo
import argparse
from DBLP import filter_year_dblp2json
from Spector import generate_embeddings
from AMiner import filter_year_aminer
from Citavi import compare_doi, compare_title, add_relevant_papers


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_address", help="MongoDB's server address")
    parser.add_argument(
        "--year_AMiner", type=int, help="in which year the AMiner dataset was published"
    )
    parser.add_argument("--dblp_dtd", help="path to the dtd file of dblp dataset")
    parser.add_argument("--dblp_xml", help="path to the xml file of dblp dataset")
    parser.add_argument("--citavi_sqlite", help="path to the Citavi sqlite")
    parser.add_argument("--batch_size_1", type=int, default=16, help="generate batch_size_1 embeddings in the same time")
    parser.add_argument("--batch_size_2", type=int, default=100000, help="compare batch_size_2 embeddings in the same time")

    args = parser.parse_args()

    # AMiner parameters
    year_AMiner = args.year_AMiner

    # DBLP parameters
    dblp_dtd = args.dblp_dtd
    dblp_xml = args.dblp_xml
    batch_size_1 = args.batch_size_1
    batch_size_2 = args.batch_size_2

    # Citavi parameters
    citavi_sqlite = sqlite3.connect(args.citavi_sqlite)

    # MongoDB parameters
    client = pymongo.MongoClient(args.server_address)
    mongodb = client["CitRec"]
    # Collection contains paper items
    aminer_mongodb = mongodb["AMiner"]
    aminer_year_mongodb = mongodb["AMiner_" + str(int(year_AMiner) - 3)]
    citavi_mongodb = mongodb["Citavi"]
    dblp_mongodb = mongodb["DBLP"]
    # Collection contains embeddings
    spector_year_mongodb = mongodb["Spector_" + str(int(year_AMiner) - 3)]
    citavi_spector_mongodb = mongodb["Citavi_Spector"]
    dblp_spector_mongodb = mongodb["DBLP_Spector"]

    # 1. Filter items in DBLP dataset according to the year, and store them in collection DBLP
    print(
        "Filtering items in DBLP dataset according to the year, and storing them in collection DBLP..."
    )
    filter_year_dblp2json(
        path_dtd=dblp_dtd,
        path_xml=dblp_xml,
        year_AMiner=year_AMiner,
        dblp_mongodb=dblp_mongodb,
    )
    # 2. Generate embeddings for dblp dataset
    print("Generating embeddings for dblp dataset...")
    generate_embeddings(
        source_collection=dblp_mongodb,
        target_collection=dblp_spector_mongodb,
        batch_size=batch_size_1,
    )
    # 3. Filter items in AMiner dataset according to the year, and store them in collection aminer_year
    print(
        "Filtering items in AMiner dataset according to the year, and storing them in collection aminer_year..."
    )
    filter_year_aminer(
        aminer_mongodb=aminer_mongodb,
        aminer_year_mongodb=aminer_year_mongodb,
        year_AMiner=year_AMiner,
    )
    # 4. Generate embeddings for aminer_year dataset
    print("Generating embeddings for aminer_year dataset")
    generate_embeddings(
        source_collection=aminer_year_mongodb,
        target_collection=spector_year_mongodb,
        batch_size=batch_size_1,
    )
    # 5. Compare Citavi dataset and AMiner dataset, store the intersection to citavi_mongodb
    print(
        "Comparing Citavi dataset and AMiner dataset, storing the intersection to citavi_mongodb..."
    )
    compare_doi(
        citavi_sqlite=citavi_sqlite,
        aminer_mongodb=aminer_mongodb,
        citavi_mongodb=citavi_mongodb,
    )
    compare_title(
        citavi_sqlite=citavi_sqlite,
        aminer_mongodb=aminer_mongodb,
        citavi_mongodb=citavi_mongodb,
    )
    # 6. Generate embeddings for citavi items
    print("Generating embeddings for citavi items...")
    generate_embeddings(
        source_collection=citavi_mongodb,
        target_collection=citavi_spector_mongodb,
        batch_size=batch_size_1,
    )
    # 7. Add relevant papers to citavi, add the corresponding embeddings to citavi_spector_mongodb
    print(
        "Adding relevant papers to citavi, adding the corresponding embeddings to citavi_spector_mongodb..."
    )
    add_relevant_papers(
        aminer_year_mongodb=aminer_mongodb,
        citavi_spector_mongodb=citavi_spector_mongodb,
        spector_year_mongodb=spector_year_mongodb,
        citavi_mongodb=citavi_mongodb,
        threshold=0.8,
        batch_size=batch_size_2,
    )
    # 8. Drop useless collections
    print("Dropping useless collections...")
    aminer_year_mongodb.drop()
    spector_year_mongodb.drop()
    citavi_mongodb.drop()
