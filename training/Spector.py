from transformers import AutoModel, AutoTokenizer
import pymongo
from tqdm.auto import tqdm
import torch


class Dataset:
    def __init__(
        self, source_collection, target_collection, batch_size, max_length=512
    ):
        self.tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
        self.max_length = max_length
        self.batch_size = batch_size
        # set collections
        self.source_collection = source_collection
        self.target_collection = target_collection
        self.documents = self.source_collection.find()

    def __len__(self):
        return self.documents.count()

    def batches(self):
        # create batches
        batch = []
        batch_ids = []
        batch_size = self.batch_size
        i = 0
        for d in self.documents:
            if i % batch_size != 0 or i == 0:
                batch.append((d.get("title") or "") + " " + (d.get("abstract") or ""))
                d.pop("title", None)
                d.pop("abstract", None)
                batch_ids.append(d)
            else:
                input_ids = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    max_length=self.max_length,
                )
                yield input_ids.to(
                    "cuda" if torch.cuda.is_available() else "cpu"
                ), batch_ids
                batch = []
                batch_ids = []
                batch.append((d.get("title") or "") + " " + (d.get("abstract") or ""))
                d.pop("title", None)
                d.pop("abstract", None)
                batch_ids.append(d)
            i += 1
        if len(batch) > 0:
            input_ids = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=self.max_length,
            )
            input_ids = input_ids.to("cuda" if torch.cuda.is_available() else "cpu")
            yield input_ids, batch_ids


class Model:
    def __init__(self):
        self.model = AutoModel.from_pretrained("allenai/specter")
        self.model.to("cuda" if torch.cuda.is_available() else "cpu")
        self.model.eval()

    def __call__(self, input_ids):
        output = self.model(**input_ids)
        return output.last_hidden_state[:, 0, :]  # cls token


if __name__ == "__main__":
    # empty cache
    torch.cuda.empty_cache()
    # connect to the MongoDB
    # use command ifconfic to get the ethernet IP
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    # set collections
    db = client["CitRec"]
    source_collection = db["Context"]
    target_collection = db["Spector"]
    # set bach size
    batch_size = 16
    dataset = Dataset(
        source_collection=source_collection,
        target_collection=target_collection,
        batch_size=batch_size,
    )
    model = Model()
    for batch, batch_ids in tqdm(
        dataset.batches(), total=len(dataset) // batch_size + 1
    ):
        embeddings = model(batch).detach().cpu().numpy().tolist()
        torch.cuda.empty_cache()
        for i, embedding in enumerate(embeddings):
            batch_ids[i]["embedding"] = embedding
        target_collection.insert(batch_ids)
