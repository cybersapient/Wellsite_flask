from flask import Blueprint, Response, request
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from requests import Session
from rejson import Client as rjClient
from rejson import Path
import pandas as pd
import numpy as np
import pymongo
import os
import math
from datetime import datetime

redis = rjClient(host='wellsite-reddis.ahoqbu.ng.0001.use1.cache.amazonaws.com', port=6379, decode_responses=True, username='default')
load_dotenv()
client = pymongo.MongoClient(os.getenv('MONGO_CONNECTION_STRING'))
db = client.test
welldata = Blueprint('welldata', __name__)

@welldata.route('/welldata/getLatestIndex',methods=['POST'])
def getLatestIndex():
    body = request.get_json()
    try:
        try:
            uidWellCustom = body['uidWellCustom']
            res=redis.jsonget(uidWellCustom, ".Hole_Depth")[-1]
            msg={'latestDepth': float(res) }
            return Response(response=json.dumps(msg), status=200, mimetype='application/json')
        except:
            uidWellCustom = body['uidWellCustom']+'-'+body['uidWellCustom']+'-Depth1-'+'TVD'
            res=redis.jsonget(uidWellCustom)
            l2 = [x.split(",") for x in res]
            df = pd.DataFrame(l2)
            df.columns=['Hole_Depth','b']
            df = df.astype({'Hole_Depth':'float'})
            df.sort_values(by=['Hole_Depth'], inplace=True)
            answer = float(df['Hole_Depth'].iloc[-1])
            msg={'latestDepth': float(answer) }
            return Response(response=json.dumps(msg), status=200, mimetype='application/json')
    except:
        msg={'message': 'No existing data'}
        return Response(response=json.dumps(msg), status=500, mimetype='application/json')
    

@welldata.route('/welldata/getLogData',methods=['POST'])
def getLogData():
    body = request.get_json()  
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
            keyName.append(uidWellCustom+'-'+uidWellCustom+'-'+'Depth1'+'-'+val)
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
    
@welldata.route('/welldata/getLogChannels',methods=['POST'])
def getLogChannels():
    coll = db.mnemonics
    doc = list(coll.find())
    lst_mnemonic = []
    try:
        for val in doc:
            lst_mnemonic.append({"key": val['key'], "displayName": val['displayName'],"unit":val['unit'],"dataType":val['dataType'],"isTemporal":val['isTemporal']})
        sorted_mnemonic = sorted(lst_mnemonic, key=lambda d: d['key']) 
        return Response(response=json.dumps(sorted_mnemonic), status=200, mimetype='application/json')
    except:
        return Response(response=json.dumps({'error': 'No data found'}), status=200, mimetype='application/json')
    
@welldata.route('/welldata/getDipAngle',methods=['POST'])
def getDipAngle():
    body = request.get_json()
    coll = db.dipanglehistory
    customWellId = body.get("customWellId", None)
    depth = body.get("depth", None)
    q = {"customWellId": customWellId}
    doc = list(coll.find(q))
    if len(doc)==0:
        return Response(response=json.dumps({"message": "No dip history"}), status=400, mimetype='application/json') 
    stations = doc[0]['stations']
    for station in stations:
        if depth >= station['startDepth'] and depth <= station['endDepth']:
            ans = { 'stationId': station['stationId'], 'dipAngle': station['angle'], 'startDepth':station['startDepth'],
            'endDepth':station['endDepth'], 'topWindow': station['topWindow'], 'bottomWindow': station['bottomWindow'] }
            return Response(response=json.dumps(ans), status=200, mimetype='application/json')
    
    return {
        'statusCode': 400,
        'body': json.dumps({"message": "Dip angle not found for the depth: "+str(depth)})
        }

