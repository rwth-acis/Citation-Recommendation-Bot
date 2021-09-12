import pymongo
from bson.objectid import ObjectId
from flask import render_template
import datetime
import json
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import bibtex_dblp.dblp_api
import numpy as np
import requests
import pybtex.database

# Only 3 threads for finding bibtex (avoid blocking)
POOL = ThreadPoolExecutor(max_workers=3)


SERVER_ADDRESS = "localhost:27017"
CLIENT = pymongo.MongoClient(SERVER_ADDRESS)
DB_CITBOT = CLIENT["CitBot"]
MARK_LISTS = DB_CITBOT["Lists"]
LIST_TEMP = DB_CITBOT["Lists_temp"]
BIBTEX = DB_CITBOT["Bibtex"]
SUGGESTIONS = DB_CITBOT["Suggestions"]
FEEDBACKS = DB_CITBOT["Feedbacks"]
RESULTS = DB_CITBOT["Results"]
DB_CITREC = CLIENT["CitRec"]
AMINER = DB_CITREC["AMiner"]
DBLP = DB_CITREC["DBLP"]
"""These codes are for evaluation"""
EVALUATION = DB_CITBOT["Evaluation"]
"""""" """""" """"end""" """""" """""" ""


def generate_bibtex_one(paper, paper_id, paper_source):

    # Using doi api
    doi = paper.get("doi")
    if not doi:
        url = paper.get("url")
        if isinstance(url, str):
            if url.startswith("https://doi.org/"):
                doi = url.replace("https://doi.org/", "")
            elif url.startswith("http://doi.org/"):
                doi = url.replace("http://doi.org/", "")
            elif url.startswith("http://dx.doi.org/"):
                doi = url.replace("http://dx.doi.org/", "")
            elif url.startswith("https://dx.doi.org/"):
                doi = url.replace("https://dx.doi.org/", "")
        elif isinstance(url, list):
            for u in url:
                if u.startswith("https://doi.org/"):
                    doi = u.replace("https://doi.org/", "")
                elif u.startswith("http://doi.org/"):
                    doi = u.replace("http://doi.org/", "")
                elif u.startswith("http://dx.doi.org/"):
                    doi = u.replace("http://dx.doi.org/", "")
                elif u.startswith("http://dx.doi.org/"):
                    doi = u.replace("http://dx.doi.org/", "")
    if not doi:
        url = paper.get("ee")
        if isinstance(url, str):
            if url.startswith("https://doi.org/"):
                doi = url.replace("https://doi.org/", "")
        elif isinstance(url, list):
            for u in url:
                if u.startswith("https://doi.org/"):
                    doi = u.replace("https://doi.org/", "")
    if doi: 
        url = 'http://dx.doi.org/' + doi
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/x-bibtex')
        try:
            with urllib.request.urlopen(req) as f:
                bib_string = f.read().decode()
            BIBTEX.insert_one({"_id": paper_id + "," + paper_source, "bib": bib_string})
            return
        except:
            pass

    title = paper.get("title") or ''
    year = eval(paper.get("year"))
    key_id = None
    author = paper.get("authors")
    if not author:
        author = paper.get("author") or ''
    if author and year:
        if isinstance(author, str):
            key_id = author.split()[-1] + '_' + str(
                eval(year) % 100
            )
        elif isinstance(author, list):
            author = author[0]
            if isinstance(author, dict):
                author = author["name"]
            key_id = author.split()[-1] + '_' + str(
                eval(year) % 100
            )
    # Using DBLP api (cannot find bibtex using doi)
    query = f'{title} {author}'
    try:
        search_results = bibtex_dblp.dblp_api.search_publication(query, max_search_results=2)
        assert search_results.total_matches != 0
        pubs = [result.publication for result in search_results.results]
        is_arxiv = [pub.venue == 'CoRR' for pub in pubs]
        if len(is_arxiv) == 1:
            # only one match, no other choice
            pub = pubs[0]
        elif np.sum(is_arxiv) == 1:
            # one is arxiv and the other is not, use the non-arxiv one
            pub = pubs[np.argmin(is_arxiv)]
        else:
            # two pubs are non arxiv, use the first one as the first one matches more info
            pub = pubs[0]
        bytes = requests.get(f'{pub.url}.bib')
        updated_entries = pybtex.database.parse_bytes(bytes.content, bib_format="bibtex")
        assert len(updated_entries.entries) == 1
        for new_key in updated_entries.entries:
            updated_entry = updated_entries.entries[new_key]
        if pub.venue == 'CoRR':
            # hard-coding for arxiv publications
            updated_entry.fields['journal'] = f'arXiv preprint arXiv:{updated_entry.fields["volume"][4:]}'
        updated_entry.key = key_id
        BIBTEX.insert_one({"_id": paper_id + "," + paper_source, "bib": updated_entry.to_string("bibtex")})
    except:
        pass

    # using betterbib package (crossref api)
    bib_db = BibDatabase()
    if doi:
        bib_db.entries = [{"ENTRYTYPE": "artical", "title": title, "author": author, "doi": doi}]
    else:
        bib_db.entries = [{"ENTRYTYPE": "artical", "title": title, "author": author}]
    
    writer = BibTexWriter()
    file_name = str(ObjectId())
    file_parth = "./bib_cache/" + file_name + ".bib"
    try:
        with open(file_parth, "w") as bibfile:
            bibfile.write(writer.write(bib_db))
        subprocess.call(["betterbib", "-i", "-t", file_parth])
        subprocess.call(["sed", "-i", "1,2d", file_parth])
        bib_string = open(file_parth).read()
        BIBTEX.insert_one({"_id": paper_id + "," + paper_source, "bib": bib_string})
        subprocess.call(["rm", file_parth])
    except: 
        subprocess.call(["rm", file_parth])


