from flask import Blueprint, Response, request
import json
import requests

test = Blueprint('test', __name__)


@test.route('/test/connectiontest',methods=['POST'])
def testconnection():
    data=requests.get('http://worldtimeapi.org/api/timezone/America/New_York')
    return Response(data.text, status=200, mimetype='application/json')