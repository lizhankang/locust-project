import os
from locust import HttpUser, SequentialTaskSet, task, between
envir = "dev"
num = 10


class CheckApiTaskSet(SequentialTaskSet):
    @task
    def task1(self):
        endpoint = "/api/lite-pos/test"
        headers = {
            "Content-Type": "application/json",
        }
        body = {
            "brand_code": "1024"
        }
        with self.client.post(url=endpoint, headers=headers, json=body,
                              name='purchase'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[RESPONSE]: {response.text}')

        self.interrupt()


class WebsiteUser(HttpUser):
    tasks = [CheckApiTaskSet]

    def __init__(self, environment):
        super().__init__(environment)
        # self.order_token = None


if __name__ == '__main__':
    num = 10
    host = "https://vip-apigateway.iwosai.com"
    file_name = os.path.basename(os.path.abspath(__file__))
    command_str = f"locust -f {file_name} --host={host} --users {num} --spawn-rate 3 -t 100"
    os.system(command_str)
