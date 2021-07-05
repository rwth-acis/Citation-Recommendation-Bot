import torch
import pymongo


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

def link_relevance(documents, threshold, batch_size, target_collection):

    # cos = CosineSimilarity().to("cuda" if torch.cuda.is_available() else "cpu")
    cos = CosineSimilarity().to("cpu")

    for i, d_x2 in enumerate(documents.clone()):
        x2 = torch.Tensor(d_x2["embedding"]).reshape(-1,1)
        id_x2= d_x2["_id"]
        x1 = []
        j, k = 0, 0
        for d_x1 in documents.clone()[(i+1):]:
            if j != batch_size:
                x1.append(d_x1["embedding"])
            else:  
                x1 = torch.Tensor(x1)
                batch_result = cos(x1, x2)
                x1 = []
                j = 0
                for batch_ind, res in enumerate(batch_result):
                    if res >= threshold:
                        id_x1= documents.clone()[i + 1 + (k * batch_size) + batch_ind]["_id"]
                        target_collection.update_one({"_id": id_x2}, {"$addToSet":{"relevances": id_x1}})
                k += 1
                x1.append(d_x1["embedding"])
            j += 1
        if len(x1) > 0:
            x1 = torch.Tensor(x1)
            batch_result = cos(x1, x2)
            for batch_ind, res in enumerate(batch_result):
                if res >= threshold:
                    id_x1= documents.clone()[i + 1 + (k * batch_size) + batch_ind]["_id"]
                    target_collection.update_one({"_id": id_x2}, {"$addToSet":{"relevances": id_x1}})

            

def main():
    client = pymongo.MongoClient("134.61.193.185:27017")
    # set collections
    db = client["CitRec"]
    collection = db["Graph"]
    documents = collection.find()



if __name__ == "__main__":
    main()
