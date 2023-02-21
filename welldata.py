from flask import Blueprint, Response, request
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from requests import Session
from rejson import Client as rjClient
from rejson import Path
import pandas as pd
import numpy as np
redis = rjClient(host='wellsite-reddis.ahoqbu.ng.0001.use1.cache.amazonaws.com', port=6379, decode_responses=True, username='default')

welldata = Blueprint('welldata', __name__)

@welldata.route('/welldata/getLatestIndex',methods=['POST'])
def getLatestIndex():
    body = request.get_json()
    try:
        uidWellCustom = body['uidWellCustom']
        res=redis.jsonget(uidWellCustom, ".Hole_Depth")[-1]
        msg={'latestDepth': float(res) }
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    except:
        uidWellCustom = body['partitionId']+'-'+body['uidWellCustom']+'-'+body['uidWellCustom']+'-Depth1-'+'TVD'
        res=redis.jsonget(uidWellCustom)
        l2 = [x.split(",") for x in res]
        df = pd.DataFrame(l2)
        df.columns=['Hole_Depth','b']
        df = df.astype({'Hole_Depth':'float'})
        df.sort_values(by=['Hole_Depth'], inplace=True)
        answer = float(df['Hole_Depth'].iloc[-1])
        msg={'latestDepth': float(answer) }
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    

@welldata.route('/welldata/getLogData',methods=['POST'])
def getLogData():
    body = request.get_json()  
    partitionId = body['partitionId']
    uidWellCustom = body['uidWellCustom']
    startDepth=body.get("startDepth", None)
    endDepth=body.get("endDepth", None) 
    channels = body['datasetMnemonics']
    try:
        keyName = uidWellCustom
        p = ".Hole_Depth"
        holeDepth=redis.jsonget(keyName, p)
        lst = np.asarray(holeDepth)
        print(lst)
        startDepthIndex = (np.abs(lst - startDepth)).argmin()
        endDepthIndex = (np.abs(lst - endDepth)).argmin()+1
        holeDepth = holeDepth[startDepthIndex:endDepthIndex]
        mainLst = [holeDepth]
        channels.remove("Hole_Depth")
        for channel in channels:
            p="."+channel
            #p="."+channel+"["+str(startDepthIndex)+":"+str(endDepthIndex)+"]"
            channel = redis.jsonget(keyName, p)
            mainLst.append(channel[startDepthIndex:endDepthIndex])
            
        channels.insert(0, "Hole_Depth")
        df=pd.DataFrame(mainLst)
        df = df.transpose()
        df.columns = channels
        answer=df.to_dict('list')
        #print(answer)
        msg={'data': answer}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    except:
        keyName = []
        data_nov = []
        for val in channels:
            keyName.append(partitionId+'-'+uidWellCustom+'-'+uidWellCustom+'-'+'Depth1'+'-'+val)
        count = 0
        for k,i in enumerate(channels):
            if count == 0:
                # print('1 baar aaya')
                temp_data = (redis.jsonget(keyName[k]))
                print('temp_data',temp_data)
                try:
                    res = [x.split(",") for x in temp_data]
                    df = pd.DataFrame(res)
                    df.columns = ['Hole_Depth',i]
                    count+=1
                except:
                    pass
            else:
                # print('else m aaya')
                temp_data = (redis.jsonget(keyName[k]))
                try:
                    res = [x.split(",") for x in temp_data]
                    df_temp = pd.DataFrame(res)
                    del df_temp[df_temp.columns[0]]
                    df_temp.columns=[i]
                    df = df.join(df_temp)
                except:
                    pass
        df = df.astype(float)
        df = df.loc[(df['Hole_Depth'] >= float(startDepth)) & (df['Hole_Depth'] <= float(endDepth))]
        df = df.fillna(-9999.9)
        df.sort_values(by=['Hole_Depth'], inplace=True)
        df.drop_duplicates(subset=['Hole_Depth'],keep='first',inplace=True)
        answer=df.to_dict('list')
        msg={'data': answer}
        return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    else:
        return Response(response=json.dumps({'error': 'No data found'}), status=200, mimetype='application/json')