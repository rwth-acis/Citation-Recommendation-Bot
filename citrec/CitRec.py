import torch
import pymongo
from transformers import AutoModel, AutoTokenizer
import yake
from nltk.stem.snowball import SnowballStemmer
from nltk.stem import WordNetLemmatizer


server_adress = "mongodb://localhost:27017/"


def load_embeddings(server_adress):
    client = pymongo.MongoClient(server_adress)
    ids_embeddings = client["CitRec"]["Citavi_Spector"].find()

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
    ids, paper_embeddings = load_embeddings(server_adress)

    def __init__(self):
        self.server_adress = server_adress
        self.client = pymongo.MongoClient(server_adress)
        self.db = self.client["CitRec"]
        self.citavi = self.db["Citavi"]
        self.citavi_embeddings = self.db["Citavi_Spector"]
        self.aminer = self.db["AMiner"]
        self.aminer_embeddings = self.db["Spector"]
        self.cos = CosineSimilarity().to("cpu")
        self.tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
        self.model = AutoModel.from_pretrained("allenai/specter")
        self.stemmer = SnowballStemmer("english", ignore_stopwords=True)
        self.lemmatizer = WordNetLemmatizer()
        self.kw_extractor = yake.KeywordExtractor(n=1)

    def generate_embedding(self, context):
        # Calculate embedding of input context
        inputs = self.tokenizer(
            context, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        result = self.model(**inputs)
        # take the first token in the batch as the embedding
        embedding = result.last_hidden_state[:, 0, :].reshape(-1, 1)

        return embedding

    def find_topk_relevant_papers(self, embedding, k):
        
        relevances_all = self.cos(CitRec.paper_embeddings, embedding)
        relevances, indec = torch.topk(
            relevances_all, k, dim=0, largest=True, sorted=True
        )

        relevances = relevances.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()
        indec = indec.detach().reshape(1, -1).squeeze().cpu().numpy().tolist()

        ids_relevances = []
        for i, rel in zip(indec, relevances):
            ids_relevances.append((CitRec.ids[i], rel))

        return ids_relevances   

    def consider_references(self, embedding, ids_relevances, threshold=5):
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
        frequency = sorted(frequency.items(), key = lambda kv:(kv[1], kv[0]),reverse=True)

        new_ids = []
        new_x1 = []
        for i, freq in frequency:
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

        return ids_relevances_ref

    def find_papers_with_ids_relevances(self, ids_relevances):
        rec_list = []
        for i, rel in ids_relevances:
            dic = self.aminer.find({"_id": i},{"title": 1}).next()
            dic["rel_score"] = rel
            rec_list.append(dic)
        return rec_list
    
    def search_newst(self, context, ids_relevances):
        kv_freq = {}

        context = " ".join(self.stemmer.stem(self.lemmatizer.lemmatize(w)) for w in context.split())
        keywords = self.kw_extractor.extract_keywords(context)
        for kv, _ in keywords:
            if kv not in kv_freq:
                kv_freq[kv] = 2

        for i, _ in ids_relevances:
            context = self.aminer.find({"_id": i},{"_id": 0, "title": 1, "abstract": 1}).next()
            context = ((context.get("title") or "") + " " + (context.get("abstract") or " ")).lower()
            context = " ".join(self.stemmer.stem(self.lemmatizer.lemmatize(w)) for w in context.split())
            keywords = self.kw_extractor.extract_keywords(context)
            for kv, _ in keywords:
                if kv not in kv_freq:
                    kv_freq[kv] = 1
                else:
                    kv_freq[kv] += 1
        
        keywords = []
        kv_freq = sorted(kv_freq.items(), key = lambda kv:(kv[1], kv[0]),reverse=True)
        print(kv_freq)
        for i, (kv, freq) in enumerate(kv_freq):
            if i == 3:
                break
            if freq >= 10:
                keywords.append(kv)
            
        print(keywords)


if __name__ == "__main__":

    citrec = CitRec()

    context = """
DeepWalk: Online Learning of Social Representations. We present DeepWalk, a novel approach for learning latent representations of vertices in a network. These latent representations encode social relations in a continuous vector space, which is easily exploited by statistical models. DeepWalk generalizes recent advancements in language modeling and unsupervised feature learning (or deep learning) from sequences of words to graphs. DeepWalk uses local information obtained from truncated random walks to learn latent representations by treating walks as the equivalent of sentences. We demonstrate DeepWalk's latent representations on several multi-label network classification tasks for social networks such as BlogCatalog, Flickr, and YouTube. Our results show that DeepWalk outperforms challenging baselines which are allowed a global view of the network, especially in the presence of missing information. DeepWalk's representations can provide F1 scores up to 10% higher than competing methods when labeled data is sparse. In some experiments, DeepWalk's representations are able to outperform all baseline methods while using 60% less training data. DeepWalk is also scalable. It is an online learning algorithm which builds useful incremental results, and is trivially parallelizable. These qualities make it suitable for a broad class of real world applications such as network classification, and anomaly detection.              """
    embedding = citrec.generate_embedding(context)
    ids_relevances = citrec.find_topk_relevant_papers(embedding, 20)
    # ids_relevances_ref = citrec.consider_references(embedding, ids_relevances, threshold=5)
    # citrec.find_papers_with_ids_relevances(ids_relevances)
    # citrec.find_papers_with_ids_relevances(ids_relevances_ref)
    citrec.search_newst(context, ids_relevances)
