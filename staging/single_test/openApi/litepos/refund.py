import os
import queue
import sys
import time

import requests
from tqdm import tqdm
import urllib3

from common.auth_utils import AuthUtils
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, LoadTestShape, task, events

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

dev_info = {
    "host": "https://vip-apigateway.iwosai.com",
    "brand_code": "1024",
    "store_sn": "LPK001",
    "client_member_sn": "lip-p-David",
    "card_number": "20014057378"
}
prod_info = {
    "host": "https://vapi.shouqianba.com",
    "brand_code": "999888",
    "store_sn": "LPK001",
    "client_member_sn": "lip-p-Tara",
    "card_number": "20016967110"
}


class RefundTaskSet(SequentialTaskSet):
    def on_start(self):
        self.__dict__['tender_sn'] = self.user.__dict__['tender_sn']
        self.__dict__['auth_utils'] = self.user.__dict__['auth_utils']
        self.__dict__['environment'] = self.__dict__['auth_utils'].environment
        self.__dict__['info'] = dev_info if self.__dict__['environment'] != 'prod' else prod_info
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
            "check_sn": f"Refund 阶梯并发测试-" + check_sn,
            "sales_sn": f"Refund 阶梯 并发测试-" + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the Refund order",
            "description": "Description of Refund order",
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
        body = self.__dict__['auth_utils'].signature(biz_body)
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
        self.__dict__['auth_utils'] = self.environment.__dict__['auth_utils']
        self.__dict__['tender_sn'] = self.environment.__dict__['pay_tenders_q'].get()


class StepLoadShape(LoadTestShape):
    step_duration = 5  # Each step lasts 60 seconds
    step_users = 1  # Add 10 users at each step
    total_steps = 5  # Number of steps

    def tick(self):
        run_time = self.get_run_time()
        print(f'run_time: {run_time}')
        current_step = run_time // self.step_duration
        if current_step > self.total_steps:
            return None
        user_count = self.step_users * (current_step + 1)
        return (user_count, self.step_users)


def prepare_pay_tender(max_user_num, auth_utils):
    environ = auth_utils.environment
    pay_tenders = []
    req_info = dev_info if environ != "prod" else prod_info
    for i in tqdm(range(max_user_num), desc="数据准备中..."):
        user_token_domain = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
        user_token_url = user_token_domain + "/api/wallet/v1/members/_get_user_token"
        user_token_headers = {"Content-Type": "application/json"}
        user_info = {
            "brand_code": req_info['brand_code'],
            'client_member_sn': req_info['client_member_sn'],
        }
        print(user_token_url)
        user_token_response = requests.post(user_token_url, headers=user_token_headers,
                                        json=AuthUtils(environ).signature(user_info), verify=False)
        try:
            user_token_resp = user_token_response.json()
            user_token = user_token_resp['response']['body']['biz_response']['data']['user_token']
        except Exception as e:
            print(f'user_token_resp: {user_token_response.text}')
            sys.exit(e)

        auth_code_domain = "https://pro-customer-gateway.iwosai.com" if environ != 'prod' else "https://ums.shouqianba.com"
        auth_code_url = auth_code_domain + "/wallet/v1/authcode/getmycode"
        auth_code_headers = {"Content-Type": "application/json;charset=utf-8", "Authorization": user_token}
        auth_code_body = {"preferred_class": "GIFT_CARD", "preferred_refer_id": req_info['card_number']}
        print(auth_code_url)
        auth_code_response = requests.post(auth_code_url, headers=auth_code_headers, json=auth_code_body, verify=False)
        try:
            auth_code_resp = auth_code_response.json()
            auth_code = auth_code_resp['data']['auth_code']
        except Exception as e:
            print(f'auth_code_resp: {auth_code_response.text}')
            sys.exit(e)

        ipay_domain = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
        ipay_url = ipay_domain + '/api/lite-pos/v1/sales/ipay'
        ipay_headers = {
            "Content-Type": "application/json",
        }
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        ipay_body = {
            "request_id": request_id,
            "brand_code": req_info['brand_code'],
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": "1",
            "scene_type": "1",
            "dynamic_id": auth_code,
            "currency": "156",
            "industry_code": "0",
            "check_sn": f'Refund-{max_user_num}-Performance' + check_sn,
            "sales_sn": f'Refund-{max_user_num}-Performance' + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": f"For Refund {max_user_num} 并发测试",
            "description": "Description of Ipay order",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
        }

        ipay_response = requests.post(ipay_url, headers=ipay_headers, json=auth_utils.signature(ipay_body), verify=False)
        try:
            ipay_resp = ipay_response.json()
            tender_sn = ipay_resp['response']['body']['biz_response']['data']['tender_sn']
        except Exception as e:
            print(f" ipay url: {ipay_response.request.url}")
            print(f" ipay body: {ipay_response.request.body}")
            print(f'ipay_response: {ipay_response.text}')
            sys.exit(e)

        pay_tenders.append(tender_sn)

    return pay_tenders


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

    auth_utils = AuthUtils(environ)
    environment.__dict__['auth_utils'] = auth_utils
    environment.__dict__['pay_tenders_q'] = queue.Queue()

    pay_tenders = prepare_pay_tender(max_user_num, auth_utils)
    for tender in pay_tenders:
        environment.__dict__['pay_tenders_q'].put(tender)
    # 获取钱包用户
    print("-------------Locust环境初始化成功-------👌👌👌👌👌")


if __name__ == '__main__':
    max_user_num = 10
    # environ = os.getenv("ENVIRONMENT", "dev")
    environ = "prod"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {max_user_num} --env={environ}"
                   f" --expect-workers {int(max_user_num / 6) + 1} --spawn-rate 6")
    os.system(command_str)
