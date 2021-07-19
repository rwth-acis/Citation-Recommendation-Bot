import pymongo
import sqlite3
import torch
import tqdm


def compare_doi(citavi_sqlite, aminer_mongodb, citavi_mongodb):

    batch_size = 100000
    dois_aminer_cursor = aminer_mongodb.find(
        {"doi": {"$exists": True}}, {"_id": 1, "doi": 1}
    )
    dois_sqlite = citavi_sqlite.execute(
        "SELECT DOI FROM Reference WHERE DOI NOT NULL"
    ).fetchall()

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
                        citavi_mongodb.insert_one(
                            aminer_mongodb.find({"_id": ids_aminer[ind]}).next()
                        )
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
                    citavi_mongodb.insert_one(
                        aminer_mongodb.find({"_id": ids_aminer[ind]}).next()
                    )
                except pymongo.errors.DuplicateKeyError:
                    pass
                citavi_sqlite.execute("DELETE FROM Reference where DOI = ?", doi)
            except ValueError:
                pass
        citavi_sqlite.commit()


def compare_title(citavi_sqlite, aminer_mongodb, citavi_mongodb):

    batch_size = 100000
    titles_aminer_cursor = aminer_mongodb.find(
        {"title": {"$exists": True}}, {"_id": 1, "title": 1}
    )
    titles_sqlite = citavi_sqlite.execute(
        "SELECT Title FROM Reference WHERE title NOT NULL"
    ).fetchall()

    j = 0
    title_aminer = []
    ids_aminer = []
    for doc in titles_aminer_cursor:
        if j != batch_size:
            title_aminer.append(doc["title"].lower().strip().replace(" ", ""))
            ids_aminer.append(doc["_id"])
        else:
            for title in titles_sqlite:
                try:
                    ind = title_aminer.index(title[0].lower().strip().replace(" ", ""))
                    try:
                        citavi_mongodb.insert_one(
                            aminer_mongodb.find({"_id": ids_aminer[ind]}).next()
                        )
                    except pymongo.errors.DuplicateKeyError:
                        pass
                    citavi_sqlite.execute(
                        "DELETE FROM Reference where Title = ?", title
                    )
                except ValueError:
                    try:
                        ind = title_aminer.index(
                            (title[0] + ".").lower().strip().replace(" ", "")
                        )
                        try:
                            citavi_mongodb.insert_one(
                                aminer_mongodb.find({"_id": ids_aminer[ind]}).next()
                            )
                        except pymongo.errors.DuplicateKeyError:
                            pass
                        citavi_sqlite.execute(
                            "DELETE FROM Reference where Title = ?", title
                        )
                    except ValueError:
                        pass
            citavi_sqlite.commit()
            j = 0
            title_aminer = []
            ids_aminer = []
            title_aminer.append(doc["title"].lower().strip().replace(" ", ""))
            ids_aminer.append(doc["_id"])
        j += 1
    if len(ids_aminer) > 0:
        for title in titles_sqlite:
            try:
                ind = title_aminer.index(title[0].lower().strip().replace(" ", ""))
                try:
                    citavi_mongodb.insert_one(
                        aminer_mongodb.find({"_id": ids_aminer[ind]}).next()
                    )
                except pymongo.errors.DuplicateKeyError:
                    pass
                citavi_sqlite.execute("DELETE FROM Reference where Title = ?", title)
            except ValueError:
                try:
                    ind = title_aminer.index(
                        (title[0] + ".").lower().strip().replace(" ", "")
                    )
                    try:
                        citavi_mongodb.insert_one(
                            aminer_mongodb.find({"_id": ids_aminer[ind]}).next()
                        )
                    except pymongo.errors.DuplicateKeyError:
                        pass
                    citavi_sqlite.execute(
                        "DELETE FROM Reference where Title = ?", title
                    )
                except ValueError:
                    pass
        citavi_sqlite.commit()


class CosineSimilarity(torch.nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x1, x2):
        x = x1.mm(x2)

        x1_frobenius = x1.norm(dim=1).unsqueeze(0).t()
        x2_frobenins = x2.norm(dim=0).unsqueeze(0)
        x_frobenins = x1_frobenius.mm(x2_frobenins)

        final = x.mul(1 / x_frobenins)
        return final


