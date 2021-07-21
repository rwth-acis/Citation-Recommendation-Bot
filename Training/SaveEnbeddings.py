import pymongo
import nodevectors
import tqdm


def store_embeddings(g2v_result, col_spector, col_target):
    pbar = tqdm.tqdm(total=len(g2v_result))
    pbar.set_description("Storing embeddings: ")

    count = 0
    for i, node_emb in g2v_result.items():
        col_target.insert_one(
            {
                "_id": i,
                "paper_embedding": col_spector.find({"_id": i}).next()["embedding"],
                "node_embedding": node_emb.tolist(),
            }
        )
        
        if count == 1000:
            pbar.update(1000)
            count = 0
        count += 1

    pbar.close()


if __name__ == "__main__":
    # connect to the MongoDB
    # use command ifconfic to get the ethernet IP
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    # set collections
    db = client["CitRec"]
    col_spector = db["Spector"]
    col_target = db["Embeddings"]

    g2v = nodevectors.ProNE.load(
        "/home/pl908030/Codes/Citation-Recommendation-Bot/node_embedding.zip"
    )

    store_embeddings(g2v.model, col_spector, col_target)
