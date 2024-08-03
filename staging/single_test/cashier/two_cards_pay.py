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
        "store_sn": "LPK001"
    }
prod_info = {
    "host": "https://vapi.shouqianba.com",
    "brand_code": "999888",
    "store_sn": "LPK001"
}


class CardPayTaskSet(SequentialTaskSet):
    def on_start(self):
        self.__dict__['datainfo'] = self.user.__dict__.get('datainfo')
        self.__dict__['auth_utils'] = self.user.environment.__dict__.get('auth_utils')

    @task
    def card_pay(self):
        endpoint = "/api/lpos/cashier/v1/order/{}/pay/card".format(self.__dict__['datainfo'].get('order_token'))
        redeem_cards = []
        amount = 0
        for card_number in self.__dict__['datainfo']['card_numbers']:
            redeem_cards.append({'card_number': card_number, "amount": 1})
            amount = amount + 1
        body = {"scene_type": "MINI", "sub_tender_type": 801, "payer_uid": self.__dict__['datainfo'].get('payer_uid'),
                "showModalStatus": True, "amount": amount, "redeem_cards": redeem_cards, "isClick": True}
        with self.client.post(endpoint, json=body, catch_response=True) as response:
            if response.status_code == 200:
                print(f'[ Card Pay URL ]: {response.request.url}')
                print(f'[ Card Pay REQUEST ]: {response.request.body.decode("utf-8")}')
                print(f'请求耗时: {response.request_meta["response_time"]}ms')
                print(f'[ Card Pay RESPONSE ]: {response.text}')


class CardPayUser(HttpUser):
    tasks = [CardPayTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__["datainfo"] = self.environment.__dict__['datainfo_q'].get()
        print(self.__dict__["datainfo"])


class StepLoadShape(LoadTestShape):
    step_duration = 30  # Each step lasts 60 seconds
    step_users = 10     # Add 10 users at each step
    total_steps = 5     # Number of steps

    def tick(self):
        run_time = self.get_run_time()
        print(f'run_time: {run_time}')
        current_step = run_time // self.step_duration
        if current_step > self.total_steps:
            return None
        user_count = self.step_users * (current_step + 1)
        return (user_count, self.step_users)


def query_card_numbers(member_sn, card_num=1, auth_utils=AuthUtils('dev')):
    info = dev_info if auth_utils.environment != "prod" else prod_info
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
    body = auth_utils.signature(biz_body)
    response = requests.post(url=url, headers=headers, json=body)
    try:
        cards_list = jsonpath.jsonpath(response.json(), "$.response.body.biz_response.data.cards")[0]
    except Exception as e:
        print(response.text)
        sys.exit(f'error: {e}')
    cards = random.sample(cards_list, int(card_num))
    cards_numbers = list(map(lambda card: card['card_number'], cards))
    return cards_numbers


def prepare_datainfo(max_user_nums, auth_utils):
    req_info = dev_info if auth_utils.environment != "prod" else prod_info
    # 准备 会员
    client_member_sns = []
    dev_member_file_path = "/Users/lizhankang/workSpace/selfProject/pythonProject/it-is-useful/shouqianba/src/main/test/wallet/wallet_sn_2024-07-04T17:35:16+08:00.csv"
    prod_member_file_path = "/Users/lizhankang/workSpace/selfProject/pythonProject/it-is-useful/shouqianba/src/main/test/wallet/wallet_sn_2024-07-04T17:35:16+08:00.csv"
    client_member_sn_path = dev_member_file_path if auth_utils.environment != 'prod' else prod_member_file_path
    with open(client_member_sn_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            client_member_sns.append(row['client_member_id'])

    member_sns = random.sample(client_member_sns * (int(max_user_nums / 100) + 1), int(max_user_nums))

    # 为会员准备用于核销礼品卡?
    card_number = 2
    member_infos = []
    for member_sn in member_sns:
        card_numbers = query_card_numbers(member_sn, card_number, auth_utils=auth_utils)
        member_infos.append({"card_numbers": card_numbers, "member_sn": member_sn})

    datainfo_s = []
    purchase_url = req_info.get('host') + "/api/lite-pos/v1/sales/purchase"
    cashier_url = req_info.get('host') + "/api/lpos/cashier/v2/cashier"
    headers = {"Content-Type": "application/json"}
    for member_info in member_infos:
        # 循环调用 purchase接口,获取 order_token
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
            "check_sn": "For Card Pay P - " + check_sn,
            "sales_sn": "For Card Pay P - " + sales_sn,
            "sales_time": auth_utils.date_time(),
            "subject": "Subject of the purchase performance order",
            "description": "Description of 25个并发，持续240s 并发测试",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "enable_sub_tender_types1": "301",
            "expired_at": auth_utils.date_time(minutes=5),
            "crm_account_option": {
                "app_type": 5,
                "member_sn": member_info.get('member_sn')
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        body = auth_utils.signature(purchase_body)
        response = requests.post(url=purchase_url, headers=headers, json=body)
        if response.status_code == 200:
            try:
                member_info['order_token'] = response.json()['response']['body']['biz_response']['data']['order_token']
            except KeyError:
                print(response.text)

        # 获取 lite_member_id
        params = {
            "order_token": member_info['order_token']
        }
        payer_uid = requests.get(url=cashier_url, headers=headers, params=params).json()['biz_response']['data'][
            'member_privileges']['lite_member_id']
        member_info['payer_uid'] = payer_uid
        datainfo_s.append(member_info)

    return datainfo_s


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
    max_user_nums = environment.parsed_options.num_users
    environment.__dict__['auth_utils'] = auth_utils
    environment.__dict__['datainfo_q'] = queue.Queue()
    datainfo_s = prepare_datainfo(max_user_nums, auth_utils)
    for datainfo in datainfo_s:
        environment.__dict__['datainfo_q'].put(datainfo)

    print("-------------Locust环境初始化成功-----------👌👌👌👌👌")


if __name__ == '__main__':
    max_user_nums = 30
    environ = "dev"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {max_user_nums} --env={environ}"
                   f" --expect-workers {int(max_user_nums / 6) + 1} --spawn-rate 6")
    os.system(command_str)