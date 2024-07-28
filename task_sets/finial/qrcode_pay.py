import os
import queue
import sys
import time

import jsonpath
import requests
from tqdm import tqdm
import urllib3

from common.auth_utils import AuthUtils
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

dev_info = {
        "host": "https://vip-apigateway.iwosai.com",
        "brand_code": "1024",
        "store_sn": "LPK001"
    }
prod_info = {
    "host": "https://vapi.shouqianba.com",
    "brand_code": "999888",
    "store_sn": "LPK001"
}


class QRCodePayTaskSet(SequentialTaskSet):
    def on_start(self):
        self.__dict__['auth_utils'] = self.user.__dict__.get("auth_utils")
        self.__dict__['order_token'] = self.user.__dict__.get('order_token')
        self.__dict__['environment'] = self.__dict__.get("auth_utils").environment

    @task
    def qrcode_pay(self):
        endpoint = "/api/lpos/cashier/v1/order/{}/pay/qrcode".format(self.__dict__.get('order_token'))
        body = {"amount": 1, "order_token": self.__dict__.get('order_token'), "sub_tender_type": 301,
                    "scene_type": "MINI", "appid": "wx8d774503eebab558", "payer_uid": "ooBK95O85UIbY51fSHRou5HYxRuc",
                    }
        with self.client.post(endpoint, json=body, catch_response=True) as response:
            if response.status_code == 200:
                print(f'[ QRCode Pay URL ]: {response.request.url}')
                print(f'[ QRCode Pay REQUEST ]: {response.request.body.decode("utf-8")}')
                print(f'请求耗时: {response.request_meta["response_time"]}ms')
                print(f'[ QRCode Pay RESPONSE ]: {response.text}')
        self.interrupt()


class QRCodePayUser(HttpUser):
    tasks = [QRCodePayTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__['order_token'] = self.environment.__dict__['order_token_q'].get()
        print(f'QRCodePayUser order_token : {self.__dict__["order_token"]}')
        self.__dict__['auth_utils'] = self.environment.__dict__['auth_utils']


def prepare_pay_order(user_nums, auth_utils=AuthUtils("dev")):
    print(f'user_nums: {user_nums}')
    req_info = dev_info if auth_utils.environment != "prod" else prod_info
    purchase_url = req_info.get('host') + "/api/lite-pos/v1/sales/purchase"
    headers = {"Content-Type": "application/json"}
    order_tokens = []
    for _ in range(user_nums):
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        purchase_body = {
            "request_id": request_id,
            "brand_code": req_info.get('brand_code'),
            "store_sn": req_info.get('store_sn'),
            "workstation_sn": "567",
            "amount": "30000",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "For QRCode Pay P - " + check_sn,
            "sales_sn": "For QRCode Pay P - " + sales_sn,
            "sales_time": auth_utils.date_time(),
            "subject": "Subject of the QRCode performance order",
            "description": "Description of QRCode接口并发测试",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "enable_sub_tender_types1": "301",
            "expired_at": auth_utils.date_time(minutes=5),
        }
        body = auth_utils.signature(purchase_body)
        response = requests.post(url=purchase_url, headers=headers, json=body)
        if response.status_code == 200:
            print(f'[ purchase Pay URL ]: {response.request.url}')
            print(f'[ purchase Pay URL ]: {response.request.body}')
            print(f'[ purchase Pay URL ]: {response.text}')
            try:
                order_token = jsonpath.jsonpath(response.json(), "$.response.body.biz_response.data.order_token")
                order_tokens.append(order_token[0])
            except KeyError:
                print(response.text)

    return order_tokens


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")


@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    envir = environment.parsed_options.env
    auth_utils = AuthUtils(envir)
    user_nums = environment.parsed_options.num_users
    environment.__dict__['auth_utils'] = auth_utils
    environment.__dict__['order_token_q'] = queue.Queue()
    print(f'Locust Environ: {envir}; num_users: {user_nums}')

    for order_token in tqdm(prepare_pay_order(user_nums, auth_utils), desc="Data Preparing ... "):
        environment.__dict__['order_token_q'].put(order_token)
    print("-------------Locust环境初始化成功-----------👌👌👌👌👌")


if __name__ == '__main__':
    num = 2
    environ = os.getenv("ENVIRONMENT", "dev")
    # environ = "prod"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {num} --env={environ}"
                   f" --expect-workers {int(num / 6) + 1} --spawn-rate 6")
    os.system(command_str)
