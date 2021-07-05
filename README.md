# Citation-Recommendation-Bot
A slack chatbot that can recommend citation.

## Requirements
 - MongoDB
 - MongoDB database tools

## Traning
### Python Environment
- Huggingface Transformers Library: `pip install transformers==4.2`
- pymongo: `pip install pymongo`
- tqdm: `pip install tqdm`
- pytorch

### Import dataset
[Download the AMiner dataset](https://www.aminer.org/citation) (current version: v13) at first, and then import it to MongoDB with database name `CitRec` and collection name `AMiner`.
To import, please use following shell command:
```bash
mongoimport --db CitRec --collection AMiner --jsonArray --file <path>/dblpv13.json
```
### Generate paper content embedding
1. Create a collection `Context` only contains `_id`, `title`, `abstract` of the papers.
    ```
    var temp = db.AMiner.find({}, {_id: 1, title: 1, abstract: 1});
    while(temp.hasNext()) db.Context.insert(temp.next());
    ```
2. Run `Spector.py`.
    Note that **the IP address of MongoDB might need to be modified.**
    It may run more then ten hours.
    The generated embedding is in collection `Spector`

## Create paper-paper graph
1. Create a collection `Graph` only contains `_id`, `references` of the papers.
    ```bash
    var temp = db.AMiner.find({}, {_id: 1, references: 1});
    while(temp.hasNext()) db.Graph.insert(temp.next());
    ```
2. Link relevant papers.