import datetime
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pymysql
import requests
from faker import Faker
from tqdm import tqdm

from common import auth_utils
from common.auth_utils import AuthUtils

all_exception_info = []


def read_csv():
    csv_file = "/Users/lizhankang/Documents/测试卡.csv"
    # 读取前50万行数据
    df = pd.read_csv(csv_file, nrows=500000)
    data = df.to_dict(orient='list')
    # print(data.keys())
    # print(len(data['card_number']))
    return data['static_auth_code']


def read_member(name_file):
    # name_file = "/Users/lizhankang/workSpace/selfProject/pythonProject/locust-project/demo/2024-07-25T08:43:58.xlsx"
    return pd.read_excel(name_file).to_dict('list')['member_sn']


def read_card_excel(file):
    # print(pd.read_excel(file, header=7).to_dict('list')['静态核销码'])
    return pd.read_excel(file, header=7).to_dict('list')['静态核销码']


def distribute_card():
    #
    cards_per_user = 500
    name_file = "/Users/lizhankang/workSpace/selfProject/pythonProject/locust-project/demo/2024-07-25T08:43:58.xlsx"
    members = read_member(name_file)
    auth_codes = read_csv()
    data = {}
    for index, member_sn in enumerate(members):
        data[member_sn] = auth_codes[index * cards_per_user: (index + 1) * cards_per_user]
    dataframe = pd.DataFrame(data)
    file_name = f'{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}-relation.xlsx'
    dataframe.to_excel(file_name, index=False)


def bind_api(member_sn, auth_codes, main_progress):
    exception_codes = []
    member_info = {
        member_sn: exception_codes
    }

    auth_utils = AuthUtils('dev')
    thread_name = threading.current_thread().name
    print(f"任务开始: {thread_name} - {member_sn} start")

    url = "https://vip-apigateway.iwosai.com/api/wallet/v1/giftcard/members/cards/redeem"
    headers = {"Content-Type": "application/json"}
    biz_body = {
        "brand_code": "1043",
        "client_member_sn": member_sn,
        "redeem_code": None
    }
    for auth_code in auth_codes:
        biz_body['redeem_code'] = auth_code
        body = auth_utils.signature(biz_body)
        retry_result = "success"
        try:
            response = requests.post(url, headers=headers, json=body)
            biz_response = response.json()['response']['body']['biz_response']
        except Exception as e:
            print(f'执行任务时，接口调用异常: {e}')
            retry_result = api_retry(url=url, headers=headers, body=body, number=10)
        else:
            if not (
                        (
                            biz_response['result_code'] == '200'
                        )
                        or
                        (
                            biz_response['result_code'] == '400'
                            and
                            biz_response['error_code'] == 'W.GC.REDEEM_CODE_ALREADY_USED'
                        )
            ):
                retry_result = api_retry(url=url, headers=headers, body=body, number=10)
        finally:
            if retry_result == 'success':
                pass
            else:
                # 把人和失败的卡信息记录下来
                exception_codes.append(auth_code)
                member_info['msg'] = retry_result
                print(f'{auth_code} 兑换失败, 失败原因: {retry_result}')

        main_progress.update(1)

    if len(exception_codes) > 0:
        all_exception_info.append(member_info)

    print(f"任务完成: {thread_name} - {member_sn} over")


def api_retry(url, headers, body, number):
    attempts = 0
    result = "fail"
    response = {}
    while attempts < number:
        try:
            response = requests.post(url=url, headers=headers, json=body)
            biz_response = response.json()['response']['body']['biz_response']
        except Exception as e:
            print(f'重试时调用接口异常: {e}')
            attempts += 1
            result = "fail  " + e
            continue

        if not (
                    (
                            biz_response['result_code'] == '200'
                    )
                    or
                    (
                            biz_response['result_code'] == '400'
                            and
                            biz_response['error_code'] == 'W.GC.REDEEM_CODE_ALREADY_USED'
                    )
        ):
            attempts += 1
            result = "fail  " + e
            continue
        else:
            result = "success"
            break
    return result


def read_distribute_file():
    file = "/Users/lizhankang/workSpace/selfProject/pythonProject/locust-project/demo/2024-07-25T09:12:32-relation.xlsx"
    data = pd.read_excel(file).to_dict('list')
    print("文件读取完毕")
    return data


def main():
    max_threads = 90  # 最大线程数
    # 总任务量
    total_tasks = sum(len(codes) for codes in read_distribute_file().values())
    with tqdm(total=total_tasks, desc="总进度") as main_progress:
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = []
            distribute_data = read_distribute_file()
            for member_sn, codes in distribute_data.items():
                future = executor.submit(bind_api, member_sn, codes, main_progress)
                futures.append(future)

    print("所有任务已执行完成")
    print(f'兑换失败的数据: {all_exception_info}')


