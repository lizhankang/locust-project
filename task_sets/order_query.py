import queue

from gevent import monkey

monkey.patch_all()

import os
import requests
from locust import HttpUser, SequentialTaskSet, task, between, events
from locust.env import Environment
from common.api_utils import ApiUtils

env = "dev"


order_sn_q = queue.Queue()


# 自定义命令行参数  -- 通过框架的钩子，向Locust添加自定义的 命令行参 数来实现环境变量
@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--my-argument", type=str, env_var="LOCUST_MY_ARGUMENT", default="", help="It's working")
    # Choices will validate command line input and show a dropdown in the web UI
    parser.add_argument("--env", choices=["dev", "staging", "prod"], default="dev", help="Environment")

num = 30


class OrderQueryTaskSet(SequentialTaskSet):

    @task
    def task1(self):
        self.envir = self.user.environment.parsed_options.env
        endpoint = "/api/lite-pos/v1/sales/query"
        headers = {
            "Content-Type": "application/json",
        }
        body = {
            "brand_code": "1024" if self.envir != "prod" else "700001",
            "order_sn": self.user.order_sn,
        }
        with self.client.post(url=endpoint, headers=headers, json=ApiUtils(env).signed_body(body),
                              name='purchase'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[RESPONSE]: {response.text}')

        self.interrupt()  # To stop after completing the sequence


class WebsiteUser(HttpUser):
    tasks = [OrderQueryTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.order_sn = order_sn_q.get()

def fetch_order_sns():
    order_sns = []
    for _ in range(num):
        host = "https://vip-apigateway.iwosai.com" if env != 'prod' else "https://vapi.shouqianba.com"
        url = host + "/api/lite-pos/v1/sales/purchase"
        headers = {
            "Content-Type": "application/json",
        }
        check_sn = sales_sn = request_id = ApiUtils.unique_random(10)
        biz_body = {
            "request_id": request_id,
            "brand_code": "1024" if env == "dev" else "700001",
            "store_sn": "LPK001",
            "workstation_sn": "567",
            "amount": "10",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "P-csn" + check_sn,
            "sales_sn": "P-ssn" + sales_sn,
            "sales_time": ApiUtils.date_time(),
            "subject": "Subject of the purchase order",
            "description": "Description of purchase order",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "enable_sub_tender_types": "301",
            "expired_at": ApiUtils.date_time(minutes=30),
            "crm_account_option": {
                "app_type": 5,
                "wx_union_id": "lip-vip"
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        response = requests.post(url=url, headers=headers, json=ApiUtils(env).signed_body(biz_body))
        if response.status_code == 200:
            order_sns.append(response.json()['response']['body']['biz_response']['data']['order_sn'])

    print(f'数据准备over: 一共{len(order_sns)}笔订单，订单号: {order_sns}')
    return order_sns


# 虚拟环境创建成功后执行
@events.init.add_listener
def on_locust_init(environment: Environment, **kwargs):
    for sn in fetch_order_sns():
        order_sn_q.put(sn)
    print("-------------Locust环境初始化成功-------")


if __name__ == "__main__":

    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com"

    command_str = (f"locust -f {file_name} --host={host} --users {num} "
                   f"--expect-workers {num} --spawn-rate {num / 10} -t 100")
    os.system(command_str)
