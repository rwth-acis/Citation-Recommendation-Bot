import pymongo
from bson.objectid import ObjectId
from flask import render_template
import datetime


server_adress = "localhost:27017"
client = pymongo.MongoClient(server_adress)
db_citbot = client["CitBot"]
mark_lists = db_citbot["Lists"]
lists_temp = db_citbot["Lists_temp"]
results = db_citbot["Results"]
db_citrec = client["CitRec"]
aminer = db_citrec["AMiner"]
dblp = db_citrec["DBLP"]


def generate_rec_result(context, rec_list, ref_list, user_id):
    try:
        marked_papers = mark_lists.find({"_id": user_id}).next()["marked"]
        for paper in rec_list:
            id_source = str(paper["_id"]) + "," + paper["source"]
            if id_source in marked_papers:
                paper["inList"] = True
            else:
                paper["inList"] = False
        if ref_list:
            for paper in ref_list:
                id_source = str(paper["_id"]) + "," + paper["source"]
                if id_source in marked_papers:
                    paper["inList"] = True
                else:
                    paper["inList"] = False
    except StopIteration:
        pass

    # found classic papers
    if ref_list:
        ref_list_id = ObjectId()
        results.insert_one(
            {
                "_id": ref_list_id,
                "context": context,
                "papers": ref_list,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            }
        )
        rec_list_id = ObjectId()
        results.insert_one(
            {
                "_id": rec_list_id,
                "context": context,
                "papers": rec_list,
                "refId": ref_list_id,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            }
        )
        return {
            "blocks": render_template(
                "rec_result.json.jinja2",
                context=context,
                rec_list=rec_list[:5],
                rec_list_id=rec_list_id,
                ref_list_id=ref_list_id,
                page=0,
            )
        }

    else:
        rec_list_id = ObjectId()
        results.insert_one(
            {
                "_id": rec_list_id,
                "context": context,
                "papers": rec_list,
                "refId": None,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            }
        )
        return {
            "blocks": render_template(
                "rec_result.json.jinja2",
                context=context,
                rec_list=rec_list[:5],
                rec_list_id=rec_list_id,
                ref_list_id=None,
                page=0,
            )
        }


def flip_page_rec(value, time):
    rec_list_id, page = tuple(value.split(","))
    page = int(page)
    try:
        rec_list = results.find({"_id": ObjectId(rec_list_id)}).next()
        return {
            "blocks": render_template(
                "rec_result.json.jinja2",
                context=rec_list["context"],
                rec_list=rec_list["papers"][(page * 5) : (page * 5 + 5)],
                rec_list_id=rec_list["_id"],
                ref_list_id=rec_list["refId"],
                page=page,
            ),
            "updateBlock": "true",
            "ts": time,
        }
    except StopIteration:
        return {
            "text": "This is an outdated message (more than 60 minutes), please send me the citation context again 🥺"
        }


def show_classic_papers(ref_list_id):
    try:
        ref_list = results.find({"_id": ObjectId(ref_list_id)}).next()
        return {
            "blocks": render_template(
                "ref_result.json.jinja2",
                context=ref_list["context"],
                ref_list=ref_list["papers"][:5],
                ref_list_id=ref_list["_id"],
                next_page=True if len(ref_list["papers"]) > 5 else False,
                page=0,
            ),
        }
    except StopIteration:
        return {
            "text": "This is an outdated message (more than 60 minutes), please send me the citation context again 🥺"
        }


def flip_page_ref(value, time):
    ref_list_id, page = tuple(value.split(","))
    page = int(page)
    try:
        ref_list = results.find({"_id": ObjectId(ref_list_id)}).next()
        return {
            "blocks": render_template(
                "ref_result.json.jinja2",
                context=ref_list["context"],
                ref_list=ref_list["papers"][(page * 5) : (page * 5 + 5)],
                ref_list_id=ref_list["_id"],
                next_page=True if len(ref_list["papers"][(page * 5) :]) > 5 else False,
                page=page,
            ),
            "updateBlock": "true",
            "ts": time,
        }
    except StopIteration:
        return {
            "text": "This is an outdated message (more than 60 minutes), please send me the citation context again 🥺"
        }


