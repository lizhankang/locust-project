import csv
import os
import random
import sys
import queue
import requests

from common.auth_utils import AuthUtils
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events


class OrderDetailTaskSet(SequentialTaskSet):
    def on_start(self):
        self.__dict__['order_token'] = self.user.__dict__['order_token']
        self.__dict__['environ'] = self.user.environment.parsed_options.env

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
        self.interrupt()


class OrderDetailUser(HttpUser):
    tasks = [OrderDetailTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__['order_token'] = self.environment.__dict__['order_token_q'].get()

    def on_stop(self):
        self.environment.__dict__['order_token_q'].put(self.__dict__['order_token'])


def prepare_order_token(task_environ, num_users):
    dev_info = {
        "brand_code": "1024",
        "store_sn": "litepos",
        "member_sn": "lip-vip"
    }
    prod_info = {
        "brand_code": "999888",
        "store_sn": "LPK001",
        "member_sn": "lip-vip"
    }
    order_tokens = []
    domain = "https://vip-apigateway.iwosai.com" if task_environ != "prod" else "https://vapi.shouqianba.com"
    url = domain + "/api/lite-pos/v1/sales/purchase"
    data_info = dev_info if task_environ != "prod" else prod_info
    headers = {
        "Content-Type": "application/json",
    }

    # 准备会员
    client_member_sns = []
    client_member_sn_path = "/Users/lizhankang/workSpace/selfProject/pythonProject/it-is-useful/shouqianba/src/main/test/wallet/wallet_sn_2024-07-04T17:35:16+08:00.csv"
    with open(client_member_sn_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            client_member_sns.append(row['client_member_id'])

    member_sns = random.sample(client_member_sns, num_users)
    for member_sn in member_sns:
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        body = {
            "request_id": request_id,
            "brand_code": data_info.get('brand_code'),
            "store_sn": data_info.get('brand_code'),
            "workstation_sn": "567",
            "amount": "30000",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "Order_Detail - " + check_sn,
            "sales_sn": "Order_Detail - " + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the Order_Detail Performance ",
            "description": f"For Order_Detail Performance {num_users} 并发测试",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "expired_at": AuthUtils.date_time(minutes=5),
            "crm_account_option": {
                "app_type": 5,
                "member_sn": member_sn
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        response = requests.post(url, headers=headers, json=AuthUtils(task_environ).signature(body))
        print(response.text)
        if response.status_code == 200:
            order_tokens.append(response.json()['response']['body']['biz_response']['data']['order_token'])

    if len(order_tokens) != num_users:
        sys.exit(f'总共有 {num_users} 名用户，但是只准备了 {len(order_tokens)} 条数据。程序退出！！！！🚫🚫🚫🚫🚫')
    else:
        print(f'总共有 {num_users} 名用户，准备了 {len(order_tokens)} 条数据。【 数据准备完成 👌👌👌👌👌】')
    return order_tokens


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")


@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    environment.__dict__['order_token_q'] = queue.Queue()
    locust_environ = environment.parsed_options.env
    num_users = environment.parsed_options.num_users
    print(f'locust_environ: {locust_environ}; num_users: {num_users}')

    for sn in prepare_order_token(locust_environ, num_users):
        environment.__dict__['order_token_q'].put(sn)
    print("-------------Locust环境初始化成功-----------👌👌👌👌👌")


if __name__ == '__main__':
    num = 8
    # environ = os.getenv("ENVIRONMENT", "dev")
    environ = "dev"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {num} --env={environ}"
                   f" --expect-workers {int(num / 5)} --spawn-rate 5 -t 240")
    os.system(command_str)
