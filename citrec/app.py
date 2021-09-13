from flask import Flask, render_template
import pymongo
import json

from CitRec import CitRec
import CitBot


K = 50
if K % 5 == 0:
    PAGE_MAX = K // 5 - 1
else:
    PAGE_MAX = K // 5

app = Flask(__name__)
SERVER_ADDRESS = "localhost:27017"
CLIENT = pymongo.MongoClient(SERVER_ADDRESS)
DB_CITBOT = CLIENT["CitBot"]
MARK_LIST = DB_CITBOT["Lists"]
RESULTS = DB_CITBOT["Results"]
DB_CITREC = CLIENT["CitRec"]
AMINER = DB_CITREC["AMiner"]
DBLP = DB_CITREC["DBLP"]


@app.route("/rec/<payload>")
def rec(payload):
    payload = json.loads(payload)
    citrec = CitRec()
    rec_list, ref_list = citrec(context=payload["context"], k=K)
    return CitBot.generate_rec_result(
        context=payload["context"],
        rec_list=rec_list,
        ref_list=ref_list,
        channel_id=payload["channel"],
        PAGE_MAX=PAGE_MAX,
    )


@app.route("/actions/<payload>")
def actions(payload):
    payload = json.loads(payload)
    actionInfo = json.loads(payload["actionInfo"])
    print(payload)

    # when clicking previous page and next page in recommendation result list
    if actionInfo["actionId"] == "next_rec" or actionInfo["actionId"] == "previous_rec":
        return CitBot.flip_page_rec(
            value=actionInfo["value"], time=payload["time"], PAGE_MAX=PAGE_MAX
        )

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
            value=actionInfo["value"],
            time=payload["time"],
            channel_id=payload["channel"],
            PAGE_MAX=PAGE_MAX,
        )

    # when clicking the delete button
    elif actionInfo["actionId"] == "del":
        return CitBot.del_paper_in_list(
            value=actionInfo["value"],
            time=payload["time"],
            channel_id=payload["channel"],
        )

    # when clicking previous page and next page in marking list
    elif (
        actionInfo["actionId"] == "next_list"
        or actionInfo["actionId"] == "previous_list"
    ):
        return CitBot.flip_page_list(
            value=actionInfo["value"],
            time=payload["time"],
            channel_id=payload["channel"],
        )

    elif actionInfo["actionId"] == "inList":
        return CitBot.remove_from_list(
            value=actionInfo["value"],
            time=payload["time"],
            channel_id=payload["channel"],
            PAGE_MAX=PAGE_MAX,
        )

    elif actionInfo["actionId"] == "delall":
        return CitBot.delete_all(channel_id=payload["channel"])

    elif actionInfo["actionId"] == "next_kw" or actionInfo["actionId"] == "previous_kw":
        return CitBot.flip_page_kw(
            value=actionInfo["value"], time=payload["time"], PAGE_MAX=PAGE_MAX
        )

    elif actionInfo["actionId"] == "feedback_submit":
        return CitBot.handle_feedback(value=actionInfo["value"])

    elif actionInfo["actionId"] == "bibtex":
        return CitBot.generate_bibtex_list(value=actionInfo["value"])

    elif actionInfo["actionId"] == "feedback":
        return CitBot.send_feedback_modal(
            trigger_id=actionInfo["triggerId"],
            value=actionInfo["value"],
            channel_id=payload["channel"],
        )

    elif actionInfo["actionId"] == "help":
        return {"text": render_template("indications.json.jinja2")}

    else:
        return {"text": "An error occurred 😖"}


@app.route("/lists/<payload>")
def lists(payload):
    payload = json.loads(payload)
    channel_id = payload["channel"]
    list_id, marked_papers = CitBot.find_papers_in_list(channel_id)
    if (not list_id) or marked_papers == []:
        return {
            "text": "No papers in your marking list (or data expired due to long periods (over 60 days) of inactivity), please add items into the marking list at first 🥺"
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


@app.route("/keywords/<payload>")
def keywords(payload):
    payload = json.loads(payload)
    print(payload)
    return CitBot.keywords_search(
        keywords=payload["keywords"],
        channel_id=payload["channel"],
        k=K,
        PAGE_MAX=PAGE_MAX,
    )
