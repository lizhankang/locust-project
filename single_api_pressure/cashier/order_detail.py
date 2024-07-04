import json
import random
import time
from json import JSONDecodeError

import requests
from locust import HttpUser, constant_throughput, tag, task, events

from common.api_utils import ApiUtils
import logging
from locust.runners import MasterRunner

env = 'dev'


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("")
    print(f'\033[91m [@events.test_start.add_listener] :  A new test is starting \033[0m')


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f'\033[91m [@events.test_stop.add_listener] :  A new test is ending \033[0m')


# 每个工作进程（而不是每个用户）
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    if isinstance(environment.runner, MasterRunner):
        print(f"\033[91m [@events.init.add_listener] :  I'm on master node \033[0m")
    else:
        print(f"\033[91m [@events.init.add_listener] :  I'm on a worker or standalone node \033[0m")


@events.request.add_listener
# def my_request_handler(request_type, name, response_time, response_length, response,
#                        context, exception, start_time, url, **kwargs):
def my_request_handler(url, request_type, name, response, exception, **kwargs):
    if exception:
        print(f"\033[91m [@events.request.add_listener] :  Request to {name} failed with exception {exception} \033[0m")
    else:
        print(f"\033[91m [@events.request.add_listener] :  Successfully made a request to: {name} \033[0m")
        # print(f"\033[91m [@events.request.add_listener] :  Successfully made a request to: {request} \033[0m")
        print(f"\033[91m [@events.request.add_listener] :  The response was {response.text} \033[0m")


def fetch_order_tokens():
    # 模拟从接口获取 token 的过程
    order_tokens = []
    order_sns = []
    for _ in range(35):
        host = "https://vip-apigateway.iwosai.com" if env != 'prod' else "https://vapi.shouqianba.com"
        endpoint = host + "/api/lite-pos/v1/sales/purchase"
        headers = {
            "Content-Type": "application/json",
        }
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": "1024" if env != "prod" else "700001",
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": "11",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "P-csn" + check_sn,
            "sales_sn": "P-ssn" + sales_sn,
            "sales_time": ApiUtils.date_time(),
            "subject": "Subject of the purchase order",
            "description": "Description of purchase order",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "enable_sub_tender_types": "301",
            "expired_at": ApiUtils.date_time(minutes=30),
            "crm_account_option": {
                "app_type": 5,
                "wx_union_id": "lip-vip"
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        body = ApiUtils(env).signed_body(biz_body)
        response = requests.post(url=endpoint, headers=headers, json=body)  # 替换为实际获取 token 的接口
        print(f'[RESPONSE]: {response.text}')
        if response.status_code == 200:
            order_tokens.append(response.json()['response']['body']['biz_response']['data']['order_token'])
            order_sns.append(response.json()['response']['body']['biz_response']['data']['order_sn'])

    print(f'order_sns: {order_sns}')
    print(f'order_tokens: {order_tokens}')
    return order_tokens


order_tokens = fetch_order_tokens()


class OrderDetailUser(HttpUser):

    def on_start(self):
        self.__dict__['info'] = {
            "headers": {
                "Content-Type": "application/json",
            },
            "order_token": random.choice(order_tokens),
        }
        order_tokens.remove(self.__dict__.get("info").get('order_token'))
        logging.info(f'[User INFO]: {self.environment.runner}')

    @task
    def task1(self):
        endpoint = "/api/lpos/cashier/v2/cashier"
        params = {
            "order_token": self.__dict__.get("info").get('order_token')
            # "order_token": "ad4a58b821c97c83b3c036ebb4576a2e"
        }
        with self.client.get(url=endpoint, headers=self.__dict__.get("info").get('headers'), params=params,
                             name='order_detail'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[CASHIER-RESPONSE]: {json.dumps(response.json(), indent=4, ensure_ascii=False)}')
            if response.status_code != 200:
                # 手动将请求标记为fail
                response.failure(response.text)
            try:
                if response.json()["result_code"] != "200":
                    response.failure("Did not get expected value in '$.biz_response.result_code'")
            except JSONDecodeError:
                response.failure("Response could not be decoded as JSON")
            except KeyError:
                response.failure("Response did not contain expected key '$.biz_response.result_code'")
