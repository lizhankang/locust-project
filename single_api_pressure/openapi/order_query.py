import json
import logging
import random
import time
from json import JSONDecodeError

import requests
from locust import HttpUser, task, between, constant_throughput, tag, events
from locust.env import Environment

from common.api_utils import ApiUtils
env = 'dev'


def fetch_order_sns():
    # 模拟从接口获取 token 的过程
    order_tokens = []
    order_sns = []
    for _ in range(35):
        host = "https://vip-apigateway.iwosai.com" if env == 'dev' else "https://vapi.shouqianba.com"
        # host = "https://lite-pos-service.iwosai.com" if env == 'dev' else "https://vapi.shouqianba.com"
        endpoint = host + "/api/lite-pos/v1/sales/purchase"
        headers = {
            "Content-Type": "application/json",
        }
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": "1024" if env == "dev" else "700001",
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": "10",
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
        if response.status_code == 200:
            order_tokens.append(response.json()['response']['body']['biz_response']['data']['order_token'])
            order_sns.append(response.json()['response']['body']['biz_response']['data']['order_sn'])

    print(f'order_sns: {order_sns}')
    print(f'order_tokens: {order_tokens}')
    return order_sns


# order_sns = fetch_order_sns()


class OrderQueryUser(HttpUser):
    host = "https://vip-apigateway.iwosai.com"
    # def on_start(self):
    #     print("CashierUser! START ")
    #     self.order_sn = random.choice(order_sns)
    #     order_sns.remove(self.order_sn)
    #     print("CashierUser: {}! START ".format(self.order_sn))

    @task
    @tag('signature')
    def task1(self):
        endpoint = "/api/lite-pos/v1/sales/query"
        headers = {
            "Content-Type": "application/json",
        }
        biz_body = {
            "brand_code": "1024" if env == "dev" else "700001",
            # "order_sn": self.order_sn
            "order_sn": "a25cf5de4e3bdc95fcbb49401d8cf0c0"
        }
        body = ApiUtils(env).signed_body(biz_body)
        with self.client.post(url=endpoint, headers=headers, json=body,
                              name='order_query'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[RESPONSE]: {response.text}')

    @task
    @tag('no_signature')
    def task2(self):
        endpoint = "/api/lite-pos/v1/sales/query"
        headers = {
            "Content-Type": "application/json",
            "App-Id": "28lpm3781001",
        }
        biz_body = {
            "brand_code": "1024" if env == "dev" else "700001",
            # "order_sn": self.order_sn
            "order_sn": "a25cf5de4e3bdc95fcbb49401d8cf0c0"
        }
        with self.client.post(url=endpoint, headers=headers, json=biz_body,
                              name='order_query'.upper() + "[no_signature]", catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[RESPONSE]: {response.text}')