@welldata.route('/welldata/saveDipAngle',methods=['POST'])
def saveDipAngle():
    body = request.get_json()
    coll = db.dipanglehistory
    customWellId = body.get("customWellId", "null")
    startDepthNew = body.get("startDepth", "null")
    endDepthNew = body.get("endDepth", "null")
    createdDate = body.get("createdDate", "null")
    userId = body.get("userId", "null")
    
    angle=body['angle']
    if angle==0:
        return Response(response=json.dumps({"message": "Angle cannot be 0"}), status=400, mimetype='application/json')
    q = {"customWellId": customWellId}
    doc = list(coll.find(q))
    if len(doc)>1:
        return Response(response=json.dumps({"message": "More than one set of data saved for this custom well"}), status=400, mimetype='application/json')
    elif len(doc)==0:
        try:
            # --------- dip angle for each depth ---------------
            depthRange = list(np.around(np.arange(startDepthNew, endDepthNew+0.1, 0.1),1))
            depth_length = len(depthRange)
            slope = math.tan(math.radians(90-angle))
            deltaX = endDepthNew - startDepthNew
            slope_X_deltaX = deltaX*slope
            
            def findEndY(windowValue):
                windowEndY = windowValue + slope_X_deltaX
                deltaY = abs(windowEndY-windowValue)
                increment = deltaY / depth_length
                if windowEndY < windowValue: increment = -increment
                windowRange = list(np.around(np.arange(windowValue, windowEndY, increment),4))
                return windowRange
            
            stationId = "".join([char for char in str(datetime.now()) if char.isalnum()])
            stations = [{"startDepth":startDepthNew, "endDepth": endDepthNew, "angle":angle, "stationId":stationId,
                        "topWindow": body['topWindow'], "bottomWindow": body['bottomWindow'], "createdDate": createdDate,
            "CreatedUserId": userId}]
            save_df_data = {}
            save_df_data['customWellId'] = customWellId
            save_df_data['stations'] = stations
            save_df_data['depthRange'] = depthRange
            if angle==90:
                save_df_data['topWindowRange'] = [ body['topWindow'] ] *depth_length
                save_df_data['bottomWindowRange'] = [ body['bottomWindow'] ] *depth_length
            else:
                save_df_data['topWindowRange'] = findEndY(body['topWindow'])
                save_df_data['bottomWindowRange'] = findEndY(body['bottomWindow'])
            rec = coll.insert_one(save_df_data)
        except Exception as e:
            return Response(response=json.dumps({"message": "Error in saving dip angle: "+str(e)}), status=400, mimetype='application/json')
        else:
            try:
                coll = db.auditlog
                timestamp = str(datetime.now())
                d_tmp ={"angle": angle, "startDepth": startDepthNew, "endDepth": endDepthNew,
                            "topWindow": body['topWindow'], "bottomWindow": body['bottomWindow']}
                for key, value in d_tmp.items():
                    q={"TIMESTAMP": timestamp, "ENTITY": "dip", "ENTITY_ID":stationId , "ACTION": "add", "FIELD": "profile."+key,
                        "VALUE_OLD": "null", "VALUE_NEW": value}
                    coll.insert_one(q)
            except: pass
            else: pass

            return Response(response=json.dumps({"message": "Dip angle saved successfully"}), status=200, mimetype='application/json')
    old_df = doc[0]
    stations = old_df['stations']
    for station in stations:
        rangeOld =  np.around(np.arange(station['startDepth'], station['endDepth']+0.1, 0.1),1)
        rangeNew = np.around(np.arange(startDepthNew, endDepthNew+0.1, 0.1),1)
        rangeNewSet = set(rangeNew)
        print(len(rangeNewSet.intersection(rangeOld)))
        if len(rangeNewSet.intersection(rangeOld))!=0:
            return {
                'statusCode': 400,
                'body': "Overlap conflict"
                }
    try:
        # --------- dip angle for each depth ---------------
        depthRange = list(np.around(np.arange(startDepthNew, endDepthNew+0.1, 0.1),1))
        depth_length = len(depthRange)
        slope = math.tan(math.radians(90-body['angle']))
        deltaX = endDepthNew - startDepthNew
        slope_X_deltaX = deltaX*slope
        
        def findEndY(windowValue):
            windowEndY = windowValue + slope_X_deltaX
            deltaY = abs(windowEndY-windowValue)
            increment = deltaY / depth_length
            if windowEndY < windowValue: increment = -increment
            windowRange = list(np.around(np.arange(windowValue, windowEndY, increment),4))
            return windowRange
            
        lenArrOld=len(doc[0]['depthRange'])    
        old_df_data = { "depthRange": doc[0]['depthRange'], "topWindowRange": doc[0]['topWindowRange'][:lenArrOld],
                        "bottomWindowRange": doc[0]['bottomWindowRange'][:lenArrOld] }
        old_df = pd.DataFrame(old_df_data)
        if angle==90:
            topWindowRange = [ body['topWindow'] ] *depth_length
            bottomWindowRange = [ body['bottomWindow'] ] *depth_length
        else:
            topWindowRange = findEndY(body['topWindow'])
            bottomWindowRange = findEndY(body['bottomWindow'])
        lenArr=len(depthRange)
        
        new_df_data = { "depthRange": depthRange, "topWindowRange": topWindowRange[:lenArr],
                        "bottomWindowRange": bottomWindowRange[:lenArr] }
        
        new_df = pd.DataFrame(new_df_data)
        df_to_store = pd.concat([old_df, new_df], ignore_index = True)
        
        df_to_store = df_to_store.sort_values(by = 'depthRange')
        
        dict_to_store = df_to_store.to_dict('list')
        
        stations = doc[0]['stations']
        stationId = "".join([char for char in str(datetime.now()) if char.isalnum()])
        stationNew = {"startDepth":startDepthNew, "endDepth": endDepthNew, "angle":angle, "stationId":stationId,
                        "topWindow": body['topWindow'], "bottomWindow": body['bottomWindow'], "createdDate": createdDate,
            "CreatedUserId": userId}
        stations.append(stationNew)
        
        save_df_data = {}
        save_df_data['customWellId'] = customWellId
        save_df_data['stations'] = stations
        save_df_data['depthRange'] = dict_to_store['depthRange']
        save_df_data['topWindowRange'] = dict_to_store['topWindowRange']
        save_df_data['bottomWindowRange'] = dict_to_store['bottomWindowRange']
        coll.delete_one(q)
        rec = coll.insert_one(save_df_data)
    except Exception as e:
        return Response(response=json.dumps({"message": "Error in saving dip angle: "+str(e)}), status=400, mimetype='application/json')
    else:
        try:
            coll = db.auditlog
            timestamp = str(datetime.now())
            d_tmp ={"angle": angle, "startDepth": startDepthNew, "endDepth": endDepthNew,
                        "topWindow": body['topWindow'], "bottomWindow": body['bottomWindow']}
            for key, value in d_tmp.items():
                q={"TIMESTAMP": timestamp, "ENTITY": "dip", "ENTITY_ID":stationId , "ACTION": "add", "FIELD": "profile."+key,
                    "VALUE_OLD": "null", "VALUE_NEW": value}
                coll.insert_one(q)
        except: pass
        else: pass
        return Response(response=json.dumps({"message": "Dip angle saved successfully"}), status=200, mimetype='application/json')