def add_to_list(value, time, user_id):
    rec_or_ref, ind, page, paper_id, paper_source = tuple(value.split(","))
    page = int(page)
    mark = [paper_id + "," + paper_source]
    try:
        mark_lists.insert_one(
            {
                "_id": user_id,
                "marked": mark,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(days=60),
            }
        )
    except pymongo.errors.DuplicateKeyError:
        mark += mark_lists.find({"_id": user_id}).next()["marked"]
        mark_lists.update(
            {"_id": user_id},
            {
                # delete duplicate papers
                "marked": sorted(set(mark), key=mark.index),
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(days=60),
            },
        )

    try:
        rec_or_ref_result = results.find({"_id": ObjectId(ind)}).next()
        for paper in (rec_or_ref_result["papers"])[(page * 5) :]:
            if paper["_id"] == paper_id or paper["_id"] == ObjectId(paper_id):
                paper["inList"] = True
        results.update_one(
            {"_id": ObjectId(ind)}, {"$set": {"papers": rec_or_ref_result["papers"]}}
        )
        if rec_or_ref == "rec":
            return {
                "blocks": render_template(
                    "rec_result.json.jinja2",
                    context=rec_or_ref_result["context"],
                    rec_list=rec_or_ref_result["papers"][(page * 5) : (page * 5 + 5)],
                    rec_list_id=rec_or_ref_result["_id"],
                    ref_list_id=rec_or_ref_result["refId"],
                    page=page,
                ),
                "updateBlock": "true",
                "ts": time,
            }
        else:
            return {
                "blocks": render_template(
                    "ref_result.json.jinja2",
                    context=rec_or_ref_result["context"],
                    ref_list=rec_or_ref_result["papers"][(page * 5) : (page * 5 + 5)],
                    ref_list_id=rec_or_ref_result["_id"],
                    next_page=True
                    if len(rec_or_ref_result["papers"][(page * 5) :]) > 5
                    else False,
                    page=page,
                ),
                "updateBlock": "true",
                "ts": time,
            }
    except StopIteration:
        return {
            "text": 'I have added this paper to the marking list, send "!list" to see the marking list 😉\n However, this message is outdated, so I could not update the message 🥺'
        }


def find_papers_in_list(user_id):
    try:
        ids_sources = mark_lists.find({"_id": user_id}).next()["marked"]
    except StopIteration:
        return None, []
    finded_papers = []
    for i in range(len(ids_sources)):
        ids_sources[i] = tuple(ids_sources[i].split(","))
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
    list_id = ObjectId()
    lists_temp.insert_one(
        {
            "_id": list_id,
            "papers": finded_papers,
            "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=20),
        }
    )
    return list_id, finded_papers


def flip_page_list(value, time, user_id):
    list_id, page = tuple(value.split(","))
    page = int(page)
    try:
        marked_papers = lists_temp.find({"_id": ObjectId(list_id)}).next()["papers"]
        return {
            "blocks": render_template(
                "mark_list.json.jinja2",
                list_id=list_id,
                marked_papers=marked_papers[(page * 5) : (page * 5 + 5)],
                page=page,
                next_page=True if len(marked_papers[(page * 5) :]) > 5 else False,
            ),
            "updateBlock": "true",
            "ts": time,
        }
    except StopIteration:
        # no temp, find papers in list again
        list_id, marked_papers = find_papers_in_list(user_id)
        return {
            "blocks": render_template(
                "mark_list.json.jinja2",
                list_id=list_id,
                marked_papers=marked_papers[(page * 5) : (page * 5 + 5)],
                page=page,
                next_page=True if len(marked_papers[(page * 5) :]) > 5 else False,
            ),
            "updateBlock": "true",
            "ts": time,
        }


def del_paper_in_list(value, time, user_id):
    list_id, paper_id, paper_source, page = tuple(value.split(","))
    page = int(page)

    try:
        marked_papers = mark_lists.find({"_id": user_id}).next()["marked"]
    except StopIteration:
        return {
            "text": "Your marking list expired due to long periods of inactivity), please add items into the marking list again 🥺"
        }

    try:
        # delete the papers id in Lists
        marked_papers.remove(paper_id + "," + paper_source)
        mark_lists.update_one({"_id": user_id}, {"$set": {"marked": marked_papers}})
        # delete from the temp
        marked_papers = lists_temp.find({"_id": ObjectId(list_id)}).next()["papers"]
        for paper in marked_papers:
            if paper["_id"] == paper_id or paper["_id"] == ObjectId(paper_id):
                marked_papers.remove(paper)
                break
        lists_temp.update(
            {"_id": ObjectId(list_id)}, {"$set": {"papers": marked_papers}}
        )
        return {
            "blocks": render_template(
                "mark_list.json.jinja2",
                list_id=list_id,
                marked_papers=marked_papers[(page * 5) : (page * 5 + 5)],
                page=page,
                next_page=True if len(marked_papers[(page * 5) :]) > 5 else False,
            ),
            "updateBlock": "true",
            "ts": time,
        }
    # no temp, find papers in list again
    except (StopIteration, ValueError):
        list_id, marked_papers = find_papers_in_list(user_id)
        return {
            "blocks": render_template(
                "mark_list.json.jinja2",
                list_id=list_id,
                marked_papers=marked_papers[(page * 5) : (page * 5 + 5)],
                page=page,
                next_page=True if len(marked_papers[(page * 5) :]) > 5 else False,
            ),
            "updateBlock": "true",
            "ts": time,
        }
