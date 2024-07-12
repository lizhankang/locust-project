import csv
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
    "host": "https://vip-apigateway.iwosai.com",
    "brand_code": "999888",
    "store_sn": "LPK001",
}


class WxAndCardPayTaskSet(SequentialTaskSet):
    def on_start(self):
        # dev_info = {
        #     "brand_code": "1024",
        #     "store_sn": "LPK001",
        # }
        # prod_info = {
        #     "brand_code": "999888",
        #     "store_sn": "LPK001"
        # }
        self.__dict__['environ'] = self.user.environment.parsed_options.env
        self.__dict__['info'] = dev_info if self.__dict__['environ'] != 'prod' else prod_info
        self.__dict__['member_info'] = self.user.__dict__['member_info']
        self.__dict__['order_token'] = None
        self.__dict__['card_number'] = None
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
            "check_sn": "P-WxAndCardPay" + check_sn,
            "sales_sn": "P-WxAndCardPay" + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the WxAndCardPay ",
            "description": "Description of WxAndCardPay",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "enable_sub_tender_types1": "301",
            "expired_at": AuthUtils.date_time(minutes=5),
            "crm_account_option": {
                "app_type": 5,
                "member_sn": self.__dict__['member_info']['member_sn']
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
            print(f'[Purchase URL]: {response.request.url}')
            print(f'计算签名值耗时：{(sign_t_end - sign_t_start) * 1000} ms')
            print(f'[Purchase REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'请求耗时: {response.request_meta["response_time"]}ms')
            print(f'[Purchase RESPONSE]: {response.text}')
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
            print(f'[Order Detail URL]: {response.request.url}')
            print(f'[Order Detail RESPONSE]: {response.text}')
            # 选择一张卡
            giftcards = jsonpath.jsonpath(response.json(),
                                          '$.biz_response.data.member_privileges.giftcard_wallet.giftcards')[0]
            print(f'giftcards: {giftcards}')
            self.__dict__['card_number'] = random.choice(giftcards)['card_number']
            self.__dict__['payer_uid'] = \
            jsonpath.jsonpath(response.json(), "$.biz_response.data.member_privileges.lite_member_id")[0]

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
            "payer_uid": "ooBK95O85UIbY51fSHRou5HYxRuc",
            "combined_tender": {"sub_tender_type": 801, "amount": 1,
                                "redeem_cards": []}
        }

        redeem_cards = []
        for card_number in self.__dict__['member_info']['card_numbers']:
            redeem_cards.append({"card_number": card_number, "amount": 1})

        body['combined_tender']['redeem_cards'] = redeem_cards
        body['combined_tender']['amount'] = len(redeem_cards)

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
        self.__dict__['member_info'] = self.environment.__dict__['member_infos_q'].get()


def query_card_numbers(member_sn, card_num, environment="dev"):
    # dev_info = {
    #     "host": "https://vip-apigateway.iwosai.com",
    #     "brand_code": "1024"
    # }
    # prod_info = {
    #     "host": "https://vip-apigateway.iwosai.com",
    #     "brand_code": "999888"
    # }
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
    cards_list = jsonpath.jsonpath(response.json(), "$.response.body.biz_response.data.cards")[0]
    cards = random.sample(cards_list, int(card_num))
    cards_number = list(map(lambda card: card['card_number'], cards))
    return cards_number


def prepare_wallet_users(environment, number):
    client_member_sns = []
    dev_member_file_path = "/Users/lizhankang/workSpace/selfProject/pythonProject/it-is-useful/shouqianba/src/main/test/wallet/wallet_sn_2024-07-04T17:35:16+08:00.csv"
    prod_member_file_path = ""
    client_member_sn_path = dev_member_file_path if environment != 'prod' else prod_member_file_path
    with open(client_member_sn_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            client_member_sns.append(row['client_member_id'])

    member_sns = random.sample(client_member_sns, int(number))

    # 使用多少张卡?
    card_number = 1

    member_infos = []
    for member_sn in member_sns:
        card_numbers = query_card_numbers(member_sn, card_number, environment=environment)
        member_infos.append({"card_numbers": card_numbers, "member_sn": member_sn})

    print(f'member_infos: {member_infos}')

    return member_infos


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

    environment.__dict__['member_infos_q'] = queue.Queue()
    member_infos = prepare_wallet_users(locust_environ, num_users)
    for member_info in tqdm(member_infos, desc="数据准备中,请稍后..."):
        environment.__dict__['member_infos_q'].put(member_info)

    print("-------------Locust环境初始化成功-------👌👌👌👌👌")


if __name__ == '__main__':
    num = 2
    environ = os.getenv("ENVIRONMENT", "dev")
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {num} --env={environ}"
                   f" --expect-workers {int(num / 6) + 1} --spawn-rate 6")
    os.system(command_str)