@welldata.route('/welldata/modifyDipAngle', methods=['POST'])
def modifyDipAngle():
    body = request.get_json()
    coll = db.dipanglehistory
    customWellId = body.get("customWellId", None)
    startDepthNew = body.get("startDepth", None)
    endDepthNew = body.get("endDepth", None)
    userId = body.get("userId", None)
    updatedDate = body.get("updatedDate", None)
    
    angle = body.get("angle", None)
    stationId = body.get("stationId", None)
    
    if angle==0:
        return {
            'statusCode': 400,
            'body': "Angle cannot be 0"
            }
            
    q = {"customWellId": customWellId}
    doc = list(coll.find(q))
    old_df = doc[0]
    stations = old_df['stations']
    for station in stations:
        if station['stationId'] != stationId:
            rangeOld =  np.around(np.arange(station['startDepth'], station['endDepth']+0.1, 0.1),1)
            rangeNew = np.around(np.arange(startDepthNew, endDepthNew+0.1, 0.1),1)
            rangeNewSet = set(rangeNew)
            if len(rangeNewSet.intersection(rangeOld))!=0:
                return Response(response=json.dumps({"message": "Dip angle cannot be modified as it overlaps with another dip angle"}), status=400, mimetype='application/json')
    try:
        data = doc[0]
        data_stations = data["stations"]
        str_d = -1
        for station in data_stations:
            if station['stationId']==stationId:
                str_d=station['startDepth']
                stp_d=station['endDepth']
                data_stations.remove(station)
                break
        if str_d == -1:
            return Response(response=json.dumps({"message": "Station not found"}), status=400, mimetype='application/json')
        del data["_id"]
        data["stations"] = data_stations
        str_d_ind=data["depthRange"].index(str_d)
        stp_d_ind=data["depthRange"].index(stp_d)
        
        try:
            del data["depthRange"][str_d_ind:stp_d_ind+1]
            del data["topWindowRange"][str_d_ind:stp_d_ind+1]
            del data["bottomWindowRange"][str_d_ind:stp_d_ind+1]
        except Exception as e:
            return Response(response=json.dumps({"message": "Error in deleting old dip angle: "+str(e)}), status=400, mimetype='application/json')
        else: pass
        
        dele= coll.delete_one(q)
        ins=coll.insert_one(data)
    except Exception as e:
        return Response(response=json.dumps({"message": "Error in deleting old dip angle: "+str(e)}), status=400, mimetype='application/json')
    else:
        pass
    
    old_df = doc[0]
    stations = old_df['stations']
    for station in stations:
        rangeOld =  np.around(np.arange(station['startDepth'], station['endDepth']+0.1, 0.1),1)
        rangeNew = np.around(np.arange(startDepthNew, endDepthNew+0.1, 0.1),1)
        rangeNewSet = set(rangeNew)
        print(len(rangeNewSet.intersection(rangeOld)))
        if len(rangeNewSet.intersection(rangeOld))!=0:
            return Response(response=json.dumps({"message": "Dip angle cannot be modified as it overlaps with another dip angle"}), status=400, mimetype='application/json')
    try:
        # --------- dip angle for each depth ---------------
        depthRange = list(np.around(np.arange(startDepthNew, endDepthNew+0.1, 0.1),1))
        depth_length = len(depthRange)
        slope = math.tan(math.radians(90-body['angle']))
        deltaX = endDepthNew - startDepthNew
        slope_X_deltaX = deltaX*slope
        
        def findEndY(windowValue):
            windowEndY = windowValue + slope_X_deltaX
            deltaY = abs(windowEndY-windowValue)
            increment = deltaY / depth_length
            if windowEndY < windowValue: increment = -increment
            windowRange = list(np.around(np.arange(windowValue, windowEndY, increment),4))
            return windowRange
            
        lenArrOld=len(doc[0]['depthRange'])    
        old_df_data = { "depthRange": doc[0]['depthRange'], "topWindowRange": doc[0]['topWindowRange'][:lenArrOld],
                        "bottomWindowRange": doc[0]['bottomWindowRange'][:lenArrOld] }
        old_df = pd.DataFrame(old_df_data)
        if angle==90:
            topWindowRange = [ body['topWindow'] ] *depth_length
            bottomWindowRange = [ body['bottomWindow'] ] *depth_length
        else:
            topWindowRange = findEndY(body['topWindow'])
            bottomWindowRange = findEndY(body['bottomWindow'])
        lenArr=len(depthRange)
        
        new_df_data = { "depthRange": depthRange, "topWindowRange": topWindowRange[:lenArr],
                        "bottomWindowRange": bottomWindowRange[:lenArr] }
        
        new_df = pd.DataFrame(new_df_data)
        df_to_store = pd.concat([old_df, new_df], ignore_index = True)
        
        df_to_store = df_to_store.sort_values(by = 'depthRange')
        
        dict_to_store = df_to_store.to_dict('list')
        
        stations = doc[0]['stations']
        stationId = "".join([char for char in str(datetime.now()) if char.isalnum()])
        stationNew = {"startDepth":startDepthNew, "endDepth": endDepthNew, "angle":angle, "stationId":stationId,
                        "topWindow": body['topWindow'], "bottomWindow": body['bottomWindow'], "lastUpdatedDate": updatedDate,
            "lastUpdatedUserId": userId}
        stations.append(stationNew)
        
        save_df_data = {}
        save_df_data['customWellId'] = customWellId
        save_df_data['stations'] = stations
        save_df_data['depthRange'] = dict_to_store['depthRange']
        save_df_data['topWindowRange'] = dict_to_store['topWindowRange']
        save_df_data['bottomWindowRange'] = dict_to_store['bottomWindowRange']
        coll.delete_one(q)
        rec = coll.insert_one(save_df_data)
    except Exception as e:
        return Response(response=json.dumps({"message": "Error in adding new dip angle: "+str(e),"error db":str(rec)}), status=400, mimetype='application/json')
    else:
        return Response(response=json.dumps({"message": "Dip angle modified"}), status=200, mimetype='application/json')
    
