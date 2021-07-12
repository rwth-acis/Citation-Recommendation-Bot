from typing import ContextManager
import torch
import pymongo
from transformers import AutoModel, AutoTokenizer


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


def find_topk_relevant_papers(context, k):

    # Calculate embedding of input context
    tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
    model = AutoModel.from_pretrained("allenai/specter")
    inputs = tokenizer(
        context, padding=True, truncation=True, return_tensors="pt", max_length=512
    )
    result = model(**inputs)
    # take the first token in the batch as the embedding
    x2 = result.last_hidden_state[:, 0, :].reshape(-1,1)

    # connect to the MongoDB
    # use command ifconfic to get the ethernet IP
    client = pymongo.MongoClient("mongodb://localhost:12345/")
    # set collections
    db = client["CitRec"]
    spector = db["Spector"]
    aminer = db["AMiner"]
    paper_embeddings = spector.find()

    # Calculate cos similarity between input context and all candidate papers
    cos = CosineSimilarity().to("cpu")
    x1 = []
    cos_sim = torch.Tensor([])
    j = 0
    for emb in paper_embeddings:
        if j != 100000:
            x1.append(emb["embedding"])
        else:
            x1 = torch.Tensor(x1)
            batch_result = cos(x1, x2)
            x1 = []
            cos_sim = torch.cat((cos_sim, batch_result), 0)
            j = 0
            x1.append(emb["embedding"])
        j += 1
    if len(x1) > 0:
        x1 = torch.Tensor(x1)
        batch_result = cos(x1, x2)
        x1 = []
        cos_sim = torch.cat((cos_sim, batch_result), 0)

    _, indec = torch.topk(cos_sim, k, dim=0, largest=True, sorted=True)
    indec = indec.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

    for i in indec:
        print(aminer.find({}, {"title": 1})[i])


if __name__ == "__main__":

    context = "Machine learning methods are used in citation recommendation."
    
    print(context)

    find_topk_relevant_papers(context, 10)

    