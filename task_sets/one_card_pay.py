import os
from json import JSONDecodeError

import jsonpath

from common.api_utils import ApiUtils
from locust import HttpUser, SequentialTaskSet, task, events
from locust.env import Environment


class OneCardPayTaskSet(SequentialTaskSet):
    def on_start(self):
        self.envir = ""
        self.__dict__['info'] = {
            "brand": "1024" if self.envir != "prod" else "9998888",
            "amount": "11"
        }
        self.headers = {
            "Content-Type": "application/json",
        }
        self.order_token = None

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
        pass

    @task
    def card_pay(self):
        pass


class WebsiteUser(HttpUser):
    tasks = []

    def __init__(self, environment):
        super().__init__(environment)
        # self.order_token = None


if __name__ == '__main__':
    num = 10
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com"


    @events.init_command_line_parser.add_listener
    def _(parser):
        # Choices will validate command line input and show a dropdown in the web UI
        parser.add_argument("--env", choices=["dev", "staging", "prod"], default="dev", help="Environment")

    # 虚拟环境创建成功后执行
    @events.init.add_listener
    def on_locust_init(environment: Environment, **kwargs):
        # 准备钱包用户
        print("-------------Locust环境初始化成功-------")

    command_str = f"locust -f {file_name} --host={host} --users={num} --spawn-rate 3 --expect-workers 20 --env=dev"
    os.system(command_str)
