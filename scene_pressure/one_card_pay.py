from json import JSONDecodeError

import jsonpath
from locust import task, tag, HttpUser

from common.api_utils import ApiUtils

env = ""


class OneCardPay(HttpUser):
    """
    收银台使用单张礼品卡支付
    """

    def on_start(self) -> None:
        # 是否新建一个钱包用户并绑卡？
        self.__dict__['info'] = {
            "brand": "1024" if env != "prod" else "9998888",
            "amount": 1,
            "headers": {
                "Content-Type": "application/json",
            }
        }

    @task
    @tag("one_card_pay")
    def test_task1(self):
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
        body = ApiUtils(env).signed_body(purchase_body)
        order_token = ""
        with self.client.post(url=purchase_endpoint, headers=self.__dict__.get("info").get("headers"), json=body,
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

        # 查询订单详情
        detail_endpoint = ""
        params = {
            "order_token": order_token
        }
        with self.client.get(url=detail_endpoint, headers=self.__dict__.get("info").get("headers"), params=params,
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

        # 选卡支付
        card_pay_endpoint = "/api/lpos/cashier/v1/order/{}/pay/card".format(order_token)
        pay_body = {
            "scene_type": "MINI",
            "sub_tender_type": 801,
            "payer_uid": 6652,
            "showModalStatus": True,
            "amount": self.__dict__.get('info').get('amount'),
            "redeem_cards":
                [
                    {
                        "card_number": "",
                        "amount": self.__dict__.get('info').get('amount')
                    }
                ],
            "isClick": True
        }
        with self.client.post(url=card_pay_endpoint, headers=self.__dict__.get("info").get("headers"), json=pay_body,
                              name='card_pay'.upper(), catch_response=True) as response:
            if response.status_code != 200:
                print(response.status_code)
                # 手动将请求标记为fail
                response.failure(response.text)

    def on_stop(self) -> None:
        pass
