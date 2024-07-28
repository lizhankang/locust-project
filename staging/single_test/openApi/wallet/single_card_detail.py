import json
import os
import queue
import time

import requests
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events, LoadTestShape
from locust.runners import MasterRunner, WorkerRunner, LocalRunner

from common.auth_utils import AuthUtils


class SingleCardDetailTaskSet(SequentialTaskSet):
    def on_start(self):
        self.auth = self.user.__dict__['auth']

    @task
    def task(self):
        endpoint = "/api/wallet/v1/giftcard/members/cards/card-detail"
        headers = {'Content-Type': 'application/json'}
        biz_body = {
            "brand_code": "1024",
            "client_member_sn": "lip-p-Lori",
            "card_number": "20014065879"
        }
        body = self.auth.signature(biz_body)
        with self.client.post(endpoint, headers=headers, json=body, catch_response=True) as resp:
            if resp.status_code == 200:
                # print(resp.request.body)
                # print(resp.text)
                print()
            else:
                resp.failure(f"通讯状态码错误!! status code: {resp.status_code}")
        self.interrupt()


class SingleCardDetailUser(HttpUser):
    tasks = [SingleCardDetailTaskSet]

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
        if run_time > self.total_time_limit:
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
            max_user_num=600,
            start_user_num=50,
            step_add_users=50,
            step_duration=60,
            total_time_limit=840,

        )

    if isinstance(runner, WorkerRunner):
        runner_info = f'{role} [{runner.worker_index}] -pid:{pid}'
    environment.__dict__['runner_info'] = runner_info

    print("-------------Locust环境初始化成功-------👌👌👌👌👌")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    '''执行数据准备'''

    runner = environment.runner
    role = runner.__class__.__name__
    if isinstance(runner, WorkerRunner):
        print(f"总共有 {os.cpu_count()} 个进程参与工作， 数据准备平均分")

    if isinstance(runner, LocalRunner):
        print(f"说明只有一个线程运行程序，所有的数据都应该自己准备")


    print(f"---------------------测试开始执行-----{environment.runner_info}------------")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 测 试 执 行 结 束 !!!!!!!!{environment.runner_info}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')


if __name__ == '__main__':
    environ = "dev"
    print(os.cpu_count())
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = f"locust -f {file_name} --host={host} --expect-workers 20 --env=dev  --processes -1"
    os.system(command_str)
