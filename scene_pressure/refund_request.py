from json import JSONDecodeError

import jsonpath
import requests
from locust import task, tag, HttpUser

from common.api_utils import ApiUtils

env = ""


class RefundRequest(HttpUser):
    """
    提交退款请求
    """

    def on_start(self):
        self.__dict__['info'] = {
            "brand": "1024" if env != "prod" else "9998888",
            "amount": "1",
            "headers": {
                "Content-Type": "application/json",
            }
        }
        # 准备交易？
        # 获取 user token
        user_token_url = "https://vip-apigateway.iwosai.com/api/wallet/v1/members/_get_user_token"
        user_info = {
            "brand_code": self.__dict__.get('info').get('brand'),
            "client_member_sn": "lip-vip"
        }
        body = ApiUtils(env).signed_body(user_info)
        response = requests.post(url=user_token_url, headers=self.__dict__.get('info').get('headers'), json=body).json()
        user_token = jsonpath.jsonpath(response, "$.response.body.biz_response.data.user_token")
        # 获取 卡片 的 authcode
        card_number = ""
        domain = "https://ums.shouqianba.com" if env == 'prod' else "https://pro-customer-gateway.iwosai.com"
        auth_code_url = domain + "/wallet/v1/authcode/getmycode"
        auth_code_headers = {"Content-Type": "application/json;charset=utf-8", "Authorization": user_token}
        auth_code_body = {"preferred_class": "GIFT_CARD", "preferred_refer_id": card_number}
        response = requests.post(url=auth_code_url, headers=auth_code_headers, json=auth_code_body).json()
        auth_code = response.get('data').get('auth_code')

        # 调用立即付
        ipay_url = "https://vip-apigateway.iwosai.com/api/lite-pos/v1/sales/ipay"
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        ipay_body = {
            "request_id": request_id,
            "brand_code": self.__dict__.get('info').get('brand'),
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": self.__dict__.get('info').get('amount'),
            "scene_type": "1",
            "dynamic_id": auth_code,
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
        body = ApiUtils(env).signed_body(ipay_body)
        response = requests.post(url=ipay_url, headers=self.__dict__.get('info').get('headers'), json=body).json()
        pay_tender_sn = jsonpath.jsonpath(response, "$.response.body.biz_response.data.tender_sn")
        self.__dict__["info"]["pay_tender_sn"] = pay_tender_sn

    @task
    def test_task1(self):
        endpoint = "/api/lite-pos/v1/sales/refund"
        headers = {
            "Content-Type": "application/json",
        }
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": self.__dict__.get('info').get('brand'),
            "store_sn": "LPK001",
            "workstation_sn": "02",
            "amount": - self.__dict__.get('info').get('amount'),
            "currency": "156",
            "industry_code": "0",
            "check_sn": check_sn,
            "sales_sn": sales_sn,
            "sales_time": ApiUtils.date_time(),
            "subject": "Subject of the purchase order",
            "description": "Description of purchase order",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "tenders": [
                {
                    "transaction_sn": check_sn,
                    "pay_status": 0,
                    "amount": - self.__dict__.get('info').get('amount'),
                    "original_tender_sn": self.__dict__.get('info').get('pay_tender_sn')
                }
            ],
            "refund_scene": "0"
        }
        body = ApiUtils(env).signed_body(biz_body)
        with self.client.post(url=endpoint, headers=headers, json=body,
                              name='refund'.upper(), catch_response=True) as response:
            if response.status_code != 200:
                print(response.status_code)
                # 手动将请求标记为fail
                response.failure(response.text)
