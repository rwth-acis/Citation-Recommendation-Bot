import networkx as nx
import pymongo
import tqdm


class Graph(nx.Graph):
    def add_nodes_from_docs(self, data_nodes):
        pbar = tqdm.tqdm(total=data_nodes.count())
        pbar.set_description("Add nodes")
        i = 0
        for d in data_nodes:
            if i == 500000:
                pbar.update(500000)
                i = 0
            self.add_node(d["_id"])
            i += 1
        pbar.update(500000)
        pbar.close()

    def add_edges_from_docs(self, data_edges, batch_size):
        edges = []
        i = 0
        pbar = tqdm.tqdm(total=data_edges.count())
        pbar.set_description("Add edges")
        for d in data_edges:
            if i != batch_size:
                papid = d["_id"]
                references = d["references"]
                for ref in references:
                    edges.append([papid, ref])
            else:
                self.add_edges_from(edges)
                pbar.update(batch_size)
                i = 0
                edges = []
                papid = d["_id"]
                references = d["references"]
                for ref in references:
                    edges.append((papid, ref))
            i += 1
        if len(edges) > 0:
            self.add_edges_from(edges)
            pbar.update(batch_size)
            pbar.close()


def main():
    # connect to the MongoDB
    # use command ifconfic to get the ethernet IP
    client = pymongo.MongoClient("134.61.193.185:27017")
    # set collections
    db = client["CitRec"]
    collection = db["Graph"]
    data_nodes = collection.find({}, {"_id": 1})
    data_edges = collection.find(
        {"references": {"$exists": True}}, {"_id": 1, "references": 1}
    )
    graph = Graph()
    graph.add_nodes_from_docs(data_nodes)
    graph.add_edges_from_docs(data_edges, 16)


if __name__ == "__main__":
    main()