@welldata.route('/welldata/getDipHistory', methods=['POST'])
def getDipHistory():
    body = request.get_json()
    coll = db.dipanglehistory
    customWellId = body.get("customWellId", None)
    startDepth = body.get("startDepth", 0)
    endDepth = body.get("endDepth", 0)
    q = {"customWellId": customWellId}
    doc = list(coll.find(q))
    if len(doc)==0:
        return Response(response=json.dumps({"message": "No dip angle history found"}), status=400, mimetype='application/json')
    depthRange = doc[0]['depthRange']
    topWindowRange =  doc[0]['topWindowRange']
    bottomWindowRange = doc[0]['bottomWindowRange']
    lst=np.asarray(depthRange)
    startDepthIndex = (np.abs(lst - startDepth)).argmin()
    endDepthIndex = (np.abs(lst - endDepth)).argmin()+1
    depthRange = depthRange[startDepthIndex:endDepthIndex]
    topWindowRange = topWindowRange[startDepthIndex:endDepthIndex]
    bottomWindowRange = bottomWindowRange[startDepthIndex:endDepthIndex]
    resp = {
        'depthRange':depthRange, 'topWindowRange': topWindowRange, 'bottomWindowRange': bottomWindowRange
    }
    return Response(response=json.dumps(resp), status=200, mimetype='application/json')

