#!/usr/bin/env python
# encoding: utf-8
'''
@author: lennon
@license: (C) Copyright 2019-2020, Node Supply Chain Manager Corporation Limited.
@contact: v-lefan@expedia.com
@software: pycharm
@file: room_distance_compare.py
@time: 2019-08-20 16:05
@desc:
'''
import traceback
import time
import re
import datetime
import numpy as np
import pandas as pd
from pandas import DataFrame
from scipy.ndimage import filters
import scipy.spatial.distance as dis
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.feature_extraction.text import CountVectorizer

temp_var = ''

def gaussian_filter(X):
    filtered_data = filters.gaussian_filter(X, sigma=20)


def getDistance(abp_df, level, compareobjects):
    try:
        col_cfg = pd.DataFrame(
            np.array(
                [
                 ['RoomType', 'Dice', 1],
                 ['RoomClass', 'Dice', 1],
                 ['RoomSize', 'cityblock', 0.5],
                 ['BedType', 'Dice', 1],
                 # ['Wheelchair', 'Dice', 1],
                 ['Smoking', 'Dice', 1],
                 ['View', 'Dice', 1]
                 ]),
            columns=['name', 'algo', 'weight'])
        col_cfg = col_cfg.set_index('name')
        #delete column "URL"
        rows = abp_df.drop(['URL'], axis=1)

        rows['RoomSize'] = rows['RoomSize'].apply(lambda x: re.search("([0-9])+", str(x)).group(0))

        d_list = []

        for c in rows.columns:
            algo = col_cfg.loc[c]['algo']
            if algo == 'Dice':
                one_hot = MultiLabelBinarizer()
                d_list.append(pd.DataFrame(
                    dis.pdist(one_hot.fit_transform(rows[c].apply(lambda x: tuple(str(x).split(',')))), algo)))
            elif algo == 'cityblock':
                ud = dis.pdist(rows[c].values.reshape(-1, 1), algo).reshape(-1, 1)
                scaler = MinMaxScaler()
                scaler.fit(ud)
                d_list.append(pd.DataFrame(scaler.transform(ud)))
            elif algo == 'ngram':
                corpus = rows[c]
                v = CountVectorizer(ngram_range=(1, 3), binary=True, lowercase=True)
                d_list.append(pd.DataFrame(dis.pdist(v.fit_transform(corpus).toarray(), 'Dice')))
            else:
                print('error')

        dm = pd.concat(d_list, ignore_index=True, axis=1)
        dm.columns = rows.columns

        d_weight = col_cfg['weight'].values.astype(np.float)
        # test = dm.values * d_weight
        ag1 = (dm.values * d_weight).mean(axis=1)
        #comment out for we don't need to compare with selves, there is no meaning
        # ag1_sq = dis.squareform(ag1)
        # gaussian_filter(ag1_sq)
        # np.fill_diagonal(ag1_sq, 1)

        #     ag1_sq[ag1_sq==0] = 1
        distance_df = pd.DataFrame(ag1)
        # print(distance_df)
        result = []
        for row_index, row in distance_df.iterrows():
            for col_index, distance in row.iteritems():
                if distance >= level:
                    result.append(
                        [str(abp_df.loc[row_index].URL), str(abp_df.loc[col_index].URL), distance, compareobjects])
        return result
    except ValueError as e:
        traceback.print_exc()
        print(e)
        raise Exception("Calculate failed!")


if __name__ == '__main__':
    start = datetime.datetime.now()

    SCRIPT = 'script'
    EXCEL_PATH_ONE = 'C:\PythonRelatedProject\compare\compare.xlsx'

    MANUAL = 'manual'
    EXCEL_PATH_RESULT= 'C:\PythonRelatedProject\compare\compare.xlsx'

    dataFrame_script = pd.read_excel(EXCEL_PATH_ONE, sheet_name=SCRIPT)
    dataFrame_Manual = pd.read_excel(EXCEL_PATH_RESULT, sheet_name=MANUAL)
#replace ' ' with 0
    dataFrame_script['RoomSize'].replace('', 0, inplace=True)
    dataFrame_script['RoomSize'].replace(np.nan, 0, inplace=True)
    dataFrame_script['RoomSize'].replace('unknown', 0, inplace=True)
    dataFrame_Manual['RoomSize'].replace('', 0, inplace=True)
    dataFrame_Manual['RoomSize'].replace(np.nan, 0, inplace=True)
    dataFrame_Manual['RoomSize'].replace('unknown', 0, inplace=True)
    dataFrame_Manual['RoomType'].replace('', 0, inplace=True)
    dataFrame_Manual['BedType'].replace('', 0, inplace=True)
    dataFrame_Manual['Smoking'].replace('', 0, inplace=True)

    #dataFrame_Result.drop(['ExtraAttributes', 'NumberOfRoomType'], axis=1, inplace=True)

    distance_result_list = list()
    count_script = 0
    for index, row_script in dataFrame_script.iterrows():
        #check if the new row of script is equal to the last one of manual,if not, it's a new hotel,begin with the 1st room of this hotel
        if temp_var != row_script['URL']:
            count_script = 0
        #when one roomtype of hotel from script finished compare with all roomtype of the same hotel from manual,go to next roomtype
        count_manual = 0
        count_script += 1
        #compared is used to set default not to compare
        compared = False
        #while one hotel's compare finished, break inner loop
        for index_m, row_manual in dataFrame_Manual.iterrows():
            #if row['URL'].strip() == rowr['URL'].strip():
            if row_script['URL'] == row_manual['URL']:
                #set compared to true means this row has been compared
                compared = True
                #erery time will set temp_var to the current row of manual
                temp_var = row_manual['URL']
                count_manual += 1
                # df = pd.DataFrame(columns=['URL', 'RoomName', 'RoomType', 'RoomClass', 'RoomSize', 'BedType', 'Wheelchair', 'Smoking', 'View'])
                df = pd.DataFrame(columns=['URL', 'RoomType', 'RoomClass', 'RoomSize', 'BedType', 'Smoking', 'View'])
                df.loc[0] = row_script
                df.loc[1] = row_manual
                compareobjects = str(count_script) + ' : ' + str(count_manual)
                print(str(index) +" " + str(index_m) +" " + row_script['URL'] + "  " + compareobjects)
                distance_result_list.extend(getDistance(df, 0, compareobjects))
            #finished comparing the current row of script with all the roomtype of the same hotel from manual
            else:
                count_manual = 0
            #break inner loop when finish comparing the current row of script with all the roomtype from the same hotel of manual
            if (compared == True) and (count_manual == 0):
                break

    df_distance_result = pd.DataFrame(np.array(distance_result_list), columns=['script', 'manual', 'difference', 'compareobjects'])
    # compare result write into a excel file
    now = time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime(time.time()))
    writer = pd.ExcelWriter('C:\PythonRelatedProject\compare\distance_' + now + '.xls')

    df_distance_result.to_excel(writer)
    writer.save()
    end = datetime.datetime.now()
    print('Running time: %s Seconds' % (end - start))
    pass