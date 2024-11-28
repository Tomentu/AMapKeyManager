
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
    start_rank = 24490
    end_rank = 1000000
    df = pd.read_excel("d:\\城市-商圈排名信息3_新增商圈重新排序.xlsx")
    #ids = [11680, 11681, 11682, 11683, 11684, 11685, 11686, 11687, 11688, 11689, 11690, 11691, 11692, 11693, 11694, 11695, 11696, 11697, 11698, 11699, 11700, 11701, 11702, 11703, 11704, 11705, 11706, 11707, 11708, 11709, 11710, 11711, 11712, 11713, 11714, 11715, 12478, 12479, 12480, 12481, 12482, 12483, 12484, 12485, 12486, 12487, 12488, 12489, 12490, 12860, 12861, 12862, 12863, 12864, 12865, 12866, 12867, 12868, 12869, 12870, 12871, 12872, 13205, 13206, 13207, 13208, 13209, 13210, 13211, 13212, 13213, 13214, 13215, 13216, 13217, 13517, 13518, 13519, 13520, 13521, 13522, 13523, 13524, 13525, 13526, 13527, 13528, 13529, 13530, 13531, 13532, 13533, 13534, 13535, 13536, 13537, 13538, 13539, 13540, 13541, 13542, 13543, 13544, 13545, 13546, 13547, 13585, 13586, 13587, 13588, 13589, 13590, 13591, 13592, 13593, 13594, 13595, 13596, 13597, 13598, 13764, 13765, 13766, 13767, 13768, 13769, 13770, 13771, 13772, 13773, 13774, 13775, 13776, 13777, 13778, 13779, 13780, 13781, 13782, 13783, 13784, 14119, 14120, 14121, 14122, 14123, 14599, 14600, 14601, 14602, 14603, 14604, 14605, 14606, 14607, 14608, 14609, 14610, 14611, 14612, 14613, 14614, 14615, 14616, 14617, 14618, 14619, 14620, 14621, 14622, 14623, 14624, 14625, 14626, 14627, 14628, 14629, 14630, 14631, 14637, 14638, 14639, 14640, 14641, 14642, 14643, 14644, 14645, 14646, 14647, 14648, 14649, 14650, 14651, 14652, 14653, 14654, 14655, 14695, 14696, 14697, 14698, 14699, 14700, 14701, 14702, 14723, 14724, 14725, 14726, 14727, 14728, 14729, 14730, 14777, 14778, 14779, 14780, 14781, 14782, 14783, 14784, 14817, 14818, 14819, 14820, 14821, 14822, 14823]
    ids = [21476, 21477, 21478, 21479, 21480, 21481, 21482, 21483, 21484, 21485, 21486, 21487, 21488, 21489, 25733, 25734, 25738, 25739, 25740, 25743, 25746, 25748, 25751, 25754, 25761, 25766, 25777, 25782, 26507, 26508, 26509, 26510, 26511, 26512, 26513, 26514, 26515, 26516, 26517, 26518, 26519, 26520, 26521, 26522, 26523, 26524, 26525, 26526, 26527, 26528, 26529, 26530, 26531, 26532, 26533, 26534, 26535, 26536, 26537, 26538]
    #筛选rank大于start_rank小于end_rank的
    df = df[(df['rank'] >= start_rank)]
    df = df[(df['rank'] <= end_rank)]
    k = 1
    for index, row in df.iterrows():
        #print(row['city'], row['rank'],row["poi_boundary_02"])
        #发送post请求
        if not row['if_get'] == 1 :

            # print(row['city'])
            # continue
            if  not row['rank'] in ids:
                pass
            if k >=90:
                break
            try:
                response = requests.post('http://172.21.12.24:5001/api/polygon/tasks', json={
                    "task_id": row['rank'],
                "name": row['city'] + "_" + str(row['rank']),
                "polygon": row["poi_boundary_02"],
                "priority": row['rank']
            })
                print(response.json())
                if response.status_code ==200:
                    time.sleep(1)
                    k+=1
            except Exception as e:
                print(e)
        
