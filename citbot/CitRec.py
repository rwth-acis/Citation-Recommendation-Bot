import torch
import pymongo
from transformers import AutoModel, AutoTokenizer
import configparser


config = configparser.ConfigParser()
config.read("config.ini")
server_address = config.get("DEFAULT", "server_address")


def load_embeddings(server_address, collection):
    client = pymongo.MongoClient(server_address)
    ids_embeddings = client["CitRec"][collection].find()

    embeddings = []
    ids = []
    for d in ids_embeddings:
        embeddings.append(d["embedding"])
        ids.append(d["_id"])

    client.close()
    embeddings = torch.Tensor(embeddings)

    return ids, embeddings


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

    # set embeddings as statistic variable
    citavi_ids, citavi_embeddings = load_embeddings(server_address, "Citavi_Spector")
    dblp_ids, dblp_embeddings = load_embeddings(server_address, "DBLP_Spector")

    def __init__(self):
        self.server_address = server_address
        self.client = pymongo.MongoClient(server_address)
        self.db = self.client["CitRec"]
        self.aminer = self.db["AMiner"]
        self.dblp = self.db["DBLP"]
        self.cos = CosineSimilarity().to("cpu")
        self.tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
        self.model = AutoModel.from_pretrained("allenai/specter")

    def __call__(self, context, k=50):
        embedding = self.generate_embedding(context)
        ids_relevances_citavi, ids_relevances = self.find_topk_relevant_papers(
            embedding, k
        )
        ids_ref = self.consider_references(ids_relevances_citavi, threshold=5)
        rec_list = self.find_papers_with_ids_relevances(ids_relevances)
        rec_list_ref = self.find_papers_with_ids(ids_ref)
        return (rec_list, rec_list_ref)

    def generate_embedding(self, context):
        """Generate embedding for the input context.

        Args:
            context (string): Citation context input by the user.

        Returns:
            torch.Tensor: Embedding for the input context
        """
        # Calculate embedding of input context
        inputs = self.tokenizer(
            context, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        result = self.model(**inputs)
        # take the first token in the batch as the embedding
        embedding = result.last_hidden_state[:, 0, :].reshape(-1, 1)

        return embedding

    def find_topk_relevant_papers(self, embedding, k):
        """Fink most relevant k papers for the input citation context.

        Args:
            embedding (torch.Tensor): The embedding of input context.
            k (int): k papers will be found.

        Returns:
            set:
        """
        # find topk in citavi dataset
        relevances_all = self.cos(CitRec.citavi_embeddings, embedding)
        relevances, indec = torch.topk(
            relevances_all, k, dim=0, largest=True, sorted=True
        )

        relevances = relevances.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()
        indec = indec.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

        ids_relevances_citavi = []
        for i, rel in zip(indec, relevances):
            ids_relevances_citavi.append((CitRec.citavi_ids[i], rel, "citavi"))

        # find topk in dblp dataset
        relevances_all = self.cos(CitRec.dblp_embeddings, embedding)
        relevances, indec = torch.topk(
            relevances_all, k, dim=0, largest=True, sorted=True
        )

        relevances = relevances.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()
        indec = indec.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

        ids_relevances_dblp = []
        for i, rel in zip(indec, relevances):
            ids_relevances_dblp.append((CitRec.dblp_ids[i], rel, "dblp"))

        # sorted by the relevance scores
        ids_relevances = sorted(
            ids_relevances_citavi + ids_relevances_dblp,
            key=lambda v: (v[1], v[2], v[0]),
            reverse=True,
        )

        return (ids_relevances_citavi, ids_relevances[:k])

    def consider_references(self, ids_relevances_citavi, threshold=5):
        frequency = {}
        for i, _, _ in ids_relevances_citavi:
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
        frequency = sorted(
            frequency.items(), key=lambda kv: (kv[1], kv[0]), reverse=True
        )

        ids_ref = []
        for i, freq in frequency:
            if freq >= threshold:
                ids_ref.append(i)

        return ids_ref

    def find_papers_with_ids_relevances(self, ids_relevances):
        rec_list = []
        for i, rel, source in ids_relevances:
            if source == "dblp":
                dic = self.dblp.find(
                    {"_id": i},
                    {
                        "title": 1,
                        "author": 1,
                        "year": 1,
                        "ee": 1,
                        "bib": 1,
                    },
                ).next()
                dic["rel_score"] = rel
                dic["source"] = "dblp"
                rec_list.append(dic)
            else:
                dic = self.aminer.find(
                    {"_id": i},
                    {
                        "title": 1,
                        "authors.name": 1,
                        "year": 1,
                        "doi": 1,
                        "url": 1,
                        "bib": 1,
                    },
                ).next()
                dic["rel_score"] = rel
                dic["source"] = "aminer"
                rec_list.append(dic)

        # test, if the url could work
        for paper in rec_list:
            if paper["source"] == "aminer":
                if "doi" in paper:
                    if paper["doi"] != "":
                        paper["url"] = "https://doi.org/" + paper["doi"]
                elif "url" in paper:
                    if isinstance(paper["url"], list):
                        for url in paper.get("url"):
                            if url.startswith("http"):
                                if url.startswith("https://dblp"):
                                    continue
                                paper["url"] = url
                                break
                            # no usable url, drop this key-value pairs
                            del paper["url"]
                    elif isinstance(paper["url"], str):
                        if not paper["url"].startswith("http"):
                            del paper["url"]
            else:
                if "ee" in paper:
                    if isinstance(paper["ee"], list):
                        for url in paper.get("ee"):
                            if url.startswith("http"):
                                paper["ee"] = url
                                break
                            # no usable url, drop this key-value pairs
                            del paper["ee"]
                    elif isinstance(paper["ee"], str):
                        if not paper["ee"].startswith("http"):
                            del paper["ee"]

        return rec_list

    def find_papers_with_ids(self, ids):
        rec_list_ref = []
        for i in ids:
            dic = self.aminer.find(
                {"_id": i},
                {
                    "title": 1,
                    "authors.name": 1,
                    "venue.raw": 1,
                    "year": 1,
                    "url": 1,
                    "bib": 1,
                },
            ).next()
            dic["source"] = "aminer"
            rec_list_ref.append(dic)

        for paper in rec_list_ref:
            if "doi" in paper:
                if paper["doi"] != "":
                    paper["url"] = "https://doi.org/" + paper["doi"]
            elif "url" in paper:
                if isinstance(paper["url"], list):
                    for url in paper.get("url"):
                        if url.startswith("http"):
                            paper["url"] = url
                            break
                        # no usable url, drop this key-value pairs
                        del paper["url"]
                elif isinstance(paper["url"], str):
                    if not paper["url"].startswith("http"):
                        del paper["url"]

        return rec_list_ref


if __name__ == "__main__":

    citrec = CitRec()

    context = """
                DeepWalk: Online Learning of Social Representations. We present DeepWalk, a novel approach for learning latent representations of vertices in a network. These latent representations encode social relations in a continuous vector space, which is easily exploited by statistical models. DeepWalk generalizes recent advancements in language modeling and unsupervised feature learning (or deep learning) from sequences of words to graphs. DeepWalk uses local information obtained from truncated random walks to learn latent representations by treating walks as the equivalent of sentences. We demonstrate DeepWalk's latent representations on several multi-label network classification tasks for social networks such as BlogCatalog, Flickr, and YouTube. Our results show that DeepWalk outperforms challenging baselines which are allowed a global view of the network, especially in the presence of missing information. DeepWalk's representations can provide F1 scores up to 10% higher than competing methods when labeled data is sparse. In some experiments, DeepWalk's representations are able to outperform all baseline methods while using 60% less training data. DeepWalk is also scalable. It is an online learning algorithm which builds useful incremental results, and is trivially parallelizable. These qualities make it suitable for a broad class of real world applications such as network classification, and anomaly detection.
              """
    rec_list, rec_list_ref = citrec(context)
    print(rec_list)
    print(rec_list_ref)
