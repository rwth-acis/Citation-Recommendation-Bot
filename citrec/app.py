from flask import Flask
from CitRec import CitRec
app = Flask(__name__)

@app.route('/rec/<context>') 
def rec(context):
    citrec = CitRec()
    rec_list, rec_list_ref = citrec(context)
    return str(rec_list) + str(rec_list_ref)
