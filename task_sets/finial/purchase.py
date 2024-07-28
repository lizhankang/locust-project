import os
import time
from locust.env import Environment
from common.auth_utils import AuthUtils
from locust import HttpUser, SequentialTaskSet, task, events


class PurchaseTaskSet(SequentialTaskSet):
    def on_start(self):
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
        self.__dict__['environ'] = self.user.environment.parsed_options.env
        self.__dict__['info'] = dev_info if self.__dict__['environ'] != 'prod' else prod_info

    @task
    def task1(self):
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
            "amount": "30000",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "100 个并发 - " + check_sn,
            "sales_sn": "100 个并发 - " + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the purchase performance order",
            "description": "Description of 100 个并发，持续240s 并发测试",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "enable_sub_tender_types1": "301",
            "expired_at": AuthUtils.date_time(minutes=5),
            "crm_account_option": {
                "app_type": 5,
                "member_sn": self.__dict__['info'].get('member_sn')
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
        self.interrupt()


class PurchaseUser(HttpUser):
    tasks = [PurchaseTaskSet]

    def __init__(self, environment):
        super().__init__(environment)


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")


@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    print("-------------Locust环境初始化成功-------👌👌👌👌👌")


if __name__ == '__main__':
    num = 60
    environ = os.getenv("ENVIRONMENT", "dev")
    # environ = "prod"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {num} --env={environ}"
                   f" --expect-workers {int(num / 6)} --spawn-rate 6 -t 240")
    os.system(command_str)
