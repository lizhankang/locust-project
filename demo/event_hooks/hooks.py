from locust import HttpUser, constant_throughput, tag, task, events

from common.api_utils import ApiUtils
from locust.runners import MasterRunner

import os

# 获取命令行输入的(设置的)环境变量 -- 传统做法
# print(os.environ['domain'])


# 自定义命令行参数  -- 通过框架的钩子，向Locust添加自定义的 命令行参 数来实现环境变量
@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--my-argument", type=str, env_var="LOCUST_MY_ARGUMENT", default="", help="It's working")
    # Choices will validate command line input and show a dropdown in the web UI
    parser.add_argument("--env", choices=["dev", "staging", "prod"], default="dev", help="Environment")
    # Set `include_in_web_ui` to False if you want to hide from the web UI
    parser.add_argument("--my-ui-invisible-argument", include_in_web_ui=False, default="I am invisible")
    # Set `is_secret` to True if you want the text input to be password masked in the web UI
    parser.add_argument("--my-ui-password-argument", is_secret=True, default="I am a secret")


# 每个工作进程（而不是每个用户）
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    if isinstance(environment.runner, MasterRunner):
        print(f"\033[91m [@events.init.add_listener] :  I'm on master node \033[0m")
    else:
        print(f"\033[91m [@events.init.add_listener] :  I'm on a worker or standalone node \033[0m")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"Custom argument supplied: {environment.parsed_options.my_argument}")
    print(f"Custom argument supplied: {environment.parsed_options.env}")
    print(f'\033[91m [@events.test_start.add_listener] :  A new test is starting \033[0m')


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f'\033[91m [@events.test_stop.add_listener] :  A new test is ending \033[0m')


@events.request.add_listener
# def my_request_handler(request_type, name, response_time, response_length, response,
#                        context, exception, start_time, url, **kwargs):
def my_request_handler(url, request_type, name, context, response, exception, **kwargs):
    """
    这个钩子的实现函数的入参其实就是：response.request_meta:
    {'request_type': 'POST', 'response_time': 233.12837499999972, 'name': '/api/lite-pos/v1/sales/query',
    'context': {}, 'response': <Response [200]>, 'exception': None, 'start_time': 1719938319.796334,
    'url': 'https://vapi.shouqianba.com/api/lite-pos/v1/sales/query', 'response_length': 1679}
    """
    if exception:
        print(f"\033[91m [@events.request.add_listener] :  Request to {name} failed with exception {exception} \033[0m")
    else:
        print(f"\033[91m [@events.request.add_listener] : Name: {name} \033[0m")
        print(f"\033[91m [@events.request.add_listener] : url: {url} \033[0m")
        print(f"\033[91m [@events.request.add_listener] : request_type: {request_type} \033[0m")
        print(f"\033[91m [@events.request.add_listener] : request_body: {response.request.body.decode('utf-8')}\033[0m")
        print(f"\033[91m [@events.request.add_listener] : response: {response.text} \033[0m")
        # 请求上下文，没搞懂
        print(f"\033[91m [@events.request.add_listener] : context: {context} \033[0m")
        print(f"\033[91m [@events.request.add_listener] : response.request_meta: {response.request_meta} \033[0m")


class MyUser(HttpUser):
    # def context(self):
    #     return {"username": self.username}

    def on_start(self):
        self.envir = self.environment.parsed_options.env
        print(f'[on_start]: {self.envir}')

    @task
    def t(self):
        self.username = "foo"
        endpoint = "/api/lite-pos/v1/sales/query"
        headers = {
            "Content-Type": "application/json",
        }
        biz_body = {
            "brand_code": "999888" if self.envir != "prod" else "1024",
            # "order_sn": self.order_sn
            "order_sn": "7903247705290125",
            "username": self.username,
        }
        body = ApiUtils(self.envir).signed_body(biz_body)
        self.client.post(endpoint, headers=headers, json=body)

    # @events.request.add_listener
    # def on_request(context, **kwargs):
    #     # 请求发送之后触发
    #     print(context["username"])
