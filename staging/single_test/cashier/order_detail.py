import csv
import datetime
import os
import random
import sys
import queue
import requests
from locust.runners import MasterRunner, WorkerRunner, LocalRunner

from common.auth_utils import AuthUtils
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events, LoadTestShape

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


class OrderDetailTaskSet(SequentialTaskSet):
    def on_start(self):
        self.__dict__['order_token'] = self.user.order_token
        self.__dict__['environ'] = self.user.environment.parsed_options.env

    @task
    def order_detail_task(self):
        endpoint = "/api/lpos/cashier/v2/cashier"
        headers = {
            "Content-Type": "application/json",
        }
        params = {
            "order_token": self.__dict__['order_token']
        }

        with self.client.get(url=endpoint, headers=headers, params=params,
                             name='order_detail'.upper(), catch_response=True) as response:
            # print(f'[URL]: {response.request.url}')
            # print(f'[RESPONSE]: {response.text}')
            pass
        self.interrupt()


class OrderDetailUser(HttpUser):
    tasks = [OrderDetailTaskSet]
    num = 0

    def __init__(self, environment):
        super().__init__(environment)
        self.order_token = self.environment.order_token_q.get()
        print(f'{environment.runner_info} -- {self.order_token}')
        # print(f'{environment.runner_info} --已创建 {OrderDetailUser.num} 个用户')
        # print(f'{environment.runner_info} --还剩余 {environment.order_token_q.qsize()} 条数据可使用')
        # try:
        #     self.order_token = self.environment.order_token_q.get()
        #     print(f"{environment.runner} -- 成功创建一个新的用户")
        #     OrderDetailUser.num += 1
        #
        # except:
        #     print("从管道中获取数据失败，导致创建用户失败...")
        # print(f'{environment.runner_info} --剩余 {environment.order_token_q.qsize()} 条数据可使用')

    # def on_stop(self):
    #     self.environment.__dict__['order_token_q'].put(self.__dict__['order_token'])


# Use the custom load shape
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
        print(f'run_time: {run_time} 秒， 此时应该要有: {user_count} 个user')
        return (user_count, self.step_add_users)


# def prepare_order_token(task_environ, num_users):
#     order_tokens = []
#     domain = "https://vip-apigateway.iwosai.com" if task_environ != "prod" else "https://vapi.shouqianba.com"
#     url = domain + "/api/lite-pos/v1/sales/purchase"
#     data_info = dev_info if task_environ != "prod" else prod_info
#     headers = {
#         "Content-Type": "application/json",
#     }
#
#     # 准备会员
#     client_member_sns = []
#     client_member_sn_path = "/Users/lizhankang/workSpace/selfProject/pythonProject/it-is-useful/shouqianba/src/main/test/wallet/wallet_sn_2024-07-04T17:35:16+08:00.csv"
#     with open(client_member_sn_path, newline='') as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             client_member_sns.append(row['client_member_id'])
#             client_member_sns.append(row['client_member_id'])
#
#     member_sns = random.sample(client_member_sns, num_users)
#     for member_sn in member_sns:
#         check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
#         body = {
#             "request_id": request_id,
#             "brand_code": data_info.get('brand_code'),
#             "store_sn": data_info.get('brand_code'),
#             "workstation_sn": "567",
#             "amount": "30000",
#             "scene": "5",
#             "currency": "156",
#             "industry_code": "0",
#             "check_sn": "Order_Detail - " + check_sn,
#             "sales_sn": "Order_Detail - " + sales_sn,
#             "sales_time": AuthUtils.date_time(),
#             "subject": "Subject of the Order_Detail Performance ",
#             "description": f"For Order_Detail Performance {num_users} 并发测试",
#             "operator": "operator of order -> lip",
#             "customer": "customer of order -> lip",
#             "pos_info": "POS_INFO of the purchase order",
#             "reflect": "Reflect of the purchase order",
#             "expired_at": AuthUtils.date_time(minutes=5),
#             "crm_account_option": {
#                 "app_type": 5,
#                 "member_sn": member_sn
#             },
#             "specified_payment": {
#                 "selected_giftcard": "0"
#             }
#         }
#         response = requests.post(url, headers=headers, json=AuthUtils(task_environ).signature(body))
#         if response.status_code == 200:
#             try:
#                 biz_response = response.json()['response']['body']['biz_response']
#             except KeyError:
#                 print(f'[ERROR]: {response.text}')
#             else:
#                 print(f'[SUCCESS]: {biz_response}')
#                 order_tokens.append(biz_response['data']['order_token'])
#         else:
#             print(f'[ERROR]: {response.text}')
#             sys.exit(f'[ERROR]: {response.text}')
#
#     if len(order_tokens) != num_users:
#         sys.exit(f'总共有 {num_users} 名用户，但是只准备了 {len(order_tokens)} 条数据。程序退出！！！！🚫🚫🚫🚫🚫')
#     else:
#         print(f'总共有 {num_users} 名用户，准备了 {len(order_tokens)} 条数据。【 数据准备完成 👌👌👌👌👌】')
#     return order_tokens


