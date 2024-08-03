import json
import os
import queue
import requests
from jsonpath import jsonpath
from locust.env import Environment
from locust import SequentialTaskSet, task, events, LoadTestShape, FastHttpUser
from locust.runners import MasterRunner, WorkerRunner, LocalRunner

from common.auth_utils import AuthUtils

import pandas as pd


def read_auth_codes():
    excel_path = "/Users/lizhankang/Documents/shouqianba/staging-自压测报告/1024品牌50w测试卡.xlsx"
    cols = ["静态核销码", "卡号"]
    df = pd.read_excel(excel_path, usecols=cols)
    # df.iloc[:, 0].tolist()
    data = df.to_dict("records")
    return data


auth_codes = read_auth_codes()



class BindValidation2TaskSet(SequentialTaskSet):

    def on_start(self):
        self.__dict__['auth'] = self.user.__dict__['auth']
        self.redeem_code = self.user.environment.auth_code_q.get() \
            if not self.user.environment.auth_code_q.empty() else {"静态核销码": "43788842058351122739", "卡号": "20015691361"}

    @task
    def task(self):
        endpoint = '/api/wallet/v1/giftcard/gift-cards-redeemcode-validation'
        headers = {'Content-Type': 'application/json'}
        biz_body = {
            "brand_code": "1024",
            "redeem_code": self.redeem_code['静态核销码']
        }
        body = self.__dict__['auth'].signature(biz_body)
        with self.client.post(endpoint, headers=headers, json=body, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"通讯异常!!! 通讯状态码: {response.status_code}")
                return

            resp = response.json()
            result_code = jsonpath(resp, "$.response.body.biz_response.result_code")[0]
            error_code = jsonpath(resp, "$.response.body.biz_response.error_code")
            if result_code == '200':
                print(f" 卡号: {self.redeem_code['卡号']} 兑换校验通过, 静态核销码: {self.redeem_code['静态核销码']}..")
            else:
                msg = (f'Request: {json.loads(response.request.body)} \n Response: {response.text} \n'
                       f'Card number: {self.redeem_code["卡号"]} Redeem code: {self.redeem_code["静态核销码"]}')
                response.failure(msg)
        self.interrupt()


class BindValidation2User(FastHttpUser):
    tasks = [BindValidation2TaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.__dict__['auth'] = self.environment.__dict__['auth']


class CustomLoadTestShape(LoadTestShape):

    def __init__(self, step_duration=30, step_add_users=5, total_time_limit=600, start_user_num=5, max_user_num=0):
        super().__init__()
        # 每个阶段持续时间（秒）
        self.step_duration = step_duration
        # 每个阶段增加的用户数量
        self.step_add_users = step_add_users
        # 总运行时间（秒）
        self.total_time_limit = total_time_limit
        # 起始用户数
        self.start_user_num = start_user_num
        # 最大用户数
        self.max_user_num = max_user_num
        print("StepLoadShape实例话完成....")

    # 该方法返回一个具有所需用户计数和生成率的元组（或者返回None以停止测试）
    def tick(self):
        # 查测试已经运行了多长时间
        run_time = self.get_run_time()
        print(f'run_time: {run_time} 秒')
        # 判断是否超过了压力测试的最大持续时间
        if (self.total_time_limit > 0) and (run_time > self.total_time_limit):
            return None
        # 计算当前时间的虚拟用户数量
        current_step = round(run_time // self.step_duration)
        if self.start_user_num > 0:
            user_count = (self.step_add_users * current_step) + self.start_user_num
        else:
            user_count = self.step_add_users * (current_step + 1)
        # 现在最大虚拟用户数量
        if (self.max_user_num > 0) and (user_count > self.max_user_num):
            user_count = self.max_user_num
        print(f'user_count: {user_count}')
        return (user_count, self.step_add_users)


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")
    parser.add_argument("--max-user-num", type=int, default=100, help="Maximum number of users")


@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    environ = environment.parsed_options.env
    num_users = environment.parsed_options.max_user_num

    auth = AuthUtils(environ)
    environment.__dict__['auth'] = auth

    pid = os.getpid()
    runner = environment.runner
    role = runner.__class__.__name__
    runner_info = None
    if isinstance(runner, MasterRunner):
        runner_info = f'{role}-pid:{pid}'
        # for i in range(num_users):
        #     global_data_queue.put(i)
        print("This is the master node.")
        environment.shape_class = CustomLoadTestShape(
            max_user_num=2000,
            start_user_num=50,
            step_add_users=50,
            step_duration=60,
            total_time_limit=1200,

        )

    if isinstance(runner, WorkerRunner):
        runner_info = f'{role} [{runner.worker_index}] -pid:{pid}'
    environment.__dict__['runner_info'] = runner_info

    print("-------------Locust环境初始化成功-------👌👌👌👌👌")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    '''执行数据准备'''
    runner = environment.runner

    if isinstance(runner, MasterRunner):
        pass

    # 如果是 WorkerRunner 根据CPU的数量各自准备数据
    if isinstance(runner, WorkerRunner):
        environment.auth_code_q = queue.Queue()
        worker_index = runner.worker_index
        cpu_number = environment.parsed_options.processes
        if len(auth_codes) % cpu_number != 0:
            worker_data_number = len(auth_codes) // cpu_number
            if worker_index == cpu_number - 1:
                worker_data = auth_codes[worker_index * worker_data_number:]
            else:
                worker_data = auth_codes[worker_index * worker_data_number: (worker_index + 1) * worker_data_number]
        else:
            worker_data_number = len(auth_codes) // cpu_number
            worker_data = auth_codes[worker_index * worker_data_number: (worker_index + 1) * worker_data_number]

        for data in worker_data:
            environment.auth_code_q.put(data)

    # 如果是 LocalRunner 全量准备数据
    if isinstance(runner, LocalRunner):
        pass

    print(f"------------测试开始执行-----{environment.runner_info}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 测 试 执 行 结 束 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')


if __name__ == '__main__':
    # environ = os.getenv("ENVIRONMENT", "dev")
    environ = "dev"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = f"locust -f {file_name} --host={host} --expect-workers 20 --env=dev  --processes -1"
    os.system(command_str)
