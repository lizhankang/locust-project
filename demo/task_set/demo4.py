from locust import HttpUser, SequentialTaskSet, task, between


class UserBehavior(SequentialTaskSet):
    def on_start(self):
        # 每次启动该任务集合时执行
        self.round_number = 0  # 用于跟踪任务轮次
        print(f'{self.round_number} 开始')

    @task
    def step_1(self):
        print(f"Round {self.round_number}: Step 1 started")
        self.client.get("/step1")
        print(f"Round {self.round_number}: Step 1 completed")

    # @task
    # def step_2(self):
    #     print(f"Round {self.round_number}: Step 2 started")
    #     self.client.get("/step2")
    #     print(f"Round {self.round_number}: Step 2 completed")
    #
    # @task
    # def step_3(self):
    #     print(f"Round {self.round_number}: Step 3 started")
    #     self.client.get("/step3")
    #     print(f"Round {self.round_number}: Step 3 completed")
        self.round_number += 1  # 增加任务轮次计数

        self.interrupt()  # To stop after completing the sequence


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    # wait_time = between(20, 30)  # 用户在每一轮任务之间等待的时间


if __name__ == "__main__":
    import os
    os.system("locust -f demo4.py --host=https://your-api-endpoint.com --users 3 --spawn-rate 1 -t 100s")
    # os.system("locust -f demo4.py")
