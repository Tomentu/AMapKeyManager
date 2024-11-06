
#推送任务脚本
'''
网址：http://172.21.12.24:5001/api/polygon/tasks
请求：POST
参数：{
    "task_id": "4",
    "name": "北京_4",
    "polygon": "116.28482364886614,39.81368294817399|116.26858844816279,39.785372333504895|116.2874587428554,39.762504743724456|116.3225745483137,39.767963142303316|116.33884519990602,39.796270187242115|116.31997297941501,39.81912887965872|116.28482364886614,39.81368294817399",
    "priority": "4"
}
'''

#读xlxs

import time
import pandas as pd
import requests

if __name__ == '__main__':
    # 读取Excel文件
    start_rank = 40
    end_rank = 42
    df = pd.read_excel('D:\城市-商圈排名信息.xlsx')
    #筛选rank大于start_rank小于end_rank的
    df = df[(df['rank'] >= start_rank)]
    df = df[(df['rank'] <= end_rank)]
    for index, row in df.iterrows():
        print(row['city'], row['rank'],row["poi_boundary_02"])
        #发送post请求
        response = requests.post('http://172.21.12.24:5001/api/polygon/tasks', json={
            "task_id": row['rank'],
            "name": row['city'] + "_" + str(row['rank']),
            "polygon": row["poi_boundary_02"],
            "priority": row['rank']
        })
        print(response.json())
        time.sleep(5)
