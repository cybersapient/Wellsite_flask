from flask import Blueprint, Response, request
import json
from dotenv import load_dotenv
import uuid 
from requests.auth import HTTPBasicAuth
from requests import Session
import pymongo
import os
from bson.objectid import ObjectId

dashboard = Blueprint('dashboard', __name__)
load_dotenv()
client = pymongo.MongoClient(os.getenv('MONGO_CONNECTION_STRING'))
db = client.test

@dashboard.route('/dashboard/getAllDashboard',methods=['POST'])
def getalldashboard():
    body = request.get_json()
    coll=db.dashboard
    userId = body['userId']
    doc = list(coll.find( {"userId":userId}) )
    if len(doc) == 0:
        msg = {'message': 'No templates added'}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')     
    elif len(doc) != 0:
        lst_templates = []
        for rec in doc:
            lst_templates.append({"templateId": str(rec['_id']), "templateName": rec['templateName'],"userId":rec['userId'],"templateIcon":rec['templateIcon']})
        return Response(response=json.dumps(lst_templates), status=200, mimetype='application/json')
    else:
        msg = {'message': 'Unknown error'}
        return Response(response=json.dumps(msg), status=500, mimetype='application/json')

@dashboard.route('/dashboard/saveDashboard',methods=['POST'])
def savedashboard():
    body = request.get_json()
    coll = db.dashboard
    templateName = body['templateName']
    userId = body['userId']
    doc = list(coll.find( {"userId":userId, "templateName": templateName} ))
    if len(doc) == 0:
        resp_ins =coll.insert_one(body)
        templateId = resp_ins.inserted_id
        msg = {'message': 'Template saved', 'templateId': str(templateId)}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    elif len(doc) != 0:
        resp = {'message': 'Template already exists'}
        return Response(response=json.dumps(resp), status=200, mimetype='application/json')
    else:
        resp = {'message': 'Unknown error'}
        return Response(response=json.dumps(resp), status=200, mimetype='application/json')

@dashboard.route('/dashboard/getDashboard',methods=['POST'])
def getdashboard():
    body = request.get_json()
    coll = db.dashboard
    templateId = body['templateId']
    doc = list(coll.find({"_id":ObjectId(templateId)}))
    if len(doc)==0:
        resp={'message': "No template Found"}
        return Response(response=json.dumps(resp), status=200, mimetype='application/json')
    elif len(doc) !=0:
        doc[0]['templateId'] = str(doc[0]['_id'])
        del doc[0]['_id']
        resp={'message': "Template Found", 'body': doc[0]}
        return Response(response=json.dumps(resp), status=200, mimetype='application/json')
    else:
        resp={'message':"Unknown error"}
        return Response(response=json.dumps(resp), status=200, mimetype='application/json')
    
@dashboard.route('/dashboard/updateDashboard',methods=['POST'])
def updatedashboard():
    body = request.get_json()
    coll = db.dashboard
    templateId = body['templateId']
    userId = body['userId']
    try:
        doc = coll.find_one({"_id":ObjectId(templateId),"userId":userId})
        print(doc)
        graphLayout=body['graphLayout']
        graphSettings=body['graphSettings']
        templateName=body['templateName']
        templateIcon=body['templateIcon']
        newvalues = { "$set": { 'templateName': templateName,'templateIcon':templateIcon,'graphSettings':graphSettings,"graphLayout":graphLayout} }
        try:
            coll.update_one({"_id":ObjectId(templateId)},newvalues)
        except:
            resp = {'message': 'Unable to update template'}
            return Response(response=json.dumps(resp), status=200, mimetype='application/json')
        else:
            resp = {'message': 'Template updated', 'templateId': templateId}
            return Response(response=json.dumps(resp), status=200, mimetype='application/json')
    except:
        resp = {'message': 'Template not found', 'templateId': templateId}
        return Response(response=json.dumps(resp), status=200, mimetype='application/json')
    
@dashboard.route('/dashboard/deleteDashboard',methods=['POST'])
def deletedashboard():
    body = request.get_json()
    coll = db.dashboard
    templateId = body['templateId']
    userId = body['userId']
    try:
        doc = coll.find_one({"_id":ObjectId(templateId),"userId":userId})
        print(doc)
        try:
            coll.delete_one({"_id":ObjectId(templateId)})
        except:
            resp = {'message': 'Unable to delete template'}
            return Response(response=json.dumps(resp), status=200, mimetype='application/json')
        else:
            resp = {'message': 'Template deleted', 'templateId': templateId}
            return Response(response=json.dumps(resp), status=200, mimetype='application/json')
    except:
        resp = {'message': 'Template not found', 'templateId': templateId}
        return Response(response=json.dumps(resp), status=200, mimetype='application/json')