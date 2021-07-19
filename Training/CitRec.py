import torch
import pymongo
from transformers import AutoModel, AutoTokenizer
from multiprocessing import Process, Queue
import time
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"


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


class CitRec:
    def __init__(self, server_adress):
        self.server_adress = server_adress
        self.client = pymongo.MongoClient(server_adress)
        self.db = self.client["CitRec"]
        self.citavi = self.db["Citavi"]
        self.spector = self.db["Citavi_Spector"]
        self.aminer = self.db["AMiner"]

    def find_topk_relevant_papers(self, context, k, worker=1, batch_size=5000):
        # Calculate embedding of input context
        tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
        model = AutoModel.from_pretrained("allenai/specter")
        inputs = tokenizer(
            context, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        result = model(**inputs)
        # take the first token in the batch as the embedding
        x2 = result.last_hidden_state[:, 0, :].reshape(-1, 1)

        def find_topk_multiprocessing(start_ind, end_ind, queue):
            client = pymongo.MongoClient(self.server_adress)
            db = client["CitRec"]
            spector = db["Citavi_Spector"]

            paper_embeddings = spector.find()[start_ind:end_ind]

            # Calculate cos similarity between input context and all candidate papers
            cos = CosineSimilarity().to("cpu")
            x1 = []
            x1_id = []
            cos_sim = torch.Tensor([])
            j = 0
            for emb in paper_embeddings:
                if j != batch_size:
                    x1.append(emb["embedding"])
                    x1_id.append(emb["_id"])
                else:
                    x1 = torch.Tensor(x1)
                    batch_result = cos(x1, x2)
                    x1 = []
                    cos_sim = torch.cat((cos_sim, batch_result), 0)
                    j = 0
                    x1.append(emb["embedding"])
                    x1_id.append(emb["_id"])
                j += 1
            if len(x1) > 0:
                x1 = torch.Tensor(x1)
                batch_result = cos(x1, x2)
                x1 = []
                cos_sim = torch.cat((cos_sim, batch_result), 0)

            values, indec = torch.topk(cos_sim, k, dim=0, largest=True, sorted=True)
            indec = indec.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

            ids = []
            for i in indec:
                ids.append(x1_id[i])

            queue.put(
                (values.detach().reshape(1, -1).squeeze().cpu().numpy().tolist(), ids)
            )

        jobs = []
        total = self.spector.find().count()
        if worker < 2:
            step_size = total
        else:
            step_size = total // (worker - 1)

        q = Queue()
        for i in range(0, total, step_size):
            p = Process(target=find_topk_multiprocessing, args=(i, i + step_size, q))
            jobs.append(p)
            p.start()

        for p in jobs:
            p.join()

        values_all, ids_all = [], []
        for _ in jobs:
            values, ids = q.get()
            values_all.append(values)
            ids_all.append(ids)
        values_all = torch.Tensor(values_all)
        values_all = torch.flatten(values_all)
        ids_all = sum(ids_all, [])
        values, indec = torch.topk(values_all, k, dim=0, largest=True, sorted=True)
        indec = indec.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

        res = []
        for i in indec:
            res.append(ids_all[i])

        return ids_all

    def consider_references(self, ids, threshold=3):
        frequency = {}
        for i in ids:
            references = self.aminer.find({"_id": i}, {"references": 1}).next().get("references") or None
            if references:
                for ref in references:
                    if ref not in frequency:
                        frequency[ref] = 1
                    else:
                        frequency[ref] += 1
        
        for i, freq in frequency.items():
            if freq > threshold:
                ids.append(i)
        
        return ids
    
    def find_papers_with_ids(self, ids):
        ids = set(ids)
        for i in ids:
            # TODO Output by format
            print(self.aminer.find({"_id": i}, {"title": 1}).next())
            

if __name__ == "__main__":

    time_start = time.time()
    citrec = CitRec("mongodb://localhost:27017/")

    context = "Machine learning methods are used in citation recommendation."
    print("Find relevant papers for: " + context)
    ids = citrec.find_topk_relevant_papers(context, 20, worker=5)
    ids = citrec.consider_references(ids)
    citrec.find_papers_with_ids(ids)
    time_end = time.time()
    print("time cost", time_end - time_start, "s")