def generate_rec_result(context, rec_list, ref_list, channel_id, PAGE_MAX):
    try:
        marked_papers = MARK_LISTS.find({"_id": channel_id}).next()["marked"]
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
        for paper in rec_list:
            paper["inList"] = False
        if ref_list:
            for paper in ref_list:
                paper["inList"] = False

    # found classic papers
    if ref_list:
        ref_list_id = ObjectId()
        RESULTS.insert_one(
            {
                "_id": ref_list_id,
                "context": context,
                "papers": ref_list,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            }
        )
        rec_list_id = ObjectId()
        RESULTS.insert_one(
            {
                "_id": rec_list_id,
                "context": context,
                "papers": rec_list,
                "refId": ref_list_id,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            }
        )
        """These codes are for evaluation"""
        add2list = 0
        for paper in rec_list[:5]:
            if paper["inList"] == True:
                add2list += 1
        EVALUATION.insert_one(
            {
                "_id": ObjectId(rec_list_id),
                "max_page": 1,
                "add2list": add2list,
                "context": context,
            }
        )
        """""" """""" """"end""" """""" """""" ""
        return {
            "blocks": render_template(
                "rec_result.json.jinja2",
                context=context,
                rec_list=rec_list[:5],
                rec_list_id=rec_list_id,
                ref_list_id=ref_list_id,
                page=0,
                PAGE_MAX=PAGE_MAX,
            )
        }

    else:
        rec_list_id = ObjectId()
        RESULTS.insert_one(
            {
                "_id": rec_list_id,
                "context": context,
                "papers": rec_list,
                "refId": None,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            }
        )
        """These codes are for evaluation"""
        add2list = 0
        for paper in rec_list[:5]:
            if paper["inList"] == True:
                add2list += 1
        EVALUATION.insert_one(
            {
                "_id": ObjectId(rec_list_id),
                "max_page": 1,
                "add2list": add2list,
                "context": context,
            }
        )
        """""" """""" """"end""" """""" """""" ""
        return {
            "blocks": render_template(
                "rec_result.json.jinja2",
                context=context,
                rec_list=rec_list[:5],
                rec_list_id=rec_list_id,
                ref_list_id=None,
                page=0,
                PAGE_MAX=PAGE_MAX,
            )
        }


