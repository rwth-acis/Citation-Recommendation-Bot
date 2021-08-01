import pymongo
import sqlite3
import torch
import tqdm


def compare_doi(citavi_sqlite, aminer_mongodb, citavi_mongodb, batch_size=100000):
    """Compare the dois of "citavi_sqlite" and "aminer_mongodb", if they are same, add the corresponding paper in "aminer_mongodb" to "citavi_mongodb".

    Args:
        citavi_sqlite (SQLite connection): The connection of Citavi SQLite.
        aminer_mongodb (MongoDB collection): The collection of AMienr dataset.
        citavi_mongodb (MongoDB collection): The collection stores the compared citavi dataset.
        batch_size (int, optional): Comparing with "bath_size" papers at a time. Defaults to 100000.
    """
    batch_size = 100000
    dois_aminer_cursor = aminer_mongodb.find(
        {"doi": {"$exists": True}}, {"_id": 1, "doi": 1}
    )

    j = 0
    doi_aminer = []
    ids_aminer = []
    for doc in dois_aminer_cursor:
        if j != batch_size:
            doi_aminer.append(doc["doi"])
            ids_aminer.append(doc["_id"])
        else:
            dois_sqlite = citavi_sqlite.execute(
                "SELECT DOI FROM Reference WHERE DOI NOT NULL"
            ).fetchall()
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
        dois_sqlite = citavi_sqlite.execute(
            "SELECT DOI FROM Reference WHERE DOI NOT NULL"
        ).fetchall()
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


def compare_title(citavi_sqlite, aminer_mongodb, citavi_mongodb, batch_size=100000):
    """Compare the titles of "citavi_sqlite" and "aminer_mongodb", if they are same, add the corresponding paper in "aminer_mongodb" to "citavi_mongodb".

    Args:
        citavi_sqlite (SQLite connection): The connection of Citavi SQLite.
        aminer_mongodb (MongoDB collection): The collection of AMienr dataset.
        citavi_mongodb (MongoDB collection): The collection stores the compared citavi dataset.
        batch_size (int, optional): Comparing with bath_size papers at a time. Defaults to 100000.
    """

    titles_aminer_cursor = aminer_mongodb.find(
        {"title": {"$exists": True}}, {"_id": 1, "title": 1}
    )

    j = 0
    title_aminer = []
    ids_aminer = []
    for doc in titles_aminer_cursor:
        if j != batch_size:
            title_aminer.append(doc["title"].lower().strip().replace(" ", ""))
            ids_aminer.append(doc["_id"])
        else:
            titles_sqlite = citavi_sqlite.execute(
                "SELECT Title FROM Reference WHERE title NOT NULL"
            ).fetchall()
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
        titles_sqlite = citavi_sqlite.execute(
            "SELECT Title FROM Reference WHERE title NOT NULL"
        ).fetchall()
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

def add_relevant_papers(aminer_year_mongodb, citavi_spector_mongodb, spector_year_mongodb, citavi_mongodb, threshold=0.8, batch_size=100000):
    """If a paper in the aminer_year_mongodb" is similar to a paper in the "citavi_mongodb" (cosine similariy >= threshold), it will be added into "citavi_mongodb", and its embedding will be added to "citavi_spector_mongodb".

    Args:
        aminer_year_mongodb (MongoDB collection): Collection stores the papers publised after the "year" in AMiner dataset.
        citavi_spector_mongodb (MongoDB collection: Colleciton contains embeddings of Citavi datset and of its relevant papers. 
        spector_year_mongodb (MongoDB collection): Collection stores embeddings of the papers publised after the "year" in AMiner dataset.
        citavi_mongodb (MongoDB collection): Colleciton contains Citavi datset and its relevant papers. 
        threshold (float, optional): [description]. Defaults to 0.8.
        batch_size (int, optional): Compare with "batch_size" papers at a time. Defaults to 100000.
    """
    citavi_emb = citavi_spector_mongodb.find()

    # Extract all embedings in citavi collection
    x2_all = []
    for doc in citavi_emb:
        x2_all.append(doc["embedding"])
    x2_all = torch.Tensor(x2_all)

    # Using GPU leads to long waiting time
    cos = CosineSimilarity().to("cpu")
    # cos = CosineSimilarity().to("cuda" if torch.cuda.is_available() else "cpu")
    # cos = torch.nn.DataParallel(cos)

    total=spector_year_mongodb.find().count()

    pbar = tqdm.tqdm(total=total)
    pbar.set_description("Adding relevant papers")

    x1 = []
    id_x1 = []
    add_papers = []
    add_ids = []
    for i in range(0, total, batch_size):
        for d_x1 in spector_year_mongodb.find()[i: (i + batch_size)]:
            x1.append(d_x1["embedding"])
            id_x1.append(d_x1["_id"])
        x1 = torch.Tensor(x1)
        for x2 in x2_all:
            x2 = x2.reshape(-1, 1)
            batch_result = cos(x1, x2)
            batch_result = torch.ge(batch_result, threshold).nonzero(as_tuple=True)[0]
            for batch_ind in batch_result:
                add_ids.append(id_x1[batch_ind])
            for add_id in add_ids:
                add_papers.append(aminer_year_mongodb.find({"_id": add_id}).next())
            if add_papers:
                try:
                    citavi_mongodb.insert_many(add_papers, ordered=False)
                # if some papers are already in the collecntion, pass
                except pymongo.errors.BulkWriteError:
                    pass
            add_ids = []
            add_papers = []
        pbar.update(batch_size)
        x1 = []
        id_x1 = []
    
    pbar.close()
    
    citavi_ids = citavi_mongodb.find({}, {"_id": 1})
    for d in citavi_ids:
        citavi_id = d["_id"]
        try:
            citavi_spector_mongodb.insert_one(spector_year_mongodb.find({"_id": citavi_id}).next())
        except pymongo.errors.DuplicateKeyError:
            pass
        except StopIteration:
            pass


if __name__ == "__main__":

    client = pymongo.MongoClient("mongodb://localhost:27017/")
    # set collections
    mongodb = client["CitRec"]
    aminer_mongodb = mongodb["AMiner"]
    citavi_mongodb = mongodb["Citavi"]
    spector_mongodb = mongodb["Spector"]
    spector_year_mongodb = mongodb["Spector_2018"]
    citavi_spector_mongodb = mongodb["Citavi_Spector"]

    citavi_sqlite = sqlite3.connect(
        "/home/pl908030/Codes/Citation-Recommendation-Bot/AWGS.db"
    )

    compare_doi(citavi_sqlite, aminer_mongodb, citavi_mongodb)
    compare_title(citavi_sqlite, aminer_mongodb, citavi_mongodb)
    add_relevant_papers(aminer_mongodb, citavi_spector_mongodb, spector_year_mongodb, citavi_mongodb)
