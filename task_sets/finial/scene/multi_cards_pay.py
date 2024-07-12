import csv
import os
import queue
import random
import time

import jsonpath
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events
from tqdm import tqdm

from common.auth_utils import AuthUtils


class MultiCardsPayTaskSet(SequentialTaskSet):
    def on_start(self):
        dev_info = {
            "brand_code": "1024",
            "store_sn": "LPK001",
        }
        prod_info = {
            "brand_code": "999888",
            "store_sn": "LPK001"
        }
        self.__dict__['environ'] = self.user.environment.parsed_options.env
        self.__dict__['info'] = dev_info if self.__dict__['environ'] != 'prod' else prod_info
        self.__dict__['member_sn'] = self.user.__dict__['member_sn']
        self.__dict__['order_token'] = None
        self.__dict__['card_numbers'] = []
        self.__dict__['payer_uid'] = None

    @task
    def purchase_task(self):
        endpoint = "/api/lite-pos/v1/sales/purchase"
        headers = {
            "Content-Type": "application/json",
        }
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": self.__dict__['info'].get('brand_code'),
            "store_sn": self.__dict__['info'].get('store_sn'),
            "workstation_sn": "567",
            "amount": "2",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "Multi card-" + check_sn,
            "sales_sn": "Multi card-" + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the purchase order - ",
            "description": "Description of purchase order",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "expired_at": AuthUtils.date_time(minutes=5),
            "crm_account_option": {
                "app_type": 5,
                "member_sn": self.__dict__['member_sn']
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        sign_t_start = time.time()
        body = AuthUtils(self.__dict__['environ']).signature(biz_body)
        sign_t_end = time.time()
        with self.client.post(url=endpoint, headers=headers, json=body,
                              name='purchase'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'计算签名值耗时：{(sign_t_end - sign_t_start) * 1000} ms')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'请求耗时: {response.request_meta["response_time"]}ms')
            print(f'[RESPONSE]: {response.text}')
            self.__dict__['order_token'] = jsonpath.jsonpath(response.json(), '$.response.body.biz_response.data.order_token')[0]
            print(f"self.__dict__['order_token']: {self.__dict__['order_token']}")

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
            print(f'[order_detail RESPONSE]: {response.json()}')
            # 选择2张卡
            giftcards = jsonpath.jsonpath(response.json(),
                                          '$.biz_response.data.member_privileges.giftcard_wallet.giftcards')[0]
            print(f'giftcards: {giftcards}')
            two_cards = random.sample(giftcards, 2)
            self.__dict__['card_numbers'] = list(map(lambda card: card['card_number'], two_cards))
            self.__dict__['payer_uid'] = jsonpath.jsonpath(response.json(), "$.biz_response.data.member_privileges.lite_member_id")[0]

    @task
    def card_pay_task(self):
        endpoint = "/api/lpos/cashier/v1/order/" + self.__dict__['order_token'] + "/pay/card"
        headers = {
            "Content-Type": "application/json",
        }
        body = {"scene_type": "MINI", "sub_tender_type": 801, "payer_uid": self.__dict__['payer_uid'], "showModalStatus": True,
                "amount": 2, "redeem_cards": [{"card_number": self.__dict__['card_numbers'][0], "amount": 1}, {"card_number": self.__dict__['card_numbers'][1], "amount": 1}], "isClick": True}
        with self.client.post(url=endpoint, headers=headers, json=body,
                              name='card_pay'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[RESPONSE]: {response.text}')
        self.interrupt()


class MultiCardPayUser(HttpUser):
    tasks = [MultiCardsPayTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__['member_sn'] = self.environment.__dict__['member_sn_q'].get()


def prepare_wallet_users(environment):
    client_member_sns = []
    dev_member_file_path = "/Users/lizhankang/workSpace/selfProject/pythonProject/it-is-useful/shouqianba/src/main/test/wallet/wallet_sn_2024-07-04T17:35:16+08:00.csv"
    prod_member_file_path = ""
    client_member_sn_path = dev_member_file_path if environment != 'prod' else prod_member_file_path
    with open(client_member_sn_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            client_member_sns.append(row['client_member_id'])

    return client_member_sns


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")


# 虚拟环境创建成功后执行
@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    locust_environ = environment.parsed_options.env
    num_users = environment.parsed_options.num_users

    environment.__dict__['member_sn_q'] = queue.Queue()
    client_member_sns = prepare_wallet_users(locust_environ)
    for i in tqdm(range(num_users), desc="数据准备中,请稍后..."):
        environment.__dict__['member_sn_q'].put(client_member_sns.pop())
    print("-------------Locust环境初始化成功-------")


if __name__ == '__main__':
    num = 2
    environ = os.getenv("ENVIRONMENT", "dev")
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {num} --env={environ}"
                   f" --expect-workers {int(num / 6) + 1} --spawn-rate 6")
    os.system(command_str)
