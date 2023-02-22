from flask import Blueprint, Response, request
import json
from dotenv import load_dotenv
import pymongo
from datetime import datetime
import os

user = Blueprint('user', __name__)
load_dotenv()
client = pymongo.MongoClient(os.getenv('MONGO_CONNECTION_STRING'))
db = client.test

@user.route('/user',methods=['GET'])
def usergreeter():
    return "Hello"

@user.route('/user/userRegistration',methods=['POST'])
def userRegistration():
    coll = db.uvusers
    body = request.get_json()
    userId = body.get('userId', None)
    role = body.get('role', 'normal')
    name=body.get('name', "User")
    company=body.get('company', "Default")
    body['role'] = role
    body['name'] = name
    body['company'] = company

    doc = list(coll.find({'userId': userId}))
    if len(doc) == 0:
        coll.insert_one(body)
        msg={'message': "User registered"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        msg= {'message': "User exists"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')

@user.route('/user/getUser',methods=['POST'])
def getUser():
    coll = db.uvusers
    body = request.get_json()
    userId = body.get("userId", "null")
    coll = db.uvusers
    doc = list(coll.find({'userId': userId}))

    if len(doc) == 0:
        msg={'message': "User not found"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        del doc[0]['_id']
        msg={'body': doc[0]}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')

@user.route('/user/getUserList',methods=['POST'])
def getUserList():
    coll = db.uvusers
    doc = list(coll.find())
    if len(doc) == 0:
        msg={'message': "No users found"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        bigList = []
        for user in range(len(doc)):
            del doc[user]['_id']
            bigList.append(doc[user])
        msg = {'body': {'userList': bigList}}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')

@user.route('/user/updateUser',methods=['POST'])
def updateUser():
    coll = db.uvusers
    body = request.get_json()
    userId = body.get("userId", "null")
    q = { "userId": userId}
    doc = list(coll.find(q))
    if len(doc)==0:
        msg={'message': "User not found"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    elif len(doc)>1:
        msg={'message': "Duplication error"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        username = body.get("username", "null")
        email = body.get("email", "null")
        company = body.get("company", "null")
        country = body.get("country", "null")
        phone = body.get("phone", "null")
        profilePicture = body.get("profilePicture", "null")
        
        try:
            coll.update_one(q, {"$set": {"username":username, "email":email, "company":company, "country":country, "phone":phone, "profilePicture":profilePicture} } )
            pass
        except:
            msg={'message': "Error"}
            return Response(response=json.dumps(msg), status=200, mimetype='application/json')
        else:
            msg={'message': "User updated"}
            return Response(response=json.dumps(msg), status=200, mimetype='application/json')
        

@user.route('/user/userVerification',methods=['POST'])
def userVerification():
    body = request.get_json()
    userId = body.get('userId', None)
    adminAction=body.get('adminAction', 'pending')
    coll = db.uvusers
    q = { "userId": userId}
    doc = list(coll.find(q))
    if len(doc)==0:
        msg={'message': "User not found"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    elif len(doc)>1:
        msg={'message': "Duplication error"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        try:
            coll.update_one(q, {"$set": {"adminAction":adminAction}} )
        except:
            msg={'message': "Error"}
            return Response(response=json.dumps(msg), status=200, mimetype='application/json')
        msg={'message': "User verification status updated"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')  

@user.route('/user/adminVerifyStatus',methods=['POST'])
def adminVerifyStatus():
    body = request.get_json()
    userId = body.get('userId', None)
    coll = db.uvusers
    q = { "userId": userId}
    doc = list(coll.find(q))
    if len(doc)==0:
        msg={'message': "User not found"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    elif len(doc)>1:
        msg={'message': "Duplication error"}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        msg={'data': {"adminVerified":doc[0]['adminAction']}}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
