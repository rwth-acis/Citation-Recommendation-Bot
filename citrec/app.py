from flask import Flask, render_template
from bson.objectid import ObjectId
import pymongo
import datetime

# from CitRec import CitRec


app = Flask(__name__)
server_adress = "mongodb"
client = pymongo.MongoClient(server_adress)
db = client["CitBot"]
mark_list = db["List"]
selected_items = db["Items"]


@app.route("/rec/<context>")
def rec(context):
    # citrec = CitRec()
    # rec_list, rec_list_ref = citrec(context)
    file = open("rec_list.txt", "r")
    rec_list = eval(file.read())
    file.close()
    # return str(rec_list) + str(rec_list_ref)
    return render_template(
        "rec_result.json.jinja2",
        context=context,
        rec_list=rec_list[:10],
        rec_list_ref=[],
    )


@app.route("/actions/<payload>")
def actions(payload):
    msg = eval(payload)
    print(payload)
    if isinstance(msg["msg"], list):
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
    else:
        if "list" in msg["msg"]:
            try:
                marked = selected_items.find(
                    {"_id": str(msg["user"]) + str(msg["time"])}
                ).next()["selected"]
            except StopIteration:
                return {
                    "text": "No items have been selected (or data expired due to long periods of inactivity), please select items at first 🥺"
                }
            try:
                mark_list.insert_one(
                    {
                        "_id": str(msg["user"]),
                        "marked": marked,
                        "expireAt": datetime.datetime.utcnow()
                        + datetime.timedelta(days=60),
                    }
                )
            except pymongo.errors.DuplicateKeyError:
                mark_list.insert_one(
                    {"_id": str(msg["user"])},
                    {
                        "marked": marked,
                        "expireAt": datetime.datetime.utcnow()
                        + datetime.timedelta(days=60),
                    },
                )
            return {
                "text": 'Selected items have been added to the marking list, send "!list" to see the marking list 😉'
            }
