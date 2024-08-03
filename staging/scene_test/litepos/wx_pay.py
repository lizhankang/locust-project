import csv
import os
import random
import sys
import queue

import jsonpath
import requests
from tqdm import tqdm

from common.auth_utils import AuthUtils
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events, LoadTestShape

dev_info = {
    "host": "https://vip-apigateway.iwosai.com",
    "brand_code": "1024",
    "store_sn": "LPK001",
    "member_sn": "lip-vip"
}
prod_info = {
    "host": "https://vapi.shouqianba.com",
    "brand_code": "999888",
    "store_sn": "LPK001",
    "member_sn": "lip-vip"
}


class WxPayTaskSet(SequentialTaskSet):

    def on_start(self):
        self.__dict__['auth_utils'] = self.user.__dict__['auth_utils']
        self.__dict__['info'] = dev_info if self.__dict__['auth_utils'].environment != 'prod' else prod_info
        self.__dict__['order_token'] = None
        print(self.__dict__['auth_utils'])
        print(self.__dict__['auth_utils'].environment)

    @task
    def purchase_task(self):
        endpoint = "/api/lite-pos/v1/sales/purchase"
        headers = {"Content-Type": "application/json"}
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        body = {
            "request_id": request_id,
            "brand_code": self.__dict__['info'].get('brand_code'),
            "store_sn": self.__dict__['info'].get('store_sn'),
            "workstation_sn": "567",
            "amount": "1",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "并发测试 - " + check_sn,
            "sales_sn": "并发测试 - " + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the purchase performance order",
            "description": "Description of 100 个并发，持续240s 并发测试",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "enable_sub_tender_types1": "301",
            "expired_at": AuthUtils.date_time(minutes=15),
            "crm_account_option": {
                "app_type": 5,
                "member_sn": self.__dict__['info'].get('member_sn')
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        with self.client.post(url=endpoint, headers=headers, json=self.__dict__['auth_utils'].signature(body),
                              name='purchase'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            # print(f'计算签名值耗时：{(sign_t_end - sign_t_start) * 1000} ms')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'请求耗时: {response.request_meta["response_time"]}ms')
            print(f'[RESPONSE]: {response.text}')
            self.__dict__['order_token'] = jsonpath.jsonpath(response.json(),
                                                             '$.response.body.biz_response.data.order_token')[0]

    @task
    def order_detail_task(self):
        endpoint = "/api/lpos/cashier/v2/cashier"
        headers = {
            "Content-Type": "application/json",
        }
        params = {
            "order_token": self.__dict__['order_token']
        }

        with self.client.get(url=endpoint, headers=headers, params=params,
                             name='order_detail'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[RESPONSE]: {response.text}')

    @task
    def wx_pay_detail_task(self):
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


class WxPay(HttpUser):
    tasks = [WxPayTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__['auth_utils'] = self.environment.__dict__['auth_utils']


class StepLoadShape(LoadTestShape):
    step_duration = 60  # Each step lasts 60 seconds
    step_users = 20    # Add 10 users at each step
    total_steps = 5     # Number of steps

    def tick(self):
        run_time = self.get_run_time()
        print(f'run_time: {run_time}')
        current_step = run_time // self.step_duration
        if current_step > self.total_steps:
            return None
        user_count = self.step_users * (current_step + 1)
        return (user_count, self.step_users)


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")


@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    environment.__dict__['order_token_q'] = queue.Queue()

    envir = environment.parsed_options.env
    max_user_nums = environment.parsed_options.num_users

    auth_utils = AuthUtils(envir)
    environment.__dict__['auth_utils'] = auth_utils

    print(f'Locust_environ: {envir.upper()}; max_user_num: {max_user_nums} is ok , show time please')
    print("-------------Locust环境初始化成功-----------👌👌👌👌👌")


if __name__ == '__main__':
    max_user_num = 100
    # environ = os.getenv("ENVIRONMENT", "dev")
    environ = "prod"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --env={environ} --users {max_user_num}"
                   f" --expect-workers 10 --spawn-rate 10 -t 500")
    os.system(command_str)
