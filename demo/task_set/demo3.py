from locust import HttpUser, SequentialTaskSet, task, between
from locust.runners import STATE_INIT, STATE_SPAWNING
from locust.env import Environment

# 假设我们有 10 个不同的 order_token
order_tokens = [
    "order_token_1",
    "order_token_2",
    "order_token_3",
    "order_token_4",
    "order_token_5",
    "order_token_6",
    "order_token_7",
    "order_token_8",
    "order_token_9",
    "order_token_10",
]


class UserBehavior(SequentialTaskSet):

    def on_start(self):
        self.user_info = {
            "order_token": self.user.order_token,
            "user_id": id(self.user),
        }
        print(f"User {self.user_info['user_id']} started with order_token {self.user_info['order_token']}")
        self.round_number = 0  # 用于跟踪任务轮次

    @task
    def step_1(self):
        print(f"{self.user_info['user_id']} Round {self.round_number}: Step 1 started")
        headers = {"Authorization": f"Bearer {self.user_info['order_token']}"}
        response = self.client.get("/api/order/step1", headers=headers)
        print(
            f"User {self.user_info['user_id']} completed step 1 with status code {response.status_code} in {response.elapsed.total_seconds()}s")

    @task
    def step_2(self):
        print(f"{self.user_info['user_id']} Round {self.round_number}: Step 2 started")
        headers = {"Authorization": f"Bearer {self.user_info['order_token']}"}
        response = self.client.get("/api/order/step2", headers=headers)
        print(
            f"User {self.user_info['user_id']} completed step 2 with status code {response.status_code} in {response.elapsed.total_seconds()}s")

    @task
    def step_3(self):
        print(f"{self.user_info['user_id']} Round {self.round_number}: Step 2 started")
        headers = {"Authorization": f"Bearer {self.user_info['order_token']}"}
        response = self.client.get("/api/order/step3", headers=headers)
        print(
            f"User {self.user_info['user_id']} completed step 3 with status code {response.status_code} in {response.elapsed.total_seconds()}s")
        self.round_number += 1  # 增加任务轮次计数
        self.interrupt()  # To stop after completing the sequence


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(10, 30)

    def __init__(self, environment):
        super().__init__(environment)
        self.order_token = None


def assign_tokens(environment: Environment):
    for i, user in enumerate(environment.runner.user_classes[WebsiteUser]):
        user.order_token = order_tokens[i]


if __name__ == "__main__":
    import os
    from locust import events

    # 得到虚拟用户实例后执行
    @events.init.add_listener
    def on_locust_init(environment: Environment, **kwargs):
        if environment.state == STATE_INIT:
            environment.events.spawning_complete.add_listener(assign_tokens)


    os.system("locust -f demo3.py --host=https://your-api-endpoint.com --users 10 --spawn-rate 1")
