import os
from json import JSONDecodeError

import jsonpath

from common.api_utils import ApiUtils
from locust import HttpUser, SequentialTaskSet, task, between

envir = "dev"
num = 10


class PurchaseUserTaskSet(SequentialTaskSet):

    @task
    def task1(self):
        endpoint = "/api/lite-pos/v1/sales/purchase"
        headers = {
            "Content-Type": "application/json",
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
        with self.client.post(url=endpoint, headers=headers, json=ApiUtils(envir).signed_body(biz_body),
                              name='purchase'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[RESPONSE]: {response.text}')


class WebsiteUser(HttpUser):
    tasks = [PurchaseUserTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        # self.order_token = None


if __name__ == '__main__':
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if envir != "prod" else "http://vip-apigateway.iwosai.com"

    command_str = f"locust -f {file_name} --host={host} --users {num} --spawn-rate 3"
    os.system(command_str)
