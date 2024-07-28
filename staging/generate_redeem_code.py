import json
import os
import queue
import requests
from locust.env import Environment
from locust import HttpUser, SequentialTaskSet, task, events, LoadTestShape
from common.auth_utils import AuthUtils

# 创建全局队列来存储生成的code
generated_codes = queue.Queue()
all_codes = []


class RedeemCodeGeneratorTaskSet(SequentialTaskSet):
    @task
    def task(self):
        endpoint = "/rpc/redeem"
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "getRedeemCode",
            "params": [
                [
                    {
                        "card_number": "20015551155"
                    }
                ]
            ],
            "id": 2
        })
        headers = {
            'Content-Type': 'application/json'
        }
        with self.client.post(endpoint, headers=headers, data=payload) as resp:
            if resp.status_code == 200:
                code = resp.json()['result']
                print(code)
                all_codes.append(code)
        self.interrupt()


class RedeemCodeGeneratorUser(HttpUser):
    tasks = [RedeemCodeGeneratorTaskSet]
    pass


class StepLoadShape(LoadTestShape):
    step_duration = 20  # Each step lasts 60 seconds
    step_users = 10     # Add 10 users at each step
    total_steps = 5     # Number of steps

    def tick(self):
        run_time = self.get_run_time()
        print(f'run_time: {run_time}')
        current_step = run_time // self.step_duration
        if current_step > self.total_steps:
            return None
        user_count = self.step_users * (current_step + 1)
        return (user_count, self.step_users)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f'生成的所有code总共: {len(all_codes)}')
    print(f'去重之后code的长度: {len(set(all_codes))}')


if __name__ == '__main__':
    max_user_num = 100
    environ = os.getenv("ENVIRONMENT", "dev")
    # environ = "prod"
    file_name = os.path.basename(os.path.abspath(__file__))
    host = "https://giftcard-redeem.iwosai.com" if environ != "prod" else "https://vapi.shouqianba.com"
    command_str = (f"locust -f {file_name} --host={host} --users {max_user_num}"
                   f" --expect-workers 10 --spawn-rate 10 -t 500")
    os.system(command_str)
