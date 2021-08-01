import pymongo


def filter_year_aminer(aminer_mongodb, aminer_year_mongodb, year_AMiner):
    """Store _ids, titles and abstracts of all papers that published after ("year_AMiner" - 3) to the "aminer_year_mongodb".

    Args:
        aminer_mongodb (MongoDB collection): The collection that stores AMiner dataset.
        aminer_year_mongodb (MongoDB collection): The collection where the filtered data should be stored.
        year_AMiner (int): The year in which AMiner dataset has been published.
    """
    docs = aminer_mongodb.find({"year": {"$gte": (year_AMiner - 3)}}, {"_id": 1, "title": 1, "abstract": 1})
    for d in docs:
        aminer_year_mongodb.insert_one(d)


if __name__ == "__main__":
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    mongodb = client["CitRec"]
    aminer_mongodb = mongodb["AMiner"]
    aminer_year_mongodb = mongodb["AMiner_2018"]
    filter_year_aminer(aminer_mongodb, aminer_year_mongodb, 2021)