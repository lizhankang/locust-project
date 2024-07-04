from json import JSONDecodeError

import jsonpath
from locust import task, tag, HttpUser

from common.api_utils import ApiUtils

env = ""


class WxCardsPay(HttpUser):
    """
    收银台微信+cards支付
    """

    def on_start(self):
        self.__dict__['info'] = {
            "brand": "1024" if env != "prod" else "9998888",
            "amount": "1"
        }

    def test_task1(self):
        headers = {
            "Content-Type": "application/json",
        }

        # 创建订单，获取 order_token
        purchase_endpoint = "/api/lite-pos/v1/sales/purchase"
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        purchase_body = {
            "request_id": request_id,
            "brand_code": self.__dict__.get('info').get('brand'),
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": self.__dict__.get('info').get('amount'),
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
                "member_sn": "lip-vip"
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        purchase_body = ApiUtils(env).signed_body(purchase_body)
        order_token = ""
        with self.client.post(url=purchase_endpoint, headers=headers, json=purchase_body,
                              name='purchase'.upper(), catch_response=True) as response:
            if response.status_code != 200:
                print(response.status_code)
                # 手动将请求标记为fail
                response.failure(response.text)
            try:
                if response.json()["response"]["body"]["result_code"] != "200":
                    response.failure("Did not get expected value in '$.response.body.result_code'")
            except JSONDecodeError:
                response.failure("Response could not be decoded as JSON")
            except KeyError:
                response.failure("Response did not contain expected key '$.response.body.result_code'")
            else:
                order_token = jsonpath.jsonpath(response.json(), "$.response.body.biz_response.data.order_token")

        # 查询订单详情并获取礼品卡信息
        detail_endpoint = ""
        card_info = {
            "card_number": "",
            "amount": 0
        }
        detail_params = {
            "order_token": order_token
        }
        with self.client.get(url=detail_endpoint, headers=headers, params=detail_params,
                             name='order_detail'.upper(), catch_response=True) as response:
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

        # 使用 微信+礼品卡支付
        qrcode_pay_endpoint = "/api/lpos/cashier/v1/order/{}/prepay/qrcode".format(order_token)
        qrcode_pay_body = {
            "amount": 1,
            "order_token": "4dc2f46728d9582dccbbe5e6cf7b1247",
            "sub_tender_type": 301,
            "scene_type": "MINI",
            "appid": "wx8d774503eebab558",
            "payer_uid": "ooBK95O85UIbY51fSHRou5HYxRuc",
            "combined_tender":
                {
                    "sub_tender_type": 801,
                    "showModalStatus": True,
                    "amount": 100000,
                    "redeem_cards":
                        [
                            {
                                "card_number": "20013903143",
                                "amount": 100000
                            }
                        ],
                    "isClick": True
                }
        }
        with self.client.post(url=qrcode_pay_endpoint, headers=headers, json=qrcode_pay_body,
                              name='WxCardsPay'.upper(), catch_response=True) as response:
            if response.status_code != 200:
                print(response.status_code)
                # 手动将请求标记为fail
                response.failure(response.text)