def add_relevant_papers(
    aminer_mongodb, spector_mongodb, spector_2018_mongodb, citavi_mongodb
):

    threshold = 0.8
    batch_size = 100000

    citavi_emb = spector_mongodb.aggregate(
        [
            {
                "$lookup": {
                    "from": "Citavi",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "citavi",
                }
            },
            {"$match": {"citavi.year": {"$gte": 2018}}},
            {"$project": {"_id": 0, "embedding": 1}},
        ]
    )

    # Extract all embedings in citavi collection
    x2_all = []
    for doc in citavi_emb:
        x2_all.append(doc["embedding"])
    x2_all = torch.Tensor(x2_all)

    # Using GPU leads to long waiting time
    cos = CosineSimilarity().to("cpu")
    # cos = CosineSimilarity().to("cuda" if torch.cuda.is_available() else "cpu")
    # cos = torch.nn.DataParallel(cos)

    # store to a new collection, because aggregate returns a commandCursor that will be timeout.
    candidates_emb = spector_2018_mongodb.find({}, no_cursor_timeout=True)

    pbar = tqdm.tqdm(total=candidates_emb.count())
    pbar.set_description("Adding relevant papers")

    x1 = []
    id_x1 = []
    j = 0
    add_papers = []
    add_ids = []
    for d_x1 in candidates_emb:
        if j != batch_size:
            x1.append(d_x1["embedding"])
            id_x1.append(d_x1["_id"])
        else:
            x1 = torch.Tensor(x1)
            for x2 in x2_all:
                x2 = x2.reshape(-1, 1)
                batch_result = cos(x1, x2)
                batch_result = torch.ge(batch_result, threshold).nonzero(as_tuple=True)[
                    0
                ]
                for batch_ind in batch_result:
                    add_ids.append(id_x1[batch_ind])
                for add_id in add_ids:
                    add_papers.append(aminer_mongodb.find({"_id": add_id}).next())
                if add_papers:
                    try:
                        citavi_mongodb.insert_many(add_papers, ordered=False)
                    except pymongo.errors.BulkWriteError:
                        pass
                add_ids = []
                add_papers = []
            pbar.update(batch_size)
            x1 = []
            j = 0
            id_x1 = []
            x1.append(d_x1["embedding"])
            id_x1.append(d_x1["_id"])
        j += 1
    if len(x1) > 0:
        x1 = torch.Tensor(x1)
        for x2 in x2_all:
            x2 = x2.reshape(-1, 1)
            batch_result = cos(x1, x2)
            batch_result = torch.ge(batch_result, threshold).nonzero(as_tuple=True)[0]
            for batch_ind in batch_result:
                add_ids.append(id_x1[batch_ind])
            for add_id in add_ids:
                add_papers.append(aminer_mongodb.find({"_id": add_id}).next())
            if add_papers:
                try:
                    citavi_mongodb.insert_many(add_papers, ordered=False)
                except pymongo.errors.BulkWriteError:
                    pass
            add_ids = []
            add_papers = []
        pbar.update(batch_size)

    pbar.close()
    candidates_emb.close()


if __name__ == "__main__":

    client = pymongo.MongoClient("mongodb://localhost:27017/")
    # set collections
    mongodb = client["CitRec"]
    aminer_mongodb = mongodb["AMiner"]
    citavi_mongodb = mongodb["Citavi"]
    spector_mongodb = mongodb["Spector"]
    spector_2018_mongodb = mongodb["Spector_2018"]

    citavi_sqlite = sqlite3.connect(
        "/home/pl908030/Codes/Citation-Recommendation-Bot/AWGS.db"
    )

    compare_doi(citavi_sqlite, aminer_mongodb, citavi_mongodb)
    compare_title(citavi_sqlite, aminer_mongodb, citavi_mongodb)
    add_relevant_papers(
        aminer_mongodb, spector_mongodb, spector_2018_mongodb, citavi_mongodb
    )
