from flask import Flask, render_template
import pymongo
import json
from CitRec import CitRec
import CitBot
import configparser

config = configparser.ConfigParser()
config.read("config.ini")

K = int(config.get("DEFAULT", "k"))
if K % 5 == 0:
    PAGE_MAX = K // 5 - 1
else:
    PAGE_MAX = K // 5

app = Flask(__name__)
SERVER_ADDRESS = config.get("DEFAULT", "server_address")
CLIENT = pymongo.MongoClient(SERVER_ADDRESS)
DB_CITBOT = CLIENT["CitBot"]
MARK_LIST = DB_CITBOT["Lists"]
RESULTS = DB_CITBOT["Results"]
DB_CITREC = CLIENT["CitRec"]
AMINER = DB_CITREC["AMiner"]
DBLP = DB_CITREC["DBLP"]
"""These codes are for evaluation"""
TIMES = DB_CITBOT["Times"]
"""""" """""" """"end""" """""" """""" ""


@app.route("/rec/<payload>")
def rec(payload):
    """(command "!rec") Gnerate rec results

    Args:
        payload (string): a json string, contains fields "context" and "channel"

    Returns:
        string: a block message contains recommendation result that should be sent to slack
    """
    payload = json.loads(payload)
    print(payload)
    channel_id = payload["channel"]
    context = payload["context"]
    citrec = CitRec()
    rec_list, ref_list = citrec(context=context, k=K)
    """These codes are for evaluation"""
    try:
        rec_times = TIMES.find({"_id": channel_id}).next()["rec"]
        TIMES.update_one({"_id": channel_id}, {"$set": {"rec": rec_times + 1}})
    except StopIteration:
        TIMES.insert_one({"_id": channel_id, "rec": 1, "kw": 0, "list": 0, "bib": 0})
    """""" """""" """"end""" """""" """""" ""
    return CitBot.generate_rec_result(
        context=context,
        rec_list=rec_list,
        ref_list=ref_list,
        channel_id=channel_id,
        PAGE_MAX=PAGE_MAX,
    )


@app.route("/actions/<payload>")
def actions(payload):
    """Interacte with actions

    Args:
        payload  (string): a json string, contains fields "actionInfo" and "channel" and "time"

    Returns:
        string: a message that should be sent to slack
    """
    payload = json.loads(payload)
    actionInfo = json.loads(payload["actionInfo"])
    print(payload)

    # when clicking previous page and next page in recommendation result list
    if actionInfo["actionId"] == "next_rec" or actionInfo["actionId"] == "previous_rec":
        return CitBot.flip_page_rec(
            value=actionInfo["value"],
            time=payload["time"],
            channel_id=payload["channel"],
            PAGE_MAX=PAGE_MAX,
        )

    # when clicking see classic papers
    elif actionInfo["actionId"] == "classic":
        return CitBot.show_classic_papers(
            ref_list_id=actionInfo["value"], channel_id=payload["channel"]
        )

    # when clicking previous page and next page in classic paper list
    elif (
        actionInfo["actionId"] == "previous_ref" or actionInfo["actionId"] == "next_ref"
    ):
        return CitBot.flip_page_ref(
            value=actionInfo["value"],
            time=payload["time"],
            channel_id=payload["channel"],
        )

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

    # when clicking In the list button
    elif actionInfo["actionId"] == "inList":
        return CitBot.remove_from_list(
            value=actionInfo["value"],
            time=payload["time"],
            channel_id=payload["channel"],
            PAGE_MAX=PAGE_MAX,
        )

    # when clicking delete all button in the marking list message
    elif actionInfo["actionId"] == "delall":
        return CitBot.delete_all(channel_id=payload["channel"])

    # when clicking previous page and next page in keyword search result
    elif actionInfo["actionId"] == "next_kw" or actionInfo["actionId"] == "previous_kw":
        return CitBot.flip_page_kw(
            value=actionInfo["value"],
            time=payload["time"],
            channel_id=payload["channel"],
            PAGE_MAX=PAGE_MAX,
        )

    # when submitting feedback (modal message)
    elif actionInfo["actionId"] == "feedback_submit":
        return CitBot.handle_feedback(value=actionInfo["value"])

    # when clicking generate bibtex button in the marking list
    elif actionInfo["actionId"] == "bibtex":
        """These codes are for evaluation"""
        channel_id=payload["channel"]
        try:
            bib_times = TIMES.find({"_id": channel_id}).next()["bib"]
            TIMES.update_one({"_id": channel_id}, {"$set": {"bib": bib_times + 1}})
        except StopIteration:
            TIMES.insert_one({"_id": channel_id, "rec": 0, "kw": 0, "list": 0, "bib": 1})
        """""" """""" """"end""" """""" """""" ""
        return CitBot.generate_bibtex_list(value=actionInfo["value"])

    # when cliking send feedback button
    elif actionInfo["actionId"] == "feedback":
        return CitBot.send_feedback_modal(
            trigger_id=actionInfo["triggerId"],
            value=actionInfo["value"],
            channel_id=payload["channel"],
        )

    # when clicking get help button
    elif actionInfo["actionId"] == "help":
        return {"text": render_template("indications.json.jinja2")}

    else:
        return {"text": "An error occurred 😖"}


@app.route("/lists/<payload>")
def lists(payload):
    """(Command "!list") Collection information for papers in the marking list and send a message shows the marking list

    Args:
        payload (string): a json string, contains field "channel"

    Returns:
        string: a block message contains marking list that should be sent to slack
    """
    payload = json.loads(payload)
    channel_id = payload["channel"]
    list_id, marked_papers = CitBot.find_papers_in_list(channel_id)
    """These codes are for evaluation"""
    try:
        list_times = TIMES.find({"_id": channel_id}).next()["list"]
        TIMES.update_one({"_id": channel_id}, {"$set": {"list": list_times + 1}})
    except StopIteration:
        TIMES.insert_one({"_id": channel_id, "rec": 0, "kw": 0, "list": 1, "bib": 0})
    """""" """""" """"end""" """""" """""" ""
    if (not list_id) or marked_papers == []:
        return {
            "text": "No papers in your marking list, please add items into the marking list at first 🥺"
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
    """(Command "!kw") search for papers based on keyworks send a message shows the result

    Args:
        payload (string): a json string, contains fields "keywords" and "channel"

    Returns:
        string: a block message contains keyword search result that should be sent to slack
    """
    payload = json.loads(payload)
    print(payload)
    keywords = payload["keywords"]
    channel_id = payload["channel"]
    """These codes are for evaluation"""
    try:
        kw_times = TIMES.find({"_id": channel_id}).next()["kw"]
        TIMES.update_one({"_id": channel_id}, {"$set": {"kw": kw_times + 1}})
    except StopIteration:
        TIMES.insert_one({"_id": channel_id, "rec": 0, "kw": 1, "list": 0, "bib": 0})
    """""" """""" """"end""" """""" """""" ""
    return CitBot.keywords_search(
        keywords=keywords,
        channel_id=channel_id,
        k=K,
        PAGE_MAX=PAGE_MAX,
    )
