from flask import Flask, render_template
from CitRec import CitRec
app = Flask(__name__)

@app.route('/rec/<context>') 
def rec(context):
    citrec = CitRec()
    rec_list, rec_list_ref = citrec(context)
    # return str(rec_list) + str(rec_list_ref)
    return render_template('rec_result.json.jinja2', context=context, rec_list=rec_list[:10], rec_list_ref=rec_list_ref[:10])