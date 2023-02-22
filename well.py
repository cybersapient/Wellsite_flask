from flask import Blueprint, Response, request
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from requests import Session
from zeep import Client
from zeep.transports import Transport
import xmltodict
import pymongo
import os

well = Blueprint('well', __name__)
load_dotenv()
client = pymongo.MongoClient(os.getenv('MONGO_CONNECTION_STRING'))
db = client.test

@well.route('/well/getlivewells',methods=['POST'])
def wells():
    load_dotenv()
    body = request.get_json()
    username = body['username']
    password = body['password']
    connectionURL = body['url']
    
    try:
        session = Session()
        session.auth = HTTPBasicAuth(username, password)
        client = Client(connectionURL, transport=Transport(session=session))
    except: 
        msg={'body': {"message": "Client Error Unauthorized for url"}} 
        return Response(response=json.dumps(msg), status=401, mimetype='application/json')
    else: 
        q = '<wells xmlns="http://www.witsml.org/schemas/131" version="1.3.1.1"><well uid=""><name></name></well></wells>'
        result = client.service.WMLS_GetFromStore(WMLtypeIn = 'well', QueryIn = q, OptionsIn='', CapabilitiesIn='')
        data_dict = xmltodict.parse(result['XMLout'])
        msg={'wells': data_dict['wells']['well']}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    
@well.route('/well/getwells',methods=['POST'])
def getwells():
    coll = db.wellsforuv
    doc = list(coll.find())
    if len(doc)==0:
        msg={'body': {"message": "No wells found"}}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        returnList=[]
        for i in doc:
            del i['_id']
            returnList.append(i)
        msg={'body': returnList[::-1]}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    
@well.route('/well/addwell',methods=['POST'])
def addwell():
    body = request.get_json()
    coll = db.wellsforuv
    uidWell = body.get("uidWell", None)
    nameWell = body.get("nameWell", None)
    datasetName=body.get("datasetName", None)
    status=body.get("status", None)
    body['status']=status
    body['datasetName']=datasetName
    body['dataset'] = nameWell.replace(" ","_")+"_depth1"
    q = {"uidWell": uidWell}
    doc = list(coll.find(q))
    if len(doc)==0:
        try:
            resp = coll.insert_one(body)
        except:
            msg={'body': {"message": "Unknown error"}}
            return Response(response=json.dumps(msg), status=200, mimetype='application/json')
        else:
            msg={'body': {"message": "Well added successfully"}}
            return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        msg={'body': {"message": "Well already saved for the customer"}}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    
@well.route('/well/deletewell',methods=['POST'])
def deletewell():
    body = request.get_json()
    coll = db.wellsforuv
    uidWell = body.get("uidWell", None)
    q = {"uidWell": uidWell}
    doc = list(coll.find(q))
    if len(doc)==0:
        msg={'body': {"message": "Well not found"}}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        try:
            rec = coll.delete_one(q)
        except:
            msg={'body': {"message": "Unknown error"}}
            return Response(response=json.dumps(msg), status=200, mimetype='application/json')
        msg={'body': {"message": "Well deleted successfully"}}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')

@well.route('/well/updatewellstatus',methods=['POST'])
def updatewellstatus():
    body = request.get_json()
    coll = db.wellsforuv
    uidWell = body.get("uidWell", None)
    status = body.get("status", None)
    q = {"uidWell": uidWell}
    doc = list(coll.find(q))
    if len(doc)==0:
        msg={'body': {"message": "Well not found"}}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        coll.update_one(q, {"$set": {"status":status}})
        msg={'body': {"message": "Well status updated successfully"}}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')