def flip_page_rec(value, time, PAGE_MAX):
    rec_list_id, page = tuple(value.split(","))
    page = int(page)
    try:
        rec_list = RESULTS.find({"_id": ObjectId(rec_list_id)}).next()
        """These codes are for evaluation"""
        log = EVALUATION.find({"_id": ObjectId(rec_list_id)}).next()
        if log["max_page"] < (page + 1):
            add2list = 0
            for paper in rec_list["papers"][(page * 5) : (page * 5 + 5)]:
                if paper["inList"] == True:
                    add2list += 1
            EVALUATION.update_one(
                {"_id": ObjectId(rec_list_id)},
                {
                    "$set": {
                        "max_page": page + 1,
                        "add2list": (log["add2list"] + add2list),
                    }
                },
            )
        """""" """""" """"end""" """""" """""" ""
        return {
            "blocks": render_template(
                "rec_result.json.jinja2",
                context=rec_list["context"],
                rec_list=rec_list["papers"][(page * 5) : (page * 5 + 5)],
                rec_list_id=rec_list["_id"],
                ref_list_id=rec_list["refId"],
                page=page,
                PAGE_MAX=PAGE_MAX,
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
        ref_list = RESULTS.find({"_id": ObjectId(ref_list_id)}).next()
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
        ref_list = RESULTS.find({"_id": ObjectId(ref_list_id)}).next()
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


def add_to_list(value, time, channel_id, PAGE_MAX):
    rec_or_ref_or_kw, ind, page, paper_id, paper_source = tuple(value.split(","))

    # add paper to the marking list
    page = int(page)
    mark = [paper_id + "," + paper_source]
    try:
        MARK_LISTS.insert_one(
            {
                "_id": channel_id,
                "marked": mark,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(days=180),
            }
        )
    except pymongo.errors.DuplicateKeyError:
        mark += MARK_LISTS.find({"_id": channel_id}).next()["marked"]
        MARK_LISTS.update(
            {"_id": channel_id},
            {
                # delete duplicate papers
                "marked": sorted(set(mark), key=mark.index),
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(days=180),
            },
        )

    try:
        rec_or_ref_or_kw_result = RESULTS.find({"_id": ObjectId(ind)}).next()
        for paper in (rec_or_ref_or_kw_result["papers"])[(page * 5) :]:
            if paper["_id"] == paper_id or paper["_id"] == ObjectId(paper_id):
                paper["inList"] = True
                # TODO add bibtex information
                if BIBTEX.find({"_id": paper_id + "," + paper_source}).count() == 0:
                    POOL.submit(generate_bibtex_one, paper, paper_id, paper_source)

        RESULTS.update_one(
            {"_id": ObjectId(ind)},
            {"$set": {"papers": rec_or_ref_or_kw_result["papers"]}},
        )
        if rec_or_ref_or_kw == "rec":
            """These codes are for evaluation"""
            log = EVALUATION.find({"_id": ObjectId(ind)}).next()
            EVALUATION.update_one(
                {"_id": ObjectId(ind)}, {"$set": {"add2list": log["add2list"] + 1}}
            )
            """""" """""" """"end""" """""" """""" ""
            return {
                "blocks": render_template(
                    "rec_result.json.jinja2",
                    context=rec_or_ref_or_kw_result["context"],
                    rec_list=rec_or_ref_or_kw_result["papers"][
                        (page * 5) : (page * 5 + 5)
                    ],
                    rec_list_id=rec_or_ref_or_kw_result["_id"],
                    ref_list_id=rec_or_ref_or_kw_result["refId"],
                    page=page,
                    PAGE_MAX=PAGE_MAX,
                ),
                "updateBlock": "true",
                "ts": time,
            }
        elif rec_or_ref_or_kw == "ref":
            return {
                "blocks": render_template(
                    "ref_result.json.jinja2",
                    context=rec_or_ref_or_kw_result["context"],
                    ref_list=rec_or_ref_or_kw_result["papers"][
                        (page * 5) : (page * 5 + 5)
                    ],
                    ref_list_id=rec_or_ref_or_kw_result["_id"],
                    next_page=True
                    if len(rec_or_ref_or_kw_result["papers"][(page * 5) :]) > 5
                    else False,
                    page=page,
                ),
                "updateBlock": "true",
                "ts": time,
            }
        else:
            return {
                "blocks": render_template(
                    "kw_result.json.jinja2",
                    keywords=rec_or_ref_or_kw_result["keywords"],
                    kw_list=rec_or_ref_or_kw_result["papers"][
                        (page * 5) : (page * 5 + 5)
                    ],
                    kw_list_id=rec_or_ref_or_kw_result["_id"],
                    page=page,
                    PAGE_MAX=PAGE_MAX,
                ),
                "updateBlock": "true",
                "ts": time,
            }
    except StopIteration:
        return {
            "text": 'I have added this paper to the marking list, send "!list" to see the marking list 😉\n However, this message is outdated, so I could not update the message 🥺'
        }


def find_papers_in_list(channel_id):
    try:
        ids_sources = MARK_LISTS.find({"_id": channel_id}).next()["marked"]
    except StopIteration:
        return None, []
    finded_papers = []
    for i in range(len(ids_sources)):
        ids_sources[i] = tuple(ids_sources[i].split(","))
    for i, source in ids_sources:
        if source == "dblp":
            try:
                dic = DBLP.find(
                    {"_id": ObjectId(i)},
                    {
                        "title": 1,
                        "author": 1,
                        "year": 1,
                        "ee": 1,
                        "bib": 1,
                    },
                ).next()
            except StopIteration:
                dic = DBLP.find(
                    {"_id": i},
                    {
                        "title": 1,
                        "author": 1,
                        "year": 1,
                        "ee": 1,
                        "bib": 1,
                    },
                ).next()
            dic["source"] = "dblp"
            finded_papers.append(dic)
        else:
            try:
                dic = AMINER.find(
                    {"_id": i},
                    {
                        "title": 1,
                        "authors.name": 1,
                        "year": 1,
                        "doi": 1,
                        "url": 1,
                        "bib": 1,
                    },
                ).next()
            except StopIteration:
                dic = AMINER.find(
                    {"_id": ObjectId(i)},
                    {
                        "title": 1,
                        "authors.name": 1,
                        "year": 1,
                        "doi": 1,
                        "url": 1,
                        "bib": 1,
                    },
                ).next()
            dic["source"] = "aminer"
            finded_papers.append(dic)
    list_id = ObjectId()
    LIST_TEMP.insert_one(
        {
            "_id": list_id,
            "papers": finded_papers,
            "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=10),
        }
    )
    return list_id, finded_papers


def flip_page_list(value, time, channel_id):
    list_id, page = tuple(value.split(","))
    page = int(page)
    try:
        marked_papers = LIST_TEMP.find({"_id": ObjectId(list_id)}).next()["papers"]
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
        list_id, marked_papers = find_papers_in_list(channel_id)
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


def del_paper_in_list(value, time, channel_id):
    list_id, paper_id, paper_source, page = tuple(value.split(","))
    page = int(page)

    try:
        marked_papers = MARK_LISTS.find({"_id": channel_id}).next()["marked"]
    except StopIteration:
        return {
            "text": "No papers in your marking list (or data expired due to long periods (over 60 days) of inactivity), please add items into the marking list at first 🥺"
        }

    try:
        # delete the papers id in Lists
        marked_papers.remove(paper_id + "," + paper_source)
        MARK_LISTS.update_one({"_id": channel_id}, {"$set": {"marked": marked_papers}})
        # delete from the temp
        marked_papers = LIST_TEMP.find({"_id": ObjectId(list_id)}).next()["papers"]
        for paper in marked_papers:
            if paper["_id"] == paper_id or paper["_id"] == ObjectId(paper_id):
                marked_papers.remove(paper)
                break
        LIST_TEMP.update(
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
    except StopIteration:
        list_id, marked_papers = find_papers_in_list(channel_id)
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
    except ValueError:
        return {"text": 'This message is outdated, please send me "!list" again 🥺'}


def delete_all(channel_id):
    MARK_LISTS.delete_one({"_id": channel_id})
    return {"text": "All the papers in the marking list have been deleted."}


def keywords_search(keywords, channel_id, k, PAGE_MAX):
    aminer_result = list(
        AMINER.find(
            {"$text": {"$search": keywords}},
            {
                "title": 1,
                "authors.name": 1,
                "year": 1,
                "doi": 1,
                "url": 1,
                "bib": 1,
                "source": "aminer",
                "score": {"$meta": "textScore"},
            },
        )
        .sort("score", {"$meta": "textScore"})
        .limit(50)
    )
    dblp_result = list(
        DBLP.find(
            {"$text": {"$search": keywords}},
            {
                "title": 1,
                "author": 1,
                "year": 1,
                "ee": 1,
                "bib": 1,
                "source": "dblp",
                "score": {"$meta": "textScore"},
            },
        )
        .sort("score", {"$meta": "textScore"})
        .limit(50)
    )

    if aminer_result and dblp_result:
        i_aminer = 0
        i_dblp = 0
        kw_list = []
        len_aminer = len(aminer_result)
        len_dblp = len(dblp_result)
        while (i_aminer < len_aminer or i_dblp < len_dblp) and len(kw_list) < k:
            if i_aminer < len_aminer and i_dblp < len_dblp:
                if dblp_result[i_dblp]["score"] >= aminer_result[i_aminer]["score"]:
                    kw_list.append(dblp_result[i_dblp])
                    i_dblp += 1
                else:
                    kw_list.append(aminer_result[i_aminer])
                    i_aminer += 1
            elif i_dblp < len_dblp:
                while i_dblp < len_dblp:
                    kw_list.append(dblp_result[i_dblp])
                    i_dblp += 1
            elif i_aminer < len_aminer:
                while i_aminer < len_aminer:
                    kw_list.append(aminer_result[i_aminer])
                    i_aminer += 1
    elif aminer_result:
        kw_list = aminer_result
    elif dblp_result:
        kw_list = dblp_result
    else:
        kw_list = []

    if kw_list:
        # handle url
        for paper in kw_list:
            if paper["source"] == "aminer":
                if "doi" in paper:
                    if paper["doi"] != "":
                        paper["url"] = "https://doi.org/" + paper["doi"]
                elif "url" in paper:
                    if isinstance(paper["url"], list):
                        for url in paper.get("url"):
                            if url.startswith("http"):
                                if url.startswith("https://dblp"):
                                    continue
                                paper["url"] = url
                                break
                            # no usable url, drop this key-value pairs
                            del paper["url"]
                    elif isinstance(paper["url"], str):
                        if not paper["url"].startswith("http"):
                            del paper["url"]
            else:
                if "ee" in paper:
                    if isinstance(paper["ee"], list):
                        for url in paper.get("ee"):
                            if url.startswith("http"):
                                paper["ee"] = url
                                break
                            # no usable url, drop this key-value pairs
                            del paper["ee"]
                    elif isinstance(paper["ee"], str):
                        if not paper["ee"].startswith("http"):
                            del paper["ee"]

        try:
            marked_papers = MARK_LISTS.find({"_id": channel_id}).next()["marked"]
            for paper in kw_list:
                id_source = str(paper["_id"]) + "," + paper["source"]
                if id_source in marked_papers:
                    paper["inList"] = True
                else:
                    paper["inList"] = False
        except StopIteration:
            for paper in kw_list:
                paper["inList"] = False

        kw_list_id = ObjectId()
        RESULTS.insert_one(
            {
                "_id": kw_list_id,
                "keywords": keywords,
                "papers": kw_list,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            }
        )
        return {
            "blocks": render_template(
                "kw_result.json.jinja2",
                keywords=keywords,
                kw_list=kw_list[:5],
                kw_list_id=kw_list_id,
                page=0,
                PAGE_MAX=PAGE_MAX,
            )
        }
    else:
        return {"text": "No paper has been found."}


def flip_page_kw(value, time, PAGE_MAX):
    kw_list_id, page = tuple(value.split(","))
    page = int(page)
    try:
        kw_list = RESULTS.find({"_id": ObjectId(kw_list_id)}).next()
        return {
            "blocks": render_template(
                "kw_result.json.jinja2",
                keywords=kw_list["keywords"],
                kw_list=kw_list["papers"][(page * 5) : (page * 5 + 5)],
                kw_list_id=kw_list["_id"],
                page=page,
                PAGE_MAX=PAGE_MAX,
            ),
            "updateBlock": "true",
            "ts": time,
        }
    except StopIteration:
        return {
            "text": "This is an outdated message (more than 60 minutes), please send me the keywords again 🥺"
        }


def remove_from_list(value, time, channel_id, PAGE_MAX):
    rec_or_ref_or_kw, ind, page, paper_id, paper_source = tuple(value.split(","))
    page = int(page)
    remove = paper_id + "," + paper_source
    try:
        marked_papers = MARK_LISTS.find({"_id": channel_id}).next()["marked"]
        marked_papers.remove(remove)
        MARK_LISTS.update(
            {"_id": channel_id},
            {
                # delete duplicate papers
                "marked": marked_papers,
                "expireAt": datetime.datetime.utcnow() + datetime.timedelta(days=60),
            },
        )
    except Exception:
        pass

    try:
        rec_or_ref_or_kw_result = RESULTS.find({"_id": ObjectId(ind)}).next()
        for paper in (rec_or_ref_or_kw_result["papers"])[(page * 5) :]:
            if paper["_id"] == paper_id or paper["_id"] == ObjectId(paper_id):
                paper["inList"] = False
        RESULTS.update_one(
            {"_id": ObjectId(ind)},
            {"$set": {"papers": rec_or_ref_or_kw_result["papers"]}},
        )
        if rec_or_ref_or_kw == "rec":
            """These codes are for evaluation"""
            log = EVALUATION.find({"_id": ObjectId(ind)}).next()
            EVALUATION.update_one(
                {"_id": ObjectId(ind)}, {"$set": {"add2list": log["add2list"] - 1}}
            )
            """""" """""" """"end""" """""" """""" ""
            return {
                "blocks": render_template(
                    "rec_result.json.jinja2",
                    context=rec_or_ref_or_kw_result["context"],
                    rec_list=rec_or_ref_or_kw_result["papers"][
                        (page * 5) : (page * 5 + 5)
                    ],
                    rec_list_id=rec_or_ref_or_kw_result["_id"],
                    ref_list_id=rec_or_ref_or_kw_result["refId"],
                    page=page,
                    PAGE_MAX=PAGE_MAX,
                ),
                "updateBlock": "true",
                "ts": time,
            }
        elif rec_or_ref_or_kw == "ref":
            return {
                "blocks": render_template(
                    "ref_result.json.jinja2",
                    context=rec_or_ref_or_kw_result["context"],
                    ref_list=rec_or_ref_or_kw_result["papers"][
                        (page * 5) : (page * 5 + 5)
                    ],
                    ref_list_id=rec_or_ref_or_kw_result["_id"],
                    next_page=True
                    if len(rec_or_ref_or_kw_result["papers"][(page * 5) :]) > 5
                    else False,
                    page=page,
                    PAGE_MAX=PAGE_MAX,
                ),
                "updateBlock": "true",
                "ts": time,
            }
        else:
            return {
                "blocks": render_template(
                    "kw_result.json.jinja2",
                    keywords=rec_or_ref_or_kw_result["keywords"],
                    kw_list=rec_or_ref_or_kw_result["papers"][
                        (page * 5) : (page * 5 + 5)
                    ],
                    kw_list_id=rec_or_ref_or_kw_result["_id"],
                    page=page,
                    PAGE_MAX=PAGE_MAX,
                ),
                "updateBlock": "true",
                "ts": time,
            }
    except StopIteration:
        return {
            "text": 'I have deleted this paper from the marking list, send "!list" to see the marking list 😉\n However, this message is outdated, so I could not update the message 🥺'
        }


def send_feedback_modal(trigger_id, value, channel_id):
    rec_or_ref_or_kw_or_list, ind, page = tuple(value.split(","))
    page = int(page)
    try:
        if rec_or_ref_or_kw_or_list in ["rec", "ref", "kw"]:
            papers = RESULTS.find({"_id": ObjectId(ind)}).next()["papers"][
                (page * 5) : (page * 5 + 5)
            ]
        elif rec_or_ref_or_kw_or_list == "list":
            papers = LIST_TEMP.find({"_id": ObjectId(ind)}).next()["papers"][
                (page * 5) : (page * 5 + 5)
            ]
        return {
            "trigger_id": trigger_id,
            "view": render_template(
                "feedback.json.jinja2", papers=papers, page=page, channel_id=channel_id
            ),
        }
    except StopIteration:
        return {
            "text": "Sorry 🥺 This message is outdated, so I could not handle the feedback."
        }


def handle_feedback(value):
    value = json.loads(value)
    print(value)
    value_dict = value["values"]
    for _, v in value_dict.items():
        for id_source, feedback_dict in v.items():
            if feedback_dict["value"]:
                if id_source == "others":
                    SUGGESTIONS.insert_one(
                        {"_id": ObjectId(), "suggestion": feedback_dict["value"]}
                    )
                else:
                    try:
                        FEEDBACKS.insert_one(
                            {"_id": id_source, "feedback": [feedback_dict["value"]]}
                        )
                    except pymongo.errors.DuplicateKeyError:
                        feedback_list = FEEDBACKS.find({"_id": id_source}).next()[
                            "feedback"
                        ]
                        feedback_list.append(feedback_dict["value"])
                        FEEDBACKS.update_one(
                            {"_id": id_source}, {"$set": {"feedback": feedback_list}}
                        )
    return {"text": "Thanks for you feedback 🥰"}
