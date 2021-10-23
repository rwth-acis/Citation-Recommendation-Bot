# Citation-Recommendation-Bot

A slack chatbot that can recommend citation.

As this bot needs tens of GBs RAM for computing, we only recommended to running it in a cluster.

## Traning

### Datasets

You need a MongoDB database service to manage the datasets.

#### AMiner dateset

[Download the AMiner dataset](https://www.aminer.org/citation) (current version: v13) at first, here you should note that the `json` file was build as `JsonArray`.

Then import the json data to the mongdb with database name `CitRec`and collection name`AMiner`.
To import, please use following shell command in `citrec_mongodb` container:

```bash
mongoimport --db CitRec --collection AMiner --jsonArray --legacy --file <path>/dblpv13.json
```

#### DBLP dataset

[Download the DBLP datset](https://dblp.org/xml/) ([dblp.dtd](https://dblp.org/xml/dblp.dtd) and [dblp.xml.gz](https://dblp.org/xml/dblp.xml.gz)).

#### Citavi dataset

Export the citavi project as `.ctv6`. Change the filename extension to`zip` and unzip it, then the `.db` (SQLite) is what we need. 

### Start training

1. Enter the *training* directory.

2. In a Python in environment, using the following command to install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the training process using the following command:

   ```bash
   python3 __init__.py --year_AMiner <year in which AMIner dataset was publised (e.g. 2021)> --dblp_dtd <path to .dtd> --dblp_xml <path to .xml> --citavi_sqlite <path to .db> --server_address <server address of MongoDB, e.g. localhost:27017> --batch_size_1 <defaut as 16> --batch_size_2 <default as 100000>
   ```

   Now the training process begins and might last tens of hours.

   If it run out of the GPU's memory, decrease the number filled in batch_size_1. If it run out of CPU's memory, decrease the number filled in batch_size_2

## Application

### Requirement

- [las2peer-social-bot-manager-service](https://github.com/rwth-acis/las2peer-social-bot-manager-service) and [las2peer-CitRec-Handler-Service](https://github.com/rwth-acis/las2peer-CitRec-Handler-Service) need to work with this bot together.

  To check if they are working, visit the following addresses:

  - `localhost:8080/SBFManager/swagger.json`
  - `localhost:8080/CitRecHandler/swagger.json`

- A rasa-nlu server is needed. Install the rasa package in a Python environment with command:

  ```bash
  conda install rasa
  ```

  Start rasa server using the command:

  ```bash
  rasa run --enable-api
  ```

  Now, the rasa can be visited using address `localhost:5005`

### Creating a Slack app

Creating a classic bot app is possible [here](https://api.slack.com/apps?new_classic_app=1). (Wait for the app creation window to pop up, do not click on the green "Create New App" button). Since the las2peersocial-bot-manager-service uses RTM, a classic app, instead of a new app, is needed. 

1. Inside the app settings, create a bot user (on the left side Features: App Home, and then "Add Legacy Bot User")
3. Add the following oauth scopes under OAuth & Permissons:
   - channels:read
   - chat:write:bot
   - bot
   - users:read.email (users:read included)
   - Please do not update scopes!

Now install the app to your workspace. After this a token will be generated which is used in the redirect url.

1. Find the bot token: On the left side: OAuth and Permissons, the bot user oauth token (starting with xoxb).

2. Activate interactive components (on the left side: Basic Information: Add features and functionality, Interactive Components. After activating this feature, a Request URL is needed.)

3. Configuring the request url:

   The ip address and port where slack posts the request (the address from the sbfmanager), slack app token, the bot name from the frontend, the instance name from the frontend and the buttonintent text are needed. 

   ```url
   http://<ipAddress:port>/SBFManager/bots/<botName>/appRequestURL/<instanceName>/buttonIntent/<token>
   ```

   For the model provided in this repository (directory [bot_model](https://github.com/rwth-acis/Citation-Recommendation-Bot/tree/main/bot_model)), set the url to 

   ```url
   http://<ipAddress:port>/SBFManager/bots/CitBot/appRequestURL/Group1/buttonIntent/<instanceName>/buttonIntent/<token>
   ```

### Bot modelling

Model the bot using this url:

```url
https://sbf.tech4comp.dbis.rwth-aachen.de/bot-modeling
```

In the website:

1. Select a JSON file: select [model.json](https://github.com/rwth-acis/Citation-Recommendation-Bot/blob/main/bot_model/model.json)
2. Import/Export/Delete a (Meta- or Guidance-)Model: click the "Import" button
3. In the *Social bot manager endpoint:* fill with `http://localhost:8080/SBFManager`
4. In the *Instance* metamodel: fill the address with `http://localhost:8080`
5. In the *NLU Knowledge* metamodel: fill the address with `http://localhost:5005`
6. In the *Bot* metamodel: fill the name with `CitBot`
7. Click *Submit* button, now the bot can response on messages.

### Start the CitBot Web Service

1. Enter the *citbot* directory.

2. In a Python in environment, using the following command to install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the service using the following command:

   ```bash
   python3 -m flask run --host=0.0.0.0
   ```

   Now the service is running at `http://localhost:5000`.

   And all the functionalities of the bot are available. 
