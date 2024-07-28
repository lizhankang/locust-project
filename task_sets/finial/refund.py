import os
import queue
import sys
import time

import requests
from tqdm import tqdm
import urllib3

from common.auth_utils import AuthUtils
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


dev_info = {
    "brand_code": "1024",
    "store_sn": "LPK001"
}
prod_info = {
    "brand_code": "999888",
    "store_sn": "LPK001"
}


class RefundTaskSet(SequentialTaskSet):
    def on_start(self):
        self.__dict__['tender_sn'] = self.user.__dict__['tender_sn']
        self.__dict__['environ'] = self.user.environment.parsed_options.env
        self.__dict__['info'] = dev_info if self.__dict__['environ'] != 'prod' else prod_info
        self.__dict__['endpoint'] = "/api/lite-pos/v1/sales/refund"
        self.__dict__['num_users'] = self.user.environment.parsed_options.num_users

    @task
    def task1(self):
        endpoint = "/api/lite-pos/v1/sales/refund"
        headers = {
            "Content-Type": "application/json",
        }
        check_sn = sales_sn = request_id = AuthUtils.random_num_str(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": self.__dict__['info']['brand_code'],
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": -1,
            "currency": "156",
            "industry_code": "0",
            "check_sn": f"Refund {self.__dict__['num_users']}并发测试-" + check_sn,
            "sales_sn": f"Refund {self.__dict__['num_users']}并发测试-" + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the purchase order",
            "description": "Description of purchase order",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "tenders": [
                {
                    "transaction_sn": AuthUtils.random_num_str(10),
                    "pay_status": 0,
                    "amount": -1,
                    # "original_tender_source": "0",
                    # "operation": "9",
                    "original_tender_sn": self.__dict__['tender_sn']
                }
            ]
        }
        sign_t_start = time.time()
        body = AuthUtils(self.__dict__['environ']).signature(biz_body)
        sign_t_end = time.time()
        with self.client.post(url=endpoint, headers=headers, json=body,
                              name='refund'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'计算签名值耗时：{(sign_t_end - sign_t_start) * 1000} ms')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'请求耗时: {response.request_meta["response_time"]}ms')
            print(f'[RESPONSE]: {response.text}')
        self.interrupt()


class RefundUser(HttpUser):
    tasks = [RefundTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__['tender_sn'] = self.environment.__dict__['tender_sn_q'].get()

    def on_stop(self):
        self.environment.__dict__['tender_sn_q'].put(self.__dict__['tender_sn'])


def prepare_pay_order(environ, num_users):
    data_info = {
        "brand_code": "1024" if environ != "prod" else "999888",
        "store_sn": "LPK001" if environ != "prod" else "LPK001",
        "client_member_sn": "lip-p-David" if environ != "prod" else "lip-p-Tara",
        "card_number": "20014057378" if environ != "prod" else "20016967109",
    }
    tenders_sns = []
    for _ in tqdm(range(num_users), desc="数据准备中,请稍后....."):
        user_token_domain = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
        user_token_url = user_token_domain + "/api/wallet/v1/members/_get_user_token"
        user_token_headers = {"Content-Type": "application/json"}
        user_info = {
            "brand_code": data_info['brand_code'],
            'client_member_sn': data_info['client_member_sn'],
        }
        user_token_resp = requests.post(user_token_url, headers=user_token_headers, json=AuthUtils(environ).signature(user_info), verify=False).json()
        print(f'user_token_resp: {user_token_resp}')
        user_token = user_token_resp['response']['body']['biz_response']['data']['user_token']

        auth_code_domain = "https://pro-customer-gateway.iwosai.com" if environ != 'prod' else "https://ums.shouqianba.com"
        auth_code_url = auth_code_domain + "/wallet/v1/authcode/getmycode"
        auth_code_headers = {"Content-Type": "application/json;charset=utf-8", "Authorization": user_token}
        auth_code_body = {"preferred_class": "GIFT_CARD", "preferred_refer_id": data_info['card_number']}
        auth_code_resp = requests.post(auth_code_url, headers=auth_code_headers, json=auth_code_body, verify=False).json()
        print(f'auth_code_resp: {auth_code_resp}')
        auth_code = auth_code_resp['data']['auth_code']

        ipay_domain = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
        ipay_url = ipay_domain + '/api/lite-pos/v1/sales/ipay'
        ipay_headers = {
            "Content-Type": "application/json",
        }
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        ipay_body = {
                "request_id": request_id,
                "brand_code": data_info['brand_code'],
                "store_sn": "LPK001",
                "workstation_sn": "567",
                "amount": "3000",
                "scene_type": "1",
                "dynamic_id": auth_code,
                "currency": "156",
                "industry_code": "0",
                "check_sn": f'Refund-{num_users}-Performance' + check_sn,
                "sales_sn": f'Refund-{num_users}-Performance' + sales_sn,
                "sales_time": AuthUtils.date_time(),
                "subject": f"For Refund {num_users} 并发测试",
                "description": "Description of Ipay order",
                "operator": "operator of order -> lip",
                "customer": "customer of order -> lip",
                "pos_info": "POS_INFO of the purchase order",
                "reflect": "Reflect of the purchase order",
            }
        print(f" ipay body: {ipay_body}")
        ipay_resp = requests.post(ipay_url, headers=ipay_headers, json=AuthUtils(environ).signature(ipay_body), verify=False).json()
        print(f'ipay_resp: {ipay_resp}')
        tender_sn = ipay_resp['response']['body']['biz_response']['data']['tender_sn']
        tenders_sns.append(tender_sn)

    return tenders_sns


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")


@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    environment.__dict__['tender_sn_q'] = queue.Queue()
    locust_environ = environment.parsed_options.env
    num_users = environment.parsed_options.num_users
    print(f'locust_environ: {locust_environ}; num_users: {num_users}')

    for sn in prepare_pay_order(locust_environ, num_users):
        environment.__dict__['tender_sn_q'].put(sn)
    print("-------------Locust环境初始化成功-----------👌👌👌👌👌")


if __name__ == '__main__':
    num = 3
    environ = os.getenv("ENVIRONMENT", "dev")
    # environ = "prod"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {num} --env={environ}"
                   f" --expect-workers {int(num / 6) + 1} --spawn-rate 6")
    os.system(command_str)
