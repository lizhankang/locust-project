import datetime
import json
import sys
import threading
import time

import pandas as pd
import requests
from faker import Faker
from tqdm import tqdm

from common.auth_utils import AuthUtils
threadLock = threading.Lock()
bind_success_list = []
bind_fail_list = []


def single_thread_bulk_bind(environ, member_sn, card_number_list):
    auth_utils = AuthUtils(environ)
    thread_name = threading.current_thread().name

    for auth_code in tqdm(card_number_list, desc=f"{thread_name}: ", ncols=len(card_number_list)):

        url = "https://vip-apigateway.iwosai.com/api/wallet/v1/giftcard/members/cards/redeem"
        headers = {
            "Content-Type": "application/json",
        }
        biz_body = {
            "brand_code": "1024",
            "client_member_sn": member_sn,
            "redeem_code": auth_code
        }
        body = auth_utils.signature(biz_body)
        # threadLock.acquire()
        response = requests.post(url, headers=headers, json=body).json()
        if response['response']['body']['biz_response']['result_code'] != '200':
            print(json.dumps(response, ensure_ascii=False))
            bind_fail_list.append(auth_code)
        else:
            bind_success_list.append(auth_code)
        # threadLock.release()


def bulk_generate_name(number):
    # 初始化 Faker 实例
    fake = Faker()

    # 设置要生成的姓名数量和长度限制
    num_names = int(number)
    max_length = 20

    # 生成符合要求的姓名列表
    member_sn_list = []
    pref = datetime.datetime.now().strftime("%m%d%M")
    while len(member_sn_list) < num_names:
        print(len(member_sn_list))
        name = fake.name().replace(" ", "-") + pref
        if len(name) <= max_length and name not in member_sn_list:
            member_sn_list.append(name)

    # 创建 DataFrame
    df = pd.DataFrame(member_sn_list, columns=['member_sn'])

    # 保存到 Excel 文件
    file_name = f'{"会员"}-{datetime.datetime.now().strftime("%m-%dT%H:%M")}.xlsx'
    excel_file_path = file_name
    df.to_excel(excel_file_path, index=False)


def read_member_sn(members_file, sheet_name):
    member_sn_list = pd.read_excel(members_file, sheet_name=sheet_name, header=0).to_dict(orient='list')[
        'member_sn']
    if len(member_sn_list) != len(set(member_sn_list)):
        msg = f'文件中存在相同的姓名'
        sys.exit(msg)
    return member_sn_list


def read_card_number():
    file_path = "/Users/lizhankang/Documents/shouqianba/礼品卡/beta/2024-07-23 17_02_06.xlsx"
    card_number_list = pd.read_excel(file_path, sheet_name='jaysun空白卡制卡任务', header=7).to_dict(orient='list')['静态核销码']
    return card_number_list


def distribute_card():
    members_file = "/Users/lizhankang/workSpace/selfProject/pythonProject/locust-project/demo/2024-07-23T21:59:10.xlsx"
    sheet_name = 'Sheet1'
    member_sn_list = read_member_sn(members_file, sheet_name)
    card_number_list = read_card_number()

    distribute_result = {member_sn: card_number_list[index * 100: (index + 1) * 100] for index, member_sn in
                       enumerate(member_sn_list)}

    dataframe = pd.DataFrame(distribute_result)
    dataframe.to_excel(members_file, index=False)


def read_relationship():
    members_file = "/Users/lizhankang/workSpace/selfProject/pythonProject/locust-project/demo/2024-07-23T21:59:10.xlsx"
    sheet_name = 'Sheet1'
    relation_data = pd.read_excel(members_file, sheet_name=sheet_name, header=0).to_dict(orient='list')
    print(f'总共读取到 {len(relation_data.keys())} 个用户')
    text = input("如果终止执行请输入 no : ")
    if text == 'no':
        return

    return relation_data


def main():
    threads = []
    for member_sn, card_number_list in read_relationship().items():
        thread = threading.Thread(target=single_thread_bulk_bind, args=('dev', member_sn, card_number_list))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

    print('Completed')
    print(f'绑定成功共：{len(bind_success_list)}')
    print(f'绑定失败共：{len(bind_fail_list)} {bind_fail_list}')


def read_csv():
    file = "/Users/lizhankang/Documents/测试卡.csv"


if __name__ == '__main__':
    # bulk_generate_name(100)
    # distribute_card()
    bulk_generate_name(100)

    pass
