import torch
import pymongo
import tqdm
from multiprocessing import cpu_count
from multiprocessing import Pool, Lock


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


def link_relevance(
    server,
    database,
    source_collection_name,
    target_collection_name,
    threshold,
    batch_size,
    start_ind,
    end_ind,
):

    # for test
    # cos = CosineSimilarity().to("cuda" if torch.cuda.is_available() else "cpu")

    client = pymongo.MongoClient(server)
    # set collections
    db = client[database]
    target_collection = db[target_collection_name]
    source_collection = db[source_collection_name]
    documents = source_collection.find()

    for i, d_x2 in enumerate(documents.clone()[start_ind:end_ind]):
        x2 = torch.Tensor(d_x2["embedding"]).reshape(-1, 1)
        id_x2 = d_x2["_id"]
        x1 = []
        j, k = 0, 0
        for d_x1 in documents.clone()[(start_ind + i + 1) :]:
            if j != batch_size:
                x1.append(d_x1["embedding"])
            else:
                x1 = torch.Tensor(x1)
                batch_result = cos(x1, x2)
                x1 = []
                j = 0
                add_list = []
                for batch_ind, res in enumerate(batch_result):
                    if res >= threshold:
                        id_x1 = documents.clone()[start_ind + i + 1 + (k * batch_size) + batch_ind]["_id"]
                        add_list.append(id_x1)
                if add_list:
                    target_collection.update_one(
                        {"_id": id_x2},
                        {"$addToSet": {"relevances": {"$each": add_list}}},
                    )
                k += 1
                x1.append(d_x1["embedding"])
            j += 1
        if len(x1) > 0:
            x1 = torch.Tensor(x1)
            batch_result = cos(x1, x2)
            add_list = []
            for batch_ind, res in enumerate(batch_result):
                if res >= threshold:
                    id_x1 = documents.clone()[start_ind + i + 1 + (k * batch_size) + batch_ind]["_id"]
                    add_list.append(id_x1)
                if add_list:
                    target_collection.update_one(
                        {"_id": id_x2},
                        {"$addToSet": {"relevances": {"$each": add_list}}},
                    )

    # for test set the following as conmments
    mutex.acquire()
    pbar.update(end_ind - start_ind)
    mutex.release()

    client.close()


if __name__ == "__main__":

    server = "134.61.193.185:27017"
    database = "CitRec"
    source_collection_name = "Spector"
    target_collection_name = "Graph"
    workers = cpu_count() * 2
    threshold = 0.85
    batch_size = 10000
    step_size = 10000

    cos = CosineSimilarity().to("cuda" if torch.cuda.is_available() else "cpu")
    # cos = CosineSimilarity().to("cpu")
    mutex = Lock()

    client_for_total = pymongo.MongoClient(server)
    total = client_for_total[database][source_collection_name].find().count()
    pbar = tqdm.tqdm(total=total)
    pbar.set_description("Link relevant papers")
    client_for_total.close()

    p = Pool(workers)
    for i in range(0, total, step_size):
        p.apply_async(
            link_relevance,
            args=(
                server,
                database,
                source_collection_name,
                target_collection_name,
                threshold,
                batch_size,
                i,
                i + step_size, 
            ),
            callback=lambda _: pbar.update(step_size),
        )

    p.close()
    p.join()
