from lxml import etree
import pymongo


def filter_year_dblp2json(path_dtd, path_xml, year_AMiner, dblp_mongodb):
    """Filter the DBLP items that are published after "this_year", and store them in "dblp_mongodb".

    Args:
        path_dtd (String): path to .dtd.
        path_xml (String): path to .xml.
        year_AMiner (Int): year that AMiner dataset published.
        dblp_mongodb (MongoDB collection): MongoDB collection that stores the result.
    """
    etree.DTD(file=path_dtd)
    dblp_record_types_for_publications = (
        "article",
        "inproceedings",
        "proceedings",
        "book",
        "incollection",
        "phdthesis",
        "masterthesis",
        "www",
    )
    for event, node in etree.iterparse(path_xml, load_dtd=True):
        if event == "end" and node.tag in dblp_record_types_for_publications:
            for year in node.findall("year"):
                if int(year.text) >= year_AMiner:
                    dic = {}
                    dic["type"] = node.tag
                    for element in node.iterchildren():
                        key = element.tag
                        value = "".join(element.itertext())
                        if key in dic:
                            if type(dic[key]) is list:
                                dic[key].append(value)
                            else:
                                tempvalue = dic[key]
                                dic[key] = [tempvalue, value]
                        else:
                            dic[key] = value
                    dblp_mongodb.insert_one(dic)


if __name__ == "__main__":
    path_dtd = "/home/pl908030/Codes/Citation-Recommendation-Bot/database/dblp.dtd"
    path_xml = "database/dblp.xml"
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["CitRec"]
    dblp_mongodb = db["DBLP"]
    this_year = 2021
    filter_year_dblp2json(path_dtd, path_xml, this_year, dblp_mongodb)
