import json
import os
import queue
import time

import requests
from gevent.pool import Group
from locust.env import Environment
from locust import SequentialTaskSet, task, events, LoadTestShape, FastHttpUser, HttpUser
from locust.runners import MasterRunner, WorkerRunner

from common.auth_utils import AuthUtils

global_que = queue.Queue()


class GiftInitTaskSet(SequentialTaskSet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.runner_info = self.user.environment.runner_info
        self.auth = self.user.environment.auth

    def on_start(self) -> None:
        pass

    @task
    def task1(self):
        endpoint = "/api/wallet/v1/giftcard/members/gift-records"
        headers = {'Content-Type': 'application/json'}
        biz_body = {
            "brand_code": '1024',
            'client_member_sn': "3456789"
        }
        body = self.auth.signature(biz_body)
        with self.client.post(endpoint, headers=headers, json=body, catch_response=True) as resp:
            if resp.status_code == 200:
                pass
                # print(f'{self.runner_info} - {json.loads(resp.request.body)}')
                # print(f'{self.runner_info} - {resp.text}')
        self.interrupt()


class GiftInitUser(FastHttpUser):
    tasks = [GiftInitTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        print(f"{environment.runner_info} -- 创建一个 {time.time()} 用户")

class CustomLoadTestShape(LoadTestShape):
    def __init__(self, step_duration=20, step_add_users=5, total_time_limit=600, start_user_num=5, max_user_num=0):
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
        environment.shape_class = CustomLoadTestShape(
            start_user_num=10,
            max_user_num=num_users,
            total_time_limit=400,
            step_add_users=20,
        )
        # 广播
        for i in range(num_users):
            msg = str(i)
            runner.send_message("prepare_message", msg)

    if isinstance(runner, WorkerRunner):
        runner_info = f'{role} [{runner.worker_index}] -pid:{pid}'
    environment.__dict__['runner_info'] = runner_info
    print(f"------------- {runner_info} Locust环境初始化成功-------👌👌👌👌👌")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    '''执行数据准备'''
    data_q = queue.Queue()
    num_users = environment.parsed_options.max_user_num

    print(f"----------- {environment.runner_info} - 测试开始执行-----------------")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f'!!!!!!!!!!! {environment.runner_info} 测 试 执 行 结 束 !!!!!!!!!!!!!')


if __name__ == '__main__':
    environ = "dev"
    print(f'os.cpu_count(): {os.cpu_count()}')
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = f"locust -f {file_name} --host={host} --env=dev  --processes {os.cpu_count()} --max-user-num=150"
    os.system(command_str)