@welldata.route('/welldata/listDipAngle', methods=['POST'])
def listDipAngle():
    body = request.get_json()
    coll = db.dipanglehistory
    customWellId = body.get("customWellId", None)
    q = {"customWellId": customWellId}
    doc = list(coll.find(q))
    if len(doc)==0:
        return Response(response=json.dumps([]), status=200, mimetype='application/json')
    else:
        try:
            df=pd.DataFrame(doc[0]['stations'])
            df=df.sort_values(by=['startDepth'], ascending = False)
            df.fillna("", inplace = True)
            dict_of_df = df.to_dict('records')
            return Response(response=json.dumps(dict_of_df), status=200, mimetype='application/json')
        except Exception as e:
            return Response(response=json.dumps([]), status=200, mimetype='application/json')
    
@welldata.route('/welldata/deleteDipAngle', methods=['POST'])
def deleteDipAngle():
    body = request.get_json()
    coll = db.dipanglehistory    
    customWellId = body.get("customWellId", None)
    stationId = body.get("stationId", None)
    q = {"customWellId": customWellId}
    doc = list(coll.find(q))
    if len(doc)==0:
        return Response(response=json.dumps({"message": "No dip angle history found for this well"}), status=400, mimetype='application/json')
    try:
        data = doc[0]
        data_stations = data["stations"]
        str_d = -1
        for station in data_stations:
            if station['stationId']==stationId:
                str_d=station['startDepth']
                stp_d=station['endDepth']
                data_stations.remove(station)
                break
        if str_d == -1:
            return Response(response=json.dumps({"message": "Station not found for this well"}), status=400, mimetype='application/json')
        del data["_id"]
        data["stations"] = data_stations
        str_d_ind=data["depthRange"].index(str_d)
        stp_d_ind=data["depthRange"].index(stp_d)
        try:
            del data["depthRange"][str_d_ind:stp_d_ind+1]
            del data["topWindowRange"][str_d_ind:stp_d_ind+1]
            del data["bottomWindowRange"][str_d_ind:stp_d_ind+1]
        except Exception as e:
            return Response(response=json.dumps({"message": "Error in deleting station: "+str(e)}), status=400, mimetype='application/json')
        else: pass
        dele= coll.delete_one(q)
        ins=coll.insert_one(data)
    except Exception as e:
        return Response(response=json.dumps({"message": "Error in deleting station: "+str(e)}), status=400, mimetype='application/json')
    else:
        return Response(response=json.dumps({"message": "Station deleted"}), status=200, mimetype='application/json')