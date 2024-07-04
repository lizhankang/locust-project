import os
from json import JSONDecodeError

import jsonpath

from common.api_utils import ApiUtils
from locust import HttpUser, SequentialTaskSet, task, events
import locust.argument_parser


@events.init_command_line_parser.add_listener
def _(parser):
    # Choices will validate command line input and show a dropdown in the web UI
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Environment")


class WxPay(SequentialTaskSet):

    def on_start(self):
        self.envir = self.user.environment.parsed_options.env
        self.__dict__['info'] = {
            "brand": "1024" if self.envir != "prod" else "9998888",
            "amount": "11"
        }
        self.headers = {
            "Content-Type": "application/json",
        }
        self.order_token = None

        print(f'self.envir: {self.envir}')

    @task
    def purchase(self):
        endpoint = "/api/lite-pos/v1/sales/purchase"
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        body = {
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
        with self.client.post(endpoint, headers=self.headers,
                              json=ApiUtils(self.envir).signed_body(body), params=None, name="purchase") as response:
            print(f'[创建订单URL]: {response.request.url}')
            print(f'[创建订单REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[创建订单RESPONSE]: {response.text}')
            if response.status_code != 200:
                response.failure(response.text)
            try:
                resp = response.json()
                self.order_token = jsonpath.jsonpath(resp, '$..order_token')[0]
            except JSONDecodeError:
                response.failure(response.text)

    @task
    def order_detail(self):
        endpoint = "/api/lpos/cashier/v2/cashier"
        params = {
            "order_token": self.order_token
        }
        with self.client.get(url=endpoint, headers=self.headers, params=params, json=None,
                             name='Order_Detail'.upper(), catch_response=True) as cashier_response:
            print(f'[查询订单详情URL]: {cashier_response.request.url}')
            print(f'[查询订单详情RESPONSE]: {cashier_response.text}')

    @task
    def qrcode_pay(self):
        endpoint = "/api/lpos/cashier/v1/order/" + self.order_token +"/pay/qrcode"
        body = {
            "amount": self.__dict__.get('info').get('amount'),
            "order_token": self.order_token,
            "sub_tender_type": 301,
            "scene_type": "MINI",
            "appid": "wx8d774503eebab558",
            "payer_uid": "ooBK95O85UIbY51fSHRou5HYxRuc"
        }
        with self.client.post(url=endpoint, headers=self.headers, json=body, params=None,
                              name='WxPay'.upper(), catch_response=True) as pay_response:
            print(f'[使用微信支付URL]: {pay_response.request.url}')
            print(f'[使用微信支付REQUEST]: {pay_response.request.body.decode("utf-8")}')
            print(f'[使用微信支付RESPONSE]: {pay_response.text}')
        self.interrupt()


class WebsiteUser(HttpUser):
    tasks = [WxPay]

    def __init__(self, environment):
        super().__init__(environment)
        # self.order_token = None


if __name__ == '__main__':
    num = 10
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com"

    command_str = f"locust -f {file_name} --host={host} --users={num + 20} --spawn-rate 3 --expect-workers 20 --env=dev"
    os.system(command_str)
