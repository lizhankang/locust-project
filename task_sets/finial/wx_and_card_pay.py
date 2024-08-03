import csv
import json
import os
import queue
import random
import time

import jsonpath
import requests
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events
from tqdm import tqdm

from common.auth_utils import AuthUtils

dev_info = {
    "host": "https://vip-apigateway.iwosai.com",
    "brand_code": "1024",
    "store_sn": "LPK001",
    }
prod_info = {
    "host": "https://vapi.shouqianba.com",
    "brand_code": "999888",
    "store_sn": "LPK001",
}


class WxAndCardPayTaskSet(SequentialTaskSet):
    def on_start(self):

        self.__dict__['environ'] = self.user.environment.parsed_options.env
        self.__dict__['info'] = dev_info if self.__dict__['environ'] != 'prod' else prod_info
        self.__dict__['member_info'] = self.user.__dict__['datainfo'][1]
        self.__dict__['order_token'] = self.user.__dict__['datainfo'][0]

    @task
    def qrcode_pay(self):
        endpoint = "/api/lpos/cashier/v1/order/" + self.__dict__['order_token'] + "/pay/qrcode"
        headers = {"Content-Type": "application/json"}
        body = {
            "amount": 1,
            "order_token": self.__dict__['order_token'],
            "sub_tender_type": 301,
            "scene_type": "MINI",
            "appid": "wx8d774503eebab558",
            "payer_uid": self.__dict__['member_info']['member_sn'],
            "combined_tender": {"sub_tender_type": 801, "amount": 1,
                                "redeem_cards": []}
        }
        redeem_cards = []
        for card_number in self.__dict__['member_info']['card_numbers']:
            redeem_cards.append({"card_number": card_number, "amount": 1})

        body['combined_tender']['redeem_cards'] = redeem_cards
        body['combined_tender']['amount'] = len(redeem_cards)

        print(f'请求体: {json.dumps(body)}')

        with self.client.post(url=endpoint, headers=headers, json=body, params=None,
                              name='WxPay'.upper(), catch_response=True) as pay_response:
            print(f'[wx+card pay URL]: {pay_response.request.url}')
            print(f'[wx+card pay REQUEST]: {pay_response.request.body.decode("utf-8")}')
            print(f'[wx+card pay RESPONSE]: {pay_response.text}')
        self.interrupt()


class WxAndCardPayUser(HttpUser):
    tasks = [WxAndCardPayTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__['datainfo'] = self.environment.__dict__['datainfo_q'].get()


def query_card_numbers(member_sn, card_num, environment="dev"):

    info = dev_info if environment != "prod" else prod_info
    url = info["host"] + "/api/wallet/v1/giftcard/members/cards/list"
    headers = {"Content-Type": "application/json"}
    biz_body = {
        "brand_code": info["brand_code"],
        "client_member_sn": member_sn,
        "statuses_filter": [2, 3],
        "gift_filter": 0,
        "balance_filter1": 1,
        "page_size": 50,
        "page1": 2,

    }
    body = AuthUtils(environment).signature(biz_body)
    response = requests.post(url=url, headers=headers, json=body)
    # print(response.request.url)
    # print(response.request.body)
    # print(response.text)
    cards_list = jsonpath.jsonpath(response.json(), "$.response.body.biz_response.data.cards")[0]
    cards = random.sample(cards_list, int(card_num))
    cards_number = list(map(lambda card: card['card_number'], cards))
    return cards_number


def prepare_wallet_users(environment, number):
    client_member_sns = []
    dev_member_file_path = "/Users/lizhankang/workSpace/selfProject/pythonProject/it-is-useful/shouqianba/src/main/test/wallet/wallet_sn_2024-07-04T17:35:16+08:00.csv"
    prod_member_file_path = "/Users/lizhankang/workSpace/selfProject/pythonProject/it-is-useful/shouqianba/src/main/test/wallet/wallet_sn_2024-07-04T17:35:16+08:00.csv"
    client_member_sn_path = dev_member_file_path if environment != 'prod' else prod_member_file_path
    with open(client_member_sn_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            client_member_sns.append(row['client_member_id'])

    member_sns = random.sample(client_member_sns, int(number))
    print(member_sns)

    # 使用多少张卡?
    card_number = 1

    member_infos = []
    for member_sn in member_sns:
        card_numbers = query_card_numbers(member_sn, card_number, environment=environment)
        member_infos.append({"card_numbers": card_numbers, "member_sn": member_sn})

    order_tokens = prepare_order_tokens(environment, member_sns)

    print(f'member_infos: {member_infos}')
    # combined_list = [pair for i in range(len(member_infos)) for pair in zip([member_infos[i]], [order_tokens[i]])]
    combined_list = []
    for e in zip(order_tokens, member_infos):
        combined_list.append(e)

    # print(combined_list)
    return combined_list


def prepare_order_tokens(environment, member_sns):
    print(f'member_infos: {member_sns}')
    order_tokens = []
    info = dev_info if environment != "prod" else prod_info
    url = info["host"] + "/api/lite-pos/v1/sales/purchase"
    headers = {"Content-Type": "application/json"}
    for member_sn in member_sns:
        print(member_sn)
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        body = {
            "request_id": request_id,
            "brand_code": info.get('brand_code'),
            "store_sn": info.get('store_sn'),
            "workstation_sn": "567",
            "amount": "30000",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "Order_Detail - " + check_sn,
            "sales_sn": "Order_Detail - " + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the Order_Detail Performance ",
            "description": f"For Order_Detail Performance {len(member_sns)} 并发测试",
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
        response = requests.post(url, headers=headers, json=AuthUtils(environment).signature(body))
        print(response.request.url)
        print(response.request.body)
        print(response.text)
        if response.status_code == 200:
            order_tokens.append(response.json()['response']['body']['biz_response']['data']['order_token'])

    return order_tokens


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

    environment.__dict__['datainfo_q'] = queue.Queue()
    combined_list = prepare_wallet_users(locust_environ, num_users)
    for datainfo in tqdm(combined_list, desc="数据准备中,请稍后..."):
        environment.__dict__['datainfo_q'].put(datainfo)

    print("-------------Locust环境初始化成功-------👌👌👌👌👌")


if __name__ == '__main__':
    num = 2
    environ = os.getenv("ENVIRONMENT", "dev")
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {num} --env={environ}"
                   f" --expect-workers {int(num / 6) + 1} --spawn-rate 6")
    os.system(command_str)
