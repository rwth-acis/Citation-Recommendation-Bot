import torch
import pymongo
import tqdm
from multiprocessing import Pool
import os, signal


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
):

    # Using GPU leads to long waiting time
    cos = CosineSimilarity().to("cpu")
    # cos = CosineSimilarity().to("cuda" if torch.cuda.is_available() else "cpu")
    # cos = torch.nn.DataParallel(cos)

    client = pymongo.MongoClient(server)
    # set collections
    db = client[database]
    target_collection = db[target_collection_name]
    source_collection = db[source_collection_name]
    documents = source_collection.find()


    # extract docments for batch operations
    x2_batch = []
    id_x2_batch = []
    d_x2_cursor = source_collection.find({}, no_cursor_timeout=True)[start_ind : (start_ind + batch_size)]
    for d_x2 in d_x2_cursor:
        x2_batch.append(d_x2["embedding"])
        id_x2_batch.append(d_x2["_id"])
    d_x2_cursor.close()
    # transform x2_batch to tensor
    x2_batch = torch.Tensor(x2_batch)
    # calculate cos_sim for docs in batch_doccs
    for i, x2_batch_x2 in enumerate(x2_batch):
        x2_batch_x2 = x2_batch_x2.reshape(-1, 1)
        x2_batch_x1 = x2_batch[i + 1 :]
        batch_result = cos(x2_batch_x1, x2_batch_x2)
        add_list = []
        batch_result = torch.ge(batch_result, threshold).nonzero(as_tuple=True)[0]
        for batch_ind in batch_result:
            add_list.append(id_x2_batch[i + 1 + batch_ind])
        if add_list:
            target_collection.update_one(
                {"_id": id_x2_batch[i]},
                {"$addToSet": {"relevances": {"$each": add_list}}},
            )
        add_list = []

    # calculate cos_sim between batch_docs and other docs
    x1 = []
    id_x1 = []
    j = 0
    d_x1_cursor = source_collection.find({}, no_cursor_timeout=True)[(start_ind + batch_size):]
    for d_x1 in d_x1_cursor:
        if j != batch_size:
            x1.append(d_x1["embedding"])
            id_x1.append(d_x1["_id"])
        else:
            x1 = torch.Tensor(x1)
            for i, x2 in enumerate(x2_batch):
                x2 = x2.reshape(-1, 1)
                batch_result = cos(x1, x2)
                add_list = []
                batch_result = torch.ge(batch_result, threshold).nonzero(as_tuple=True)[0]
                for batch_ind in batch_result:
                        add_list.append(id_x1[batch_ind])
                if add_list:
                    target_collection.update_one(
                        {"_id": id_x2_batch[i]},
                        {"$addToSet": {"relevances": {"$each": add_list}}},
                    )
                add_list = []
            x1 = []
            j = 0
            id_x1 = []
            x1.append(d_x1["embedding"])
            id_x1.append(d_x1["_id"])
        j += 1
    if len(x1) > 0:
        x1 = torch.Tensor(x1)
        for i, x2 in enumerate(x2_batch):
            x2 = x2.reshape(-1, 1)
            batch_result = cos(x1, x2)
            add_list = []
            batch_result = torch.ge(batch_result, threshold).nonzero(as_tuple=True)[0]
            for batch_ind in batch_result:
                    add_list.append(id_x1[batch_ind])
            if add_list:
                target_collection.update_one(
                    {"_id": id_x2_batch[i]},
                    {"$addToSet": {"relevances": {"$each": add_list}}},
                )
            add_list = []
    d_x1_cursor.close()

    client.close()


def throw_error(e):
    print(e.__cause__)
    os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)


if __name__ == "__main__":

    server = "mongodb://localhost:27017/"
    database = "CitRec"
    source_collection_name = "Spector"
    target_collection_name = "Graph"
    workers = 144
    threshold = 0.85
    batch_size = 10000

    client_for_total = pymongo.MongoClient(server)
    total = client_for_total[database][source_collection_name].find().count()
    pbar = tqdm.tqdm(total=total)
    pbar.set_description("Link relevant papers")
    client_for_total.close()

    p = Pool(workers)
    for i in range(0, total, batch_size):
        result = p.apply_async(
            link_relevance,
            args=(
                server,
                database,
                source_collection_name,
                target_collection_name,
                threshold,
                batch_size,
                i,
            ),
            error_callback=throw_error,
            callback=lambda _: pbar.update(batch_size),
        )

    p.close()
    p.join()
