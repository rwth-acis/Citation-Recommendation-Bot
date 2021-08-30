from flask import Flask, render_template
from bson.objectid import ObjectId
import pymongo
import datetime
from CitRec import CitRec


app = Flask(__name__)
server_adress = "localhost:27017"
client = pymongo.MongoClient(server_adress)
db_citbot = client["CitBot"]
mark_list = db_citbot["Lists"]
selected_items = db_citbot["Items"]
db_citrec = client["CitRec"]
aminer = db_citrec["AMiner"]
dblp = db_citrec["DBLP"]


def find_papers(ids_sources):
    finded_papers = []
    for i in range(len(ids_sources)):
        ids_sources[i] = tuple(ids_sources[i].split(','))
    for i, source in ids_sources:
        if source == "dblp":
            try:
                dic = dblp.find(
                    {"_id": ObjectId(i)},
                    {
                        "title": 1,
                        "author": 1,
                        "year": 1,
                        "booktitle": 1,
                        "journal": 1,
                        "ee": 1,
                    },
                ).next()
            except StopIteration:
                dic = dblp.find(
                    {"_id": i},
                    {
                        "title": 1,
                        "author": 1,
                        "year": 1,
                        "booktitle": 1,
                        "journal": 1,
                        "ee": 1,
                    },
                ).next()
            dic["source"] = "dblp"
            finded_papers.append(dic)
        else:
            try:
                dic = aminer.find(
                    {"_id": i},
                    {
                        "title": 1,
                        "authors.name": 1,
                        "venue.raw": 1,
                        "year": 1,
                        "url": 1,
                    },
                ).next()
            except StopIteration: 
                dic = aminer.find(
                    {"_id": ObjectId(i)},
                    {
                        "title": 1,
                        "authors.name": 1,
                        "venue.raw": 1,
                        "year": 1,
                        "url": 1,
                    },
                ).next()
            dic["source"] = "aminer"
            finded_papers.append(dic)
    return finded_papers


@app.route("/rec/<context>")
def rec(context):
    citrec = CitRec()
    rec_list, rec_list_ref = citrec(context)
    # file = open("rec_list.txt", "r")
    # rec_list = eval(file.read())
    # file.close()
    return render_template(
        "rec_result.json.jinja2",
        context=context,
        rec_list=rec_list[:10],
        rec_list_ref=rec_list_ref[:10],
    )


@app.route("/actions/<payload>")
def actions(payload):
    msg = eval(payload)
    print(payload)
    # Select items in the checkbox, store the selected items
    if isinstance(msg["msg"], list) or msg["msg"] == "[]":
        try:
            selected_items.insert_one(
                {
                    "_id": str(msg["user"]) + str(msg["time"]),
                    "selected": msg["msg"],
                    "expireAt": datetime.datetime.utcnow()
                    + datetime.timedelta(minutes=30),
                }
            )
        except pymongo.errors.DuplicateKeyError:
            selected_items.update(
                {"_id": str(msg["user"]) + str(msg["time"])},
                {
                    "selected": msg["msg"],
                    "expireAt": datetime.datetime.utcnow()
                    + datetime.timedelta(minutes=30),
                },
            )
        return "Selected items have been stored."

    # clicked the add2list button 
    elif "list" in msg["msg"]:
        try:
            mark = selected_items.find(
                {"_id": str(msg["user"]) + str(msg["time"])}
            ).next()["selected"]
        except StopIteration:
            return {
                "text": "No items have been selected (or data expired due to long periods of inactivity), please select items at first 🥺"
            }
        if mark == "[]":
            return {
                "text": "No items have been selected, please select items at first 🥺"
            }
        else: 
            try:
                mark_list.insert_one(
                    {
                        "_id": str(msg["user"]),
                        "marked": mark,
                        "expireAt": datetime.datetime.utcnow()
                        + datetime.timedelta(days=60),
                    }
                )
            except pymongo.errors.DuplicateKeyError:
                mark += mark_list.find({"_id": str(msg["user"])}).next()["marked"]
                mark_list.update(
                    {"_id": str(msg["user"])},
                    {
                        # delete duplicate papers
                        "marked": sorted(set(mark),key=mark.index),
                        "expireAt": datetime.datetime.utcnow()
                        + datetime.timedelta(days=60),
                    },
                )
            return {
                "text": 'Selected items have been added to the marking list, send "!list" to see the marking list 😉'
            }
    return {
                "text": 'An error occurred 😖'
            }


@app.route("/lists/<payload>")
def lists(payload):
    msg = eval(payload)
    try:
        marked_ids = mark_list.find({"_id": str(msg["user"])}).next()["marked"]
    except StopIteration:
        return {
            "text": "No papers in your marking list (or data expired due to long periods of inactivity), please add items into the marking list at first 🥺"
        }
    marked_papers = find_papers(marked_ids)
    return render_template(
        "mark_list.json.jinja2",
        marked_papers = marked_papers
    )