def check_user_card_number():

    except_data = []

    distribute_data = read_distribute_file()
    members = distribute_data.keys()
    auth_utils = AuthUtils('dev')
    url = "https://vip-apigateway.iwosai.com/api/wallet/v1/giftcard/members/cards/list"
    headers = {"Content-Type": "application/json"}
    biz_body = {
        "brand_code": "1043",
        "client_member_sn": None,
        "page_size": 10,
        "page": 1
    }
    for member_sn in tqdm(members, desc="进度"):
        biz_body['client_member_sn'] = member_sn
        body = auth_utils.signature(biz_body)
        response = requests.post(url, headers=headers, json=body)
        card_number = response.json()['response']['body']['biz_response']['data']['total']
        if card_number != 500:
            except_member = {
                member_sn: card_number
            }
            except_data.append(except_member)
            print(response.text)
    print(f'except_data: {except_data}')


def member_100_bind_card_distribute():
    card_2000 = "/Users/lizhankang/Documents/shouqianba/lulu压测/核销2000张用卡.xlsx"
    card_list = read_card_excel(card_2000)

    member_100 = "/Users/lizhankang/workSpace/selfProject/pythonProject/locust-project/demo/会员-07-25T15:31.xlsx"
    member_list = read_member(member_100)
    # 分发
    cards_per_user = 1
    data = {}
    for index, member_sn in enumerate(member_list):
        data[member_sn] = card_list[index * cards_per_user: (index + 1) * cards_per_user]
    dataframe = pd.DataFrame(data)
    file_name = f'{100}{"用户"}{datetime.datetime.now().strftime("%m-%dT%H:%M:%S")}-relation.xlsx'
    dataframe.to_excel(file_name, index=False)


def member_100_card_bind():
    # 绑定关系
    bind_relation_file = "/Users/lizhankang/workSpace/selfProject/pythonProject/locust-project/demo/100用户07-25T15:46:23-relation.xlsx"
    data = pd.read_excel(bind_relation_file).to_dict('list')
    # 绑定
    max_threads = 10  # 最大线程数
    total_tasks = sum(len(codes) for codes in data.values())
    with tqdm(total=total_tasks, desc="总进度") as main_progress:
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = []
            for member_sn, codes in data.items():
                future = executor.submit(bind_api, member_sn, codes, main_progress)
                futures.append(future)

    print("所有任务已执行完成")
    print(f'兑换失败的数据: {all_exception_info}')


def ipay(code, main_progress):
    auth_utils = AuthUtils('dev')
    url = "https://vip-apigateway.iwosai.com/api/lite-pos/v1/sales/ipay"
    headers = {"Content-Type": "application/json"}
    for i in range(110):
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": '1043',
            "store_sn": "offline",
            "workstation_sn": "567",
            "amount": "1",
            "scene_type": "1",
            "dynamic_id": str(code),
            "currency": "156",
            "industry_code": "0",
            "tender_type": "8",
            "sub_tender_type": "303",
            "check_sn": "csn" + check_sn,
            "sales_sn": "ssn" + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the purchase order",
            "description": "Description of purchase order",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
        }
        body = auth_utils.signature(biz_body)
        response = requests.post(url=url, headers=headers, json=body)
        print(response.text)
        main_progress.update(1)


def freeze_card():
    # 1000个用户卡改成已冻结
    # 数据库配置
    config = {
        'host': 'rm-8vbq2i8907zzf0i1a.mysql.zhangbei.rds.aliyuncs.com',
        'user': 'p_lizhankang',
        'password': 'RkIApjlixmqDw_9sXzEfY3r7$(uC',
        'database': 'upay_gift_card',
    }

    # 连接数据库
    connection = pymysql.connect(**config)
    cur = connection.cursor()
    distribute_data = read_distribute_file()
    for member, codes in tqdm(distribute_data.items(), desc="总进度"):
        if len(set(codes)) == len(codes):
            templ = "update card set sub_freeze_state=1 where static_auth_code in {};"
            sql = templ.format(tuple(codes))
            print(sql)
            cur.execute(sql)
            connection.commit()


def bulk_redeem():
    # 绑定关系
    bind_relation_file = "/Users/lizhankang/workSpace/selfProject/pythonProject/locust-project/demo/100用户07-25T15:46:23-relation.xlsx"
    data = pd.read_excel(bind_relation_file).to_dict('list')

    max_threads = 10  # 最大线程数
    with tqdm(total=10000, desc="总进度") as main_progress:
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = []
            for member, codes in data.items():
                future = executor.submit(ipay, codes[0], main_progress)
                futures.append(future)

    print("所有任务已执行完成")


def demo1():
    for i in range(1000000000000):
        time.sleep(0.01)
        print(i)


def demo2():
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for i in range(100):
            future = executor.submit(demo1)
            futures.append(future)


if __name__ == '__main__':
    # main()
    # check_user_card_number()
    # member_100_card_bind()
    # freeze_card()
    # bulk_redeem()
    demo2()
    pass
