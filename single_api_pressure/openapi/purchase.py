import json
import logging
import os
from json import JSONDecodeError
from locust import HttpUser, task, between, constant_throughput, tag, events

from common.api_utils import ApiUtils
env = 'dev'


class PurchaseUser(HttpUser):

    @task
    def task(self):
        endpoint = "/api/lite-pos/v1/sales/purchase"
        headers = {
            "Content-Type": "application/json",
            # "App-Id": "28lpm3781001",
        }
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": "1024",
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": "30000",
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
            "expired_at": ApiUtils.date_time(minutes=5),
            "crm_account_option": {
                "app_type": 5,
                "wx_union_id": "lip-vip"
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        body = ApiUtils(env).signed_body(biz_body)
        # print(json.dumps(body, indent=4, ensure_ascii=False))
        # print(json.dumps(biz_body, indent=4, ensure_ascii=False))
        with self.client.post(url=endpoint, headers=headers, json=body,
                              name='purchase'.upper(), catch_response=True) as response:
            # logging.info(response.url)
            # logging.info(response.text)
            print(f'[URL]: {response.request.url}')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[RESPONSE]: {response.text}')

