import logging
from json import JSONDecodeError

import jsonpath
from locust import task, tag, HttpUser, between

from common.api_utils import ApiUtils

env = ""


class WxPay(HttpUser):
    """
    收银台微信支付
    """
    # wait_time = between(3, 5)

    def on_start(self):
        self.__dict__['info'] = {
            "brand": "1024" if env != "prod" else "9998888",
            "amount": "1"
        }
        print(f"self.environment.runner.user_count: {self.environment.runner.user_count}")
        logging.info(f"self.environment.runner.user_count: {self.environment.runner.user_count}")

    @task
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
                              name='Purchase'.upper(), catch_response=True) as purchaser_response:
            print(f'[创建订单URL]: {purchaser_response.request.url}')
            print(f'[创建订单REQUEST]: {purchaser_response.request.body.decode("utf-8")}')
            print(f'[创建订单RESPONSE]: {purchaser_response.text}')
            if purchaser_response.status_code != 200:
                print(purchaser_response.status_code)
                # 手动将请求标记为fail
                purchaser_response.failure(purchaser_response.text)
            try:
                if purchaser_response.json()["response"]["body"]["result_code"] != "200":
                    purchaser_response.failure("Did not get expected value in '$.response.body.result_code'")
            except JSONDecodeError:
                purchaser_response.failure("Response could not be decoded as JSON")
            except KeyError:
                purchaser_response.failure("Response did not contain expected key '$.response.body.result_code'")
            else:
                order_token = jsonpath.jsonpath(purchaser_response.json(), "$.response.body.biz_response.data.order_token")[0]

        # 查询订单详情
        detail_endpoint = "/api/lpos/cashier/v2/cashier"
        detail_params = {
            "order_token": order_token
        }
        with self.client.get(url=detail_endpoint, headers=headers, params=detail_params,
                             name='Order_Detail'.upper(), catch_response=True) as cashier_response:
            print(f'[查询订单详情URL]: {cashier_response.request.url}')
            print(f'[查询订单详情RESPONSE]: {cashier_response.text}')

        # 使用微信支付
        formate_t = "/api/lpos/cashier/v1/order/{}/pay/qrcode"
        qrcode_pay_endpoint = formate_t.format(order_token)
        qrcode_pay_body = {
            "amount": self.__dict__.get('info').get('amount'),
            "order_token": order_token,
            "sub_tender_type": 301,
            "scene_type": "MINI",
            "appid": "wx8d774503eebab558",
            "payer_uid": "ooBK95O85UIbY51fSHRou5HYxRuc"
        }
        with self.client.post(url=qrcode_pay_endpoint, headers=headers, json=qrcode_pay_body,
                              name='WxPay'.upper(), catch_response=True) as pay_response:
            print(f'[使用微信支付URL]: {pay_response.request.url}')
            print(f'[使用微信支付REQUEST]: {pay_response.request.body.decode("utf-8")}')
            print(f'[使用微信支付RESPONSE]: {pay_response.text}')
            if pay_response.status_code != 200:
                print(pay_response.status_code)
                # 手动将请求标记为fail
                pay_response.failure(pay_response.text)

    def on_stop(self):
        pass
