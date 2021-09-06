from flask import Flask, render_template
from bson.objectid import ObjectId
import pymongo
import datetime

from CitRec import CitRec
import CitBot

app = Flask(__name__)
server_adress = "localhost:27017"
client = pymongo.MongoClient(server_adress)
db_citbot = client["CitBot"]
mark_lists = db_citbot["Lists"]
results = db_citbot["Results"]
db_citrec = client["CitRec"]
aminer = db_citrec["AMiner"]
dblp = db_citrec["DBLP"]


@app.route("/rec/<payload>")
def rec(payload):
    payload = eval(payload)
    citrec = CitRec()
    rec_list, ref_list = citrec(payload["context"])
    return CitBot.generate_rec_result(context=payload["context"], rec_list=rec_list, ref_list=ref_list, user_id=payload["user"])


@app.route("/actions/<payload>")
def actions(payload):
    payload = eval(payload)
    actionInfo = eval(payload["actionInfo"])
    print(payload)

    # when clicking previous page and next page in recommendation result list
    if actionInfo["actionId"] == "next_rec" or actionInfo["actionId"] == "previous_rec":
        return CitBot.flip_page_rec(value=actionInfo["value"], time=payload["time"])

    # when clicking see classic papers
    elif actionInfo["actionId"] == "classic":
        return CitBot.show_classic_papers(ref_list_id=actionInfo["value"])

    # when clicking previous page and next page in classic paper list
    elif (
        actionInfo["actionId"] == "previous_ref" or actionInfo["actionId"] == "next_ref"
    ):
        return CitBot.flip_page_ref(value=actionInfo["value"], time=payload["time"])

    # when clicking the add2list button
    elif actionInfo["actionId"] == "add2list":
        return CitBot.add_to_list(
            value=actionInfo["value"], time=payload["time"], user_id=payload["user"]
        )

    # when clicking the delete button
    elif actionInfo["actionId"] == "del":
        return CitBot.del_paper_in_list(
            value=actionInfo["value"], time=payload["time"], user_id=payload["user"]
        )

    # when clicking previous page and next page in marking list
    elif (
        actionInfo["actionId"] == "next_list"
        or actionInfo["actionId"] == "previous_list"
    ):
        return CitBot.flip_page_list(
            value=actionInfo["value"], time=payload["time"], user_id=payload["user"]
        )
    
    elif actionInfo["actionId"] == "delall":
        return 

    return {"text": "An error occurred 😖"}


@app.route("/lists/<payload>")
def lists(payload):
    payload = eval(payload)
    user_id = str(payload["user"])
    list_id, marked_papers = CitBot.find_papers_in_list(user_id)
    print(len(marked_papers))
    if not list_id:
        return {
            "text": "No papers in your marking list (or data expired due to long periods of inactivity), please add items into the marking list at first 🥺"
        }
    else:
        return {
            "blocks": render_template(
                "mark_list.json.jinja2",
                list_id=list_id,
                marked_papers=marked_papers[:5],
                page=0,
                next_page=True if len(marked_papers) > 5 else False,
            )
        }
