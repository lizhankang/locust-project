import json
from json import JSONDecodeError

import jsonpath
import requests
from locust import task, tag, HttpUser

from common.api_utils import ApiUtils

env = ""


class IPay(HttpUser):
    def on_start(self):
        self.__dict__['info'] = {
            "brand": "1024" if env != "prod" else "9998888",
            "amount": "1",
            "headers": {
                "Content-Type": "application/json",
                "App-Id": "28lpm3781001",
            }
        }

    @task
    def task1(self):
        endpoint = "/api/lite-pos/v1/sales/ipay"
        headers = {
            "Content-Type": "application/json",
            "App-Id": "28lpm3781001",
        }
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": self.__dict__.get('info').get('brand'),
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": self.__dict__.get('info').get('amount'),
            "scene_type": "1",
            "dynamic_id": "67809890797",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "P-csn" + check_sn,
            "sales_sn": "P-csn" + sales_sn,
            "sales_time": ApiUtils.date_time(),
            "subject": "电子码核销",
            "description": "Description of purchase order",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "tender_type": "8",
            "sub_tender_type1": "801"
        }
        body = ApiUtils(env).signed_body(biz_body)
        with self.client.post(url=endpoint, headers=headers, json=biz_body,
                              name='IPay'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[RESPONSE]: {json.dumps(response.json(), indent=4, ensure_ascii=False)}')