def order_token(auth, number, q):
    subject = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    data_info = dev_info if auth.environment != "prod" else prod_info
    domain = "https://vip-apigateway.iwosai.com" if auth.environment != "prod" else "https://vapi.shouqianba.com"
    url = domain + "/api/lite-pos/v1/sales/purchase"
    headers = {"Content-Type": "application/json"}
    for _ in range(number):
        check_sn = sales_sn = request_id = AuthUtils.unique_random(10)
        body = {
            "request_id": request_id,
            "brand_code": data_info.get('brand_code'),
            "store_sn": data_info.get('brand_code'),
            "workstation_sn": "567",
            "amount": "30000",
            "scene": "5",
            "currency": "156",
            "industry_code": "0",
            "check_sn": "Order_Detail - " + check_sn,
            "sales_sn": "Order_Detail - " + sales_sn,
            "sales_time": AuthUtils.date_time(),
            "subject": "Subject of the Order_Detail Performance ",
            "description": f"For Order_Detail Performance {subject} 并发测试",
            "operator": "operator of order -> lip",
            "customer": "customer of order -> lip",
            "pos_info": "POS_INFO of the purchase order",
            "reflect": "Reflect of the purchase order",
            "expired_at": AuthUtils.date_time(minutes=30),
            "crm_account_option": {
                "app_type": 5,
                "member_sn": data_info.get("member_sn")
            },
            "specified_payment": {
                "selected_giftcard": "0"
            }
        }
        response = requests.post(url, headers=headers, json=auth.signature(body))
        if response.status_code == 200:
            try:
                biz_response = response.json()['response']['body']['biz_response']
            except KeyError:
                print(f'[ERROR]: {response.text}')
            else:
                q.put(biz_response['data']['order_token'])
        else:
            print(f'[ERROR]: {response.text}')
            sys.exit(f'[ERROR]: {response.text}')
    print(f'{number} 条数据准备成功')


@events.init_command_line_parser.add_listener
def command_line(parser):
    parser.add_argument("--env",
                        choices=["dev", "staging", "prod"],
                        default="dev",
                        help="Task Running Environment")
    parser.add_argument("--max-user-num", type=int, default=100, help="Maximum number of users")


@events.init.add_listener
def locust_environment_init(environment: Environment, **kwargs):
    environment.__dict__['order_token_q'] = queue.Queue()

    locust_environ = environment.parsed_options.env
    max_user_num = environment.parsed_options.max_user_num

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
            max_user_num=max_user_num,
            start_user_num=10,
            step_add_users=10,
            step_duration=60,
            total_time_limit=1200,

        )

    if isinstance(runner, WorkerRunner):
        runner_info = f'{role} [{runner.worker_index}] -pid:{pid}'

    environment.runner_info = runner_info
    environment.auth = AuthUtils(locust_environ)

    # for sn in prepare_order_token(locust_environ, max_user_num):
    #     environment.__dict__['order_token_q'].put(sn)
    print(f"-------------{runner_info} 初始化成功-----------👌👌👌👌👌")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    执行数据准备
    """
    runner = environment.runner
    cpu_numbers = environment.parsed_options.processes
    data_numbers = environment.parsed_options.max_user_num
    # 如果是 MasterRunner 啥也不干
    if isinstance(runner, MasterRunner):
        pass
    # 如果是 WorkerRunner 根据CPU的数量各自准备数据
    if isinstance(runner, WorkerRunner):
        # print(f'{environment.runner_info} -- 需要准备 {(data_numbers // cpu_numbers) + 1} 条数据')
        environment.order_token_q = queue.Queue()

        order_token(environment.auth, (data_numbers // (cpu_numbers * 5)) + 1, environment.order_token_q)

        print(f'{environment.runner_info} -- 准备了 {environment.order_token_q.qsize()} 条数据')

    # 如果是 LocalRunner 全量准备数据
    if isinstance(runner, LocalRunner):
        print(f'{environment.runner_info} -- {cpu_numbers}')

    print(f"------------------------ 测 试 开 始 执 行 --------------------{environment.runner_info}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 测 试 执 行 结 束 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')


@events.spawning_complete.add_listener
def on_spawning_complete(user_count, **kwargs):
    print(f"Spawning complete. Current user count: {user_count}")


if __name__ == '__main__':
    environ = "dev"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://vip-apigateway.iwosai.com" if environ != "prod" else "https://vapi-s.shouqianba.com"
    command_str = f"locust -f {file_name} --host={host} --env={environ} --processes -1 --max-user-num=20"
    os.system(command_str)
