import pymongo
import sqlite3


def compare_doi(citavi_sqlite, aminer_mongodb, citavi_mongodb):
    
    batch_size = 100000
    dois_aminer_cursor = aminer_mongodb.find({"doi":{"$exists": True}}, {"_id": 1, "doi": 1})
    dois_sqlite = citavi_sqlite.execute("SELECT DOI FROM Reference WHERE DOI NOT NULL").fetchall()
    
    j = 0
    doi_aminer = []
    ids_aminer = []
    for doc in dois_aminer_cursor:
        if j != batch_size:
            doi_aminer.append(doc["doi"])
            ids_aminer.append(doc["_id"])
        else:
            for doi in dois_sqlite:
                try:
                    ind = doi_aminer.index(doi[0])
                    try: 
                        citavi_mongodb.insert_one(aminer_mongodb.find({"_id": ids_aminer[ind]}).next())
                    except pymongo.errors.DuplicateKeyError:
                        pass
                    citavi_sqlite.execute("DELETE FROM Reference where DOI = ?", doi)
                except ValueError:
                    pass
            citavi_sqlite.commit()
            j = 0
            doi_aminer = []
            ids_aminer = []
            doi_aminer.append(doc["doi"])
            ids_aminer.append(doc["_id"])
        j += 1
    if len(ids_aminer) > 0:
        for doi in dois_sqlite:
            try:
                ind = doi_aminer.index(doi[0])
                try: 
                    citavi_mongodb.insert_one(aminer_mongodb.find({"_id": ids_aminer[ind]}).next())
                except pymongo.errors.DuplicateKeyError:
                    pass
                citavi_sqlite.execute("DELETE FROM Reference where DOI = ?", doi)
            except ValueError:
                pass
        citavi_sqlite.commit()


def compare_title(citavi_sqlite, aminer_mongodb, citavi_mongodb):

    batch_size = 100000
    titles_aminer_cursor = aminer_mongodb.find({"title":{"$exists": True}}, {"_id": 1, "title": 1})
    titles_sqlite = citavi_sqlite.execute("SELECT Title FROM Reference WHERE title NOT NULL").fetchall()
    
    j = 0
    title_aminer = []
    ids_aminer = []
    for doc in titles_aminer_cursor:
        if j != batch_size:
            title_aminer.append(doc["title"].lower().strip().replace(' ', ''))
            ids_aminer.append(doc["_id"])
        else:
            for title in titles_sqlite:
                try:
                    ind = title_aminer.index(title[0].lower().strip().replace(' ', ''))
                    try: 
                        citavi_mongodb.insert_one(aminer_mongodb.find({"_id": ids_aminer[ind]}).next())
                    except pymongo.errors.DuplicateKeyError:
                        pass
                    citavi_sqlite.execute("DELETE FROM Reference where Title = ?", title)
                except ValueError:
                    try:
                        ind = title_aminer.index((title[0] + '.').lower().strip().replace(' ', ''))
                        try: 
                            citavi_mongodb.insert_one(aminer_mongodb.find({"_id": ids_aminer[ind]}).next())
                        except pymongo.errors.DuplicateKeyError:
                            pass
                        citavi_sqlite.execute("DELETE FROM Reference where Title = ?", title)
                    except ValueError:
                        pass
            citavi_sqlite.commit()
            j = 0
            title_aminer = []
            ids_aminer = []
            title_aminer.append(doc["title"].lower().strip().replace(' ', ''))
            ids_aminer.append(doc["_id"])
        j += 1
    if len(ids_aminer) > 0:
        for title in titles_sqlite:
            try:
                ind = title_aminer.index(title[0].lower().strip().replace(' ', ''))
                try: 
                    citavi_mongodb.insert_one(aminer_mongodb.find({"_id": ids_aminer[ind]}).next())
                except pymongo.errors.DuplicateKeyError:
                    pass
                citavi_sqlite.execute("DELETE FROM Reference where Title = ?", title)
            except ValueError:
                try:
                    ind = title_aminer.index((title[0] + '.').lower().strip().replace(' ', ''))
                    try: 
                        citavi_mongodb.insert_one(aminer_mongodb.find({"_id": ids_aminer[ind]}).next())
                    except pymongo.errors.DuplicateKeyError:
                        pass
                    citavi_sqlite.execute("DELETE FROM Reference where Title = ?", title)
                except ValueError:
                    pass
        citavi_sqlite.commit()


if __name__ == "__main__":

    client = pymongo.MongoClient("mongodb://localhost:27017/")
    # set collections
    mongodb = client["CitRec"]
    aminer_mongodb = mongodb["AMiner"]
    citavi_mongodb = mongodb["Citavi"]

    citavi_sqlite = sqlite3.connect('/home/pl908030/Codes/Citation-Recommendation-Bot/AWGS.db')

    compare_doi(citavi_sqlite, aminer_mongodb, citavi_mongodb)
    compare_title(citavi_sqlite, aminer_mongodb, citavi_mongodb)
