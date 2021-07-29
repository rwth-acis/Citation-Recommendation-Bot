from flask import Flask
from citrec.CitRec import CitRec
app = Flask(__name__)

@app.route('/rec/<context>') 
def rec(context):
    citrec = CitRec()
    embedding = citrec.generate_embedding(context)
    ids_relevances = citrec.find_topk_relevant_papers(embedding, 20)
    return str(citrec.find_papers_with_ids_relevances(ids_relevances))
