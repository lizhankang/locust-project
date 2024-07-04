from locust import HttpUser, task, events

from common.api_utils import ApiUtils


# 自定义参数  -- 通过框架的钩子，向Locust添加自定义的命令行参数来实现环境变量
@events.init_command_line_parser.add_listener
def _(parser):
    # Choices will validate command line input and show a dropdown in the web UI
    parser.add_argument("--env", choices=["dev", "staging", "prod"], default="dev", help="Environment")


@events.request.add_listener
def my_request_handler(response, exception, **kwargs):
    if exception:
        print(f"\033[91m [@events.request.add_listener] :  Request to {kwargs.get('name')} failed with exception {exception} \033[0m")
    else:
        print(f"\033[91m [@events.request.add_listener] : response.request_meta: {response.request_meta} \033[0m")
        print(f"\033[91m [@events.request.add_listener] : request_body: {response.request.body.decode('utf-8')}\033[0m")
        print(f"\033[91m [@events.request.add_listener] : response: {response.text} \033[0m")


class MyTestUser(HttpUser):
    host = "https://vapi.shouqianba.com"

    def on_start(self):
        try:
            self.envir = self.environment.parsed_options.env
        except AttributeError:
            self.envir = "dev"
        # self.envir = "prod"
        print(f'[on_start]: {self.envir}')

    @task
    def t(self):
        endpoint = "/api/lite-pos/v1/sales/query"
        headers = {
            "Content-Type": "application/json",
        }
        biz_body = {
            "brand_code": "999888" if self.envir != "prod" else "1024",
            "order_sn": "7903247705290125",
            "environment": self.envir,
        }
        body = ApiUtils(self.envir).signed_body(biz_body)
        self.client.post(endpoint, headers=headers, json=body)
