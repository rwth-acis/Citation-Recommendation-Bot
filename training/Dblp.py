from lxml import etree
import pymongo


def elem2dict(node):
    """
    Convert an lxml.etree node tree into a dict.
    """
    result = {}
    result["type"] = node.tag

    for element in node.iterchildren():
        # Remove namespace prefix
        key = element.tag.split("}")[1] if "}" in element.tag else element.tag

        # Process element as tree element if the inner XML contains non-whitespace content
        if element.text and element.text.strip():
            value = element.text
        else:
            value = elem2dict(element)
        if key in result:
            if type(result[key]) is list:
                result[key].append(value)
            else:
                tempvalue = result[key]
                result[key] = [tempvalue, value]
        else:
            result[key] = value
    return result


def filter_year(path_dtd, path_xml, mongodb_collection):
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
    for event, elem in etree.iterparse(path_xml, load_dtd=True):
        if event == "end" and elem.tag in dblp_record_types_for_publications:
            for year in elem.findall("year"):
                if int(year.text) >= 2021:
                    mongodb_collection.insert_one(elem2dict(elem))


if __name__ == "__main__":
    path_dtd = "/home/pl908030/Codes/Citation-Recommendation-Bot/database/dblp.dtd"
    path_xml = "database/dblp.xml"
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["CitRec"]
    mongodb_collection = db["DBLP"]
    filter_year(path_dtd, path_xml, mongodb_collection)
