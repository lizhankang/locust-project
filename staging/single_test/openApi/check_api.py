import os
import time
import logging

import jsonpath
from locust.env import Environment
from locust.runners import WorkerRunner, MasterRunner

from common.auth_utils import AuthUtils
from locust import HttpUser, SequentialTaskSet, LoadTestShape, task, events

staging_info = {
    "brand_code": "1024",
    "store_sn": "LPK001",
    "member_sn": "lip-vip"
}
prod_info = {
    "brand_code": "999888",
    "store_sn": "LPK001",
    "member_sn": "lip-p-Tara"
}
# 配置日志记录
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class CheckApiTaskSet(SequentialTaskSet):

    def on_start(self):
        self.auth = self.user.auth
        self.environ = self.auth.environment
        self.__dict__['info'] = staging_info if self.environ != 'prod' else prod_info

    @task
    def task1(self):
        endpoint = "/check"
        headers = {
            "Content-Type": "application/json",
        }
        # time.sleep(1)

        with self.client.get(url=endpoint, headers=headers,
                             name='check'.upper(), catch_response=True) as response:
            if response.status_code != 200:
                logger.error(f'[URL]: {response.request.url}')
                logger.error(f'请求耗时: {response.request_meta["response_time"]}ms')
                logger.error(f'[RESPONSE]: {response.text}')
                print(f'[URL]: {response.request.url}')
                print(f'请求耗时: {response.request_meta["response_time"]}ms')
                print(f'[RESPONSE]: {response.text}')

            else:
                # logger.info(f'[URL]: {response.request.url}')
                # logger.info(f'请求耗时: {response.request_meta["response_time"]}ms')
                logger.info(f'[RESPONSE]: {response.text}')
        self.interrupt()


class CheckApiUser(HttpUser):
    tasks = [CheckApiTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        self.auth = self.environment.auth


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
    max_user_num = environment.parsed_options.max_user_num

    auth = AuthUtils(environ)
    environment.auth = auth

    pid = os.getpid()
    runner = environment.runner
    role = runner.__class__.__name__
    runner_info = None
    if isinstance(runner, MasterRunner):
        runner_info = f'{role}-pid:{pid}'
        environment.shape_class = CustomLoadTestShape(
            start_user_num=100,
            step_add_users=100,
            step_duration=60,
            total_time_limit=900,
        )

    if isinstance(runner, WorkerRunner):
        runner_info = f'{role} [{runner.worker_index}] -pid:{pid}'
    environment.__dict__['runner_info'] = runner_info

    print(f"-------------Locust环境初始化成功-------👌👌👌👌👌- {runner_info}")


if __name__ == '__main__':
    environ = "dev"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    # host = "http://lite-pos-core.beta.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = f"locust -f {file_name} --host={host} --env={environ} --processes -1 --max-user-num=200"
    os.system(command_str)
