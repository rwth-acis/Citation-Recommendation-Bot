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
        self.citavi_embeddings = self.db["Citavi_Spector"]
        self.aminer = self.db["AMiner"]
        self.aminer_embeddings = self.db["Spector"]
        self.cos = CosineSimilarity().to("cpu")

    def generate_embedding(self, context):
        # Calculate embedding of input context
        tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
        model = AutoModel.from_pretrained("allenai/specter")
        inputs = tokenizer(
            context, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        result = model(**inputs)
        # take the first token in the batch as the embedding
        embedding = result.last_hidden_state[:, 0, :].reshape(-1, 1)

        return embedding

    def find_topk_relevant_papers(self, embedding, k, worker=1, batch_size=5000):
        def find_topk_multiprocessing(start_ind, end_ind, queue):
            client = pymongo.MongoClient(self.server_adress)
            db = client["CitRec"]

            paper_embeddings = db["Citavi_Spector"].find()[start_ind:end_ind]

            # Calculate cos similarity between input context and all candidate papers
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
                    batch_result = self.cos(x1, embedding)
                    x1 = []
                    cos_sim = torch.cat((cos_sim, batch_result), 0)
                    j = 0
                    x1.append(emb["embedding"])
                    x1_id.append(emb["_id"])
                j += 1
            if len(x1) > 0:
                x1 = torch.Tensor(x1)
                batch_result = self.cos(x1, embedding)
                x1 = []
                cos_sim = torch.cat((cos_sim, batch_result), 0)

            relevances, indec = torch.topk(cos_sim, k, dim=0, largest=True, sorted=True)
            indec = indec.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

            ids = []
            for i in indec:
                ids.append(x1_id[i])

            queue.put(
                (
                    relevances.detach().reshape(1, -1).squeeze().cpu().numpy().tolist(),
                    ids,
                )
            )

        jobs = []
        total = self.citavi_embeddings.find().count()
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

        relevances_all, ids_all = [], []
        for _ in jobs:
            relevances, ids = q.get()
            relevances_all.append(relevances)
            ids_all.append(ids)
        relevances_all = torch.Tensor(relevances_all)
        relevances_all = torch.flatten(relevances_all)
        ids_all = sum(ids_all, [])
        relevances, indec = torch.topk(
            relevances_all, k, dim=0, largest=True, sorted=True
        )
        relevances = relevances.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()
        indec = indec.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

        ids_relevances = []
        for i, rel in zip(indec, relevances):
            ids_relevances.append((ids_all[i], rel))

        return ids_relevances

    def consider_references(self, embedding, ids_relevances, threshold=3):
        frequency = {}
        for i, _ in ids_relevances:
            references = (
                self.aminer.find({"_id": i}, {"references": 1}).next().get("references")
                or None
            )
            if references:
                for ref in references:
                    if ref not in frequency:
                        frequency[ref] = 1
                    else:
                        frequency[ref] += 1

        new_ids = []
        new_x1 = []
        for i, freq in frequency.items():
            if freq > threshold:
                new_ids.append(i)
                new_x1.append(
                    self.aminer_embeddings.find({"_id": i}, {"_id": 0}).next()["embedding"])

        new_x1 = torch.Tensor(new_x1)
        relevances = self.cos(new_x1, embedding)
        relevances = relevances.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

        ids_relevances_ref = []
        for i, rel in zip(new_ids, relevances):
            ids_relevances_ref.append((i, rel))
        ids_relevances_ref.sort(key=lambda x: x[1], reverse=True)

        return ids_relevances_ref

    def find_papers_with_ids_relevances(self, ids_relevances):
        for i, rel in ids_relevances:
            # TODO Output by format
            print(self.aminer.find({"_id": i}, {"title": 1}).next())


if __name__ == "__main__":

    time_start = time.time()
    citrec = CitRec("mongodb://localhost:27017/")

    context = "Content-Based Citation Recommendation. We present a content-based method for recommending citations in an academic paper draft. We embed a given query document into a vector space, then use its nearest neighbors as candidates, and rerank the candidates using a discriminative model trained to distinguish between observed and unobserved citations. Unlike previous work, our method does not require metadata such as author names which can be missing, e.g., during the peer review process. Without using metadata, our method outperforms the best reported results on PubMed and DBLP datasets with relative improvements of over 18% in F1@20 and over 22% in MRR. We show empirically that, although adding metadata improves the performance on standard metrics, it favors self-citations which are less useful in a citation recommendation setup. We release an online portal (http://labs.semanticscholar.org/citeomatic/) for citation recommendation based on our method, and a new dataset OpenCorpus of 7 million research articles to facilitate future research on this task."
    print("Find relevant papers for: " + context)
    embedding = citrec.generate_embedding(context)
    ids_relevances = citrec.find_topk_relevant_papers(embedding, 20, worker=5)
    ids_relevances_ref = citrec.consider_references(embedding, ids_relevances, threshold=5)
    # citrec.find_papers_with_ids_relevances(ids_relevances)
    citrec.find_papers_with_ids_relevances(ids_relevances_ref)

    time_end = time.time()
    print("time cost", time_end - time_start, "s")
