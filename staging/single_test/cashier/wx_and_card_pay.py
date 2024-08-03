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


class WxAndCardPayTaskSet(SequentialTaskSet):
    def on_start(self):
        self.__dict__['auth_utils'] = self.user.__dict__.get("auth_utils")
        self.__dict__['datainfo'] = self.user.__dict__.get('datainfo')
        self.__dict__['environment'] = self.__dict__.get("auth_utils").environment

    @task
    def qrcode_pay(self):
        endpoint = "/api/lpos/cashier/v1/order/" + self.__dict__['datainfo']['order_token'] + "/pay/qrcode"
        body = {
            "amount": 1,
            "order_token": self.__dict__['datainfo']['order_token'],
            "sub_tender_type": 301,
            "scene_type": "MINI",
            "appid": "wx8d774503eebab558",
            # "payer_uid": self.__dict__['datainfo']['payer_uid'],
            "payer_uid": "ooBK95O85UIbY51fSHRou5HYxRuc",
            "combined_tender": {"sub_tender_type": 801, "amount": 1,
                                "redeem_cards": []}
        }

        redeem_cards = []
        amount = 0
        for card_number in self.__dict__['datainfo']['cards']:
            redeem_cards.append({"card_number": card_number, "amount": 1})
            amount += 1

        body['combined_tender']['redeem_cards'] = redeem_cards
        body['combined_tender']['amount'] = amount

        with self.client.post(endpoint, json=body, catch_response=True) as response:
            if response.status_code == 200:
                print(f'[ QRCode Pay URL ]: {response.request.url}')
                print(f'[ QRCode Pay REQUEST ]: {response.request.body.decode("utf-8")}')
                print(f'请求耗时: {response.request_meta["response_time"]}ms')
                print(f'[ QRCode Pay RESPONSE ]: {response.text}')
        self.interrupt()


class WxAndCardPayUser(HttpUser):
    tasks = [WxAndCardPayTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__['auth_utils'] = self.environment.__dict__['auth_utils']
        self.__dict__["datainfo"] = self.environment.__dict__['datainfo_q'].get()
        print(self.__dict__["datainfo"])


class StepLoadShape(LoadTestShape):
    step_duration = 90  # Each step lasts 60 seconds
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
    datainfo_s = []
    # 查会员
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
    purchase_url = req_info.get('host') + "/api/lite-pos/v1/sales/purchase"
    cashier_url = req_info.get('host') + "/api/lpos/cashier/v2/cashier"
    headers = {"Content-Type": "application/json"}

    for member_sn in tqdm(member_sns, desc="数据准备中.."):
        datainfo = {}
        datainfo['payer'] = member_sn
        card_numbers = query_card_numbers(member_sn, card_number, auth_utils=auth_utils)
        datainfo['cards'] = card_numbers

        check_sn = sales_sn = request_id = auth_utils.unique_random(10)
        purchase_body = {
            "request_id": request_id,
            "brand_code": req_info.get('brand_code'),
            "store_sn": req_info.get('store_sn'),
            "workstation_sn": "567",
            "amount": "30000",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "Single WX+Card Pay P- " + check_sn,
            "sales_sn": "Single WX+Card Pay P- " + sales_sn,
            "sales_time": auth_utils.date_time(),
            "subject": "Subject of the WX+Card performance order",
            "description": "Description of WX+Card单接口并发测试",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the WX+Card order",
            "reflect": "Reflect of the WX+Card order",
            "enable_sub_tender_types1": "301",
            "expired_at": auth_utils.date_time(minutes=5),
            "crm_account_option": {
                "app_type": 5,
                "member_sn": member_sn
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        body = auth_utils.signature(purchase_body)
        response = requests.post(url=purchase_url, headers=headers, json=body)
        if response.status_code == 200:
            print(f'[ purchase Pay URL ]: {response.request.url}')
            print(f'[ purchase Pay URL ]: {response.request.body}')
            print(f'[ purchase Pay URL ]: {response.text}')
            try:
                order_token = jsonpath.jsonpath(response.json(), "$.response.body.biz_response.data.order_token")
                datainfo['order_token'] = order_token[0]
            except KeyError:
                print(response.text)
                sys.exit(f'error: {response.text}')

        # 获取lite member id
        params = {
            "order_token": datainfo['order_token']
        }
        response = requests.get(url=cashier_url, headers=headers, params=params)
        if response.status_code == 200:
            try:
                resp = response.json()
                payer_uid = resp['biz_response']['data']['member_privileges']['lite_member_id']
            except Exception as e:
                print(response.text)
                sys.exit(f'error: {e}')
            else:
                datainfo['payer_uid'] = payer_uid
        else:
            print(response.text)
            sys.exit(f'error: {response.text}')

        datainfo_s.append(datainfo)

    return datainfo_s


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")


@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    environ = environment.parsed_options.env
    max_user_num = environment.parsed_options.num_users
    environment.__dict__['datainfo_q'] = queue.Queue()

    auth_utils = AuthUtils(environ)
    environment.__dict__['auth_utils'] = auth_utils

    datainfo_s = prepare_datainfo(max_user_num, auth_utils)
    print(datainfo_s)
    for datainfo in datainfo_s:
        environment.__dict__['datainfo_q'].put(datainfo)

    print(f'locust_environ: {environ}; max_user_num: {max_user_num}')
    print("-------------Locust环境初始化成功-----------👌👌👌👌👌")


if __name__ == '__main__':
    max_user_num = 30
    # environ = os.getenv("ENVIRONMENT", "dev")
    environ = "prod"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --env={environ} --users {max_user_num}"
                   f" --expect-workers 10 --spawn-rate 10 -t 500")
    os.system(command_str)
