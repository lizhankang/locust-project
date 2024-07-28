import json
import os
import queue
import requests
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events, LoadTestShape
from locust.runners import WorkerRunner, MasterRunner

from common.auth_utils import AuthUtils


class KaCoreTaskSet(SequentialTaskSet):
    @task
    def find_by_brand_code_v2(self):
        endpoint = "/rpc/brand"
        payload = json.dumps({
            "id": "0",
            "jsonrpc": "2.0",
            "method": "findByBrandCodeV2",
            "params": [
                "1024"
            ]
        })
        headers = {
            'Content-Type': 'application/json',
            'x-env-flag': "sort-test"
        }
        with self.client.post(endpoint, headers=headers, data=payload) as resp:
            if resp.status_code == 200:
                code = resp.json()['result']
                print(code)
                # all_codes.append(code)
        self.interrupt()


class KaCoreUser(HttpUser):
    tasks = [KaCoreTaskSet]


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
            max_user_num=200,
            start_user_num=20,
            step_add_users=10,
            step_duration=60,
            total_time_limit=1200,

        )

    if isinstance(runner, WorkerRunner):
        runner_info = f'{role} [{runner.worker_index}] -pid:{pid}'
    environment.__dict__['runner_info'] = runner_info

    print("-------------Locust环境初始化成功-------👌👌👌👌👌")


if __name__ == '__main__':

    environ = "dev"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "http://ka-core-business.iwosai.com" if environ != "prod" else "http://ka-core-business.iwosai.com"
    command_str = f"locust -f {file_name} --host={host} --env=dev --processes -1"
    os.system(command_str)