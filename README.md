# Citation-Recommendation-Bot

A slack chatbot that can recommend citation.

## Traning

### Build docker image

Enter the directory `training` and build the docker image using the following command:

```bash
 docker-compose -p citrec up -d
```

Here we highly recommend not to change the name of the docker compose, because the network in the compose was set as default.

### Import dataset

#### AMiner dateset

[Download the AMiner dataset](https://www.aminer.org/citation) (current version: v13) at first, here you should note that the `json` file was build as `JsonArray`, but missing a `]` at the end. To add it, run in the terminal:

```bash
echo "]" >> dblpv13.json
```

Now move the Json file to `citrec_mongodb` container using shell command (the name of container might change):

```bash
docker cp <path>/dblpv13.json citrec_mongodb:/dblpv13.json
```

Then import the json data to the mongdb with database name `CitRec`and collection name`AMiner`.
To import, please use following shell command in `citrec_mongodb` container:

```bash
mongoimport --db CitRec --collection AMiner --jsonArray --file <path>/dblpv13.json
```

#### DBLP dataset

[Download the DBLP datset](https://dblp.org/xml/) ([dblp.dtd](https://dblp.org/xml/dblp.dtd) and [dblp.xml.gz](https://dblp.org/xml/dblp.xml.gz)), move them to the `citrec_training` container using commands:

```bash
docker cp <path>/dblp.dtd citrec_training:/workspace/dblp.dtd
```

```bash
citrec_trainingdocker cp <path>/dblp.xml citrec_mongodb:/workspace/dblp.xml
```

#### Citavi dataset

Export the citavi project as `.ctv6`. Change the filename extension to`zip` and unzip it. Now move the `.db` (SQLite) file to the `citrec_training` container.

### Start training

Start the training process using `citrec_training` container:

```bash
python3 __init__.py --year_AMiner <year in which AMIner dataset was publised (e.g. 2021)> --dblp_dtd <path to .dtd> --dblp_xml <path to .xml> --citavi_sqlite <path to .db>
```

Now the training process begins and might last tens of hours.

## Application

### Build docker image

Enter the directory `training` and build the docker image using the following command:

```bash
 docker-compose -p citrec up -d
```

Note: do not to change the name of the docker compose, because the network in the compose was set as default.

Now you can find papers for you input context on the website `localhost:5000/rec/<context>`
