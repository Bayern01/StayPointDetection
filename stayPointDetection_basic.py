# -*- coding: utf-8 -*-
# @Author  : zhang35
# @Time    : 2020/09/16 18:00
# @Function: extract stay points from a GPS log file (implementation of algorithm in [1])

# References:
# [1] Q. Li, Y. Zheng, X. Xie, Y. Chen, W. Liu, and W.-Y. Ma, "Mining user similarity based on location history", in Proceedings of the 16th ACM SIGSPATIAL international conference on Advances in geographic information systems, New York, NY, USA, 2008, pp. 34:1--34:10.

# Test data could be downloaded from: https://www.microsoft.com/en-us/download/confirmation.aspx?id=52367

import time
import os
import sys
from math import radians, cos, sin, asin, sqrt
import folium
import webbrowser

#time_format = '%Y-%m-%d,%H:%M:%S'
time_format = '%Y%m%d%H%M%S'

# structure of point
class Point:
    def __init__(self, latitude, longitude, dateTime, arriveTime, leaveTime):
        self.latitude = latitude
        self.longitude = longitude
        self.dateTime = dateTime
        self.arriveTime = arriveTime
        self.leaveTime = leaveTime

# calculate distance between two points from their coordinate
def getDistanceOfPoints(pi, pj):
    lat1, lon1, lat2, lon2 = list(map(radians, [float(pi.latitude), float(pi.longitude),
                                                float(pj.latitude), float(pj.longitude)]))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    m = 6371000 * c
    return m

# calculate time interval between two points
def getTimeIntervalOfPoints(pi, pj):
    t_i = time.mktime(time.strptime(pi.dateTime, time_format))
    t_j = time.mktime(time.strptime(pj.dateTime, time_format))
    return t_j - t_i

# compute mean coordinates of a group of points
def computMeanCoord(gpsPoints):
    lat = 0.0
    lon = 0.0
    for point in gpsPoints:
        lat += float(point.latitude)
        lon += float(point.longitude)
    return (lat/len(gpsPoints), lon/len(gpsPoints))

# extract stay points from a GPS log file
# input:
#        file: the name of a GPS log file
#        distThres: distance threshold
#        timeThres: time span threshold
# default values of distThres and timeThres are 200 m and 30 min respectively, according to [1]
def stayPointExtraction(points, distThres=800, timeThres=15 * 60):
    stayPointList = []
    stayPointCenterList = []
    pointNum = len(points)
    i = 0
    while i < pointNum:
        j = i + 1
        while j < pointNum:
            # deal the last point
            dis = getDistanceOfPoints(points[i], points[j])
            if dis <= distThres and j == pointNum-1:
                diff = getTimeIntervalOfPoints(points[i], points[j])
                if diff >= timeThres:
                    latitude, longitude = computMeanCoord(points[i:j+1])
                    arriveTime = time.mktime(time.strptime(points[i].dateTime, time_format))
                    leaveTime = time.mktime(time.strptime(points[j].dateTime, time_format))
                    dateTime = time.strftime(time_format, time.localtime(arriveTime)), time.strftime(time_format, time.localtime(leaveTime))
                    stayPointCenterList.append(Point(latitude, longitude, dateTime, arriveTime, leaveTime))
                    stayPointList.extend(points[i:j+1])
                break

            if dis > distThres:
                # points[j] has gone out of bound thus it should not be counted in the stay points.
                diff = getTimeIntervalOfPoints(points[i], points[j-1])

                if diff >= timeThres:
                    latitude, longitude = computMeanCoord(points[i:j])
                    arriveTime = time.mktime(time.strptime(points[i].dateTime, time_format))
                    leaveTime = time.mktime(time.strptime(points[j-1].dateTime, time_format))
                    dateTime = time.strftime(time_format, time.localtime(arriveTime)), time.strftime(time_format, time.localtime(leaveTime))
                    stayPointCenterList.append(Point(latitude, longitude, dateTime, arriveTime, leaveTime))
                    stayPointList.extend(points[i:j])
                break
            j += 1
        i = j

    return stayPointCenterList, stayPointList

# parse lines into points
def parseGeoTxt(lines):
    points = []
    for line in lines:
        field_pointi = line.rstrip().split(',')
        latitude = float(field_pointi[1])
        longitude = float(field_pointi[0])
        #dateTime = field_pointi[-2] + ',' + field_pointi[-1]
        dateTime = field_pointi[2][0:14]
        if field_pointi[3] == "outdoor":
            radius = 800
        else:
            radius = 100
        points.append(Point(latitude, longitude, dateTime, 0, 0))
    return points

# add points into mapDots (type: folium.map.FeatureGroup())
def addPoints(mapDots, points, color):
    for p in points:
        mapDots.add_child(folium.CircleMarker(
            [p.latitude, p.longitude], 
            radius=10,
            tooltip=p.dateTime,
            color=color,
            ))

def main():
    m = folium.Map(location=[30.597814,104.06764])
    tooltip = "hello"
    mapDots = folium.map.FeatureGroup()

    for dirname, dirnames, filenames in os.walk('d:/input/single'):
        filenum = len(filenames)
        print(filenum , "files found")
        count = 0
        for filename in filenames:
            if  filename.endswith('txt'):
                gpsfile = os.path.join(dirname, filename)
                print("processing:" ,  gpsfile) 
                log = open(gpsfile, 'r')
                lines = log.readlines()[0:] # first 6 lines are useless
                points = parseGeoTxt(lines)
                stayPointCenter, stayPoint = stayPointExtraction(points)
                addPoints(mapDots, points, 'black')

                if len(stayPointCenter) > 0:
                    # add pionts to a group to be shown on map
                    addPoints(mapDots, stayPoint, 'blue')
                    addPoints(mapDots, stayPointCenter, 'red')

                    # writen into file ./StayPoint/*.plt
                    spfile = gpsfile.replace('d:/input/single', 'd:/input/output').replace('.txt', '_basic.txt')
                    if not os.path.exists(os.path.dirname(spfile)):
                        os.makedirs(os.path.dirname(spfile))
                    spfile_handle = open(spfile, 'w+')
                    print('Extracted stay points:\nlongitude\tlatitude\tarriving time\tleaving time', file=spfile_handle)
                    for sp in stayPointCenter:
                        print("%.8f" %sp.longitude, "%.8f" %sp.latitude, time.strftime(time_format, time.localtime(sp.arriveTime)), time.strftime(time_format, time.localtime(sp.leaveTime)), file=spfile_handle)
                    spfile_handle.close()

                    print("writen into:" ,  spfile) 
                    count += 1
                else:
                    print(gpsfile , "has no stay point")
        print(count, "out of" , filenum , "files contain stay points")

    # show stay points on map
    m.add_child(mapDots)
    m.save(sys.path[0] + "/index1.html")
    webbrowser.open(sys.path[0] + "/index1.html")
if __name__ == '__main__':
    main()
