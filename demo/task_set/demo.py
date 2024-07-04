import os
from locust import User, TaskSet, constant, task


class ForumSection(TaskSet):
    wait_time = constant(1)

    @task(10)
    def view_thread(self):
        pass

    @task
    def create_thread(self):
        self.client.request()
        pass

    @task
    def stop(self):
        self.interrupt()


class LoggedInUser(User):
    wait_time = constant(5)
    tasks = {ForumSection: 2}

    @task
    def my_task(self):
        pass


if __name__ == "__main__":
    os.system("locust -f locustfile.py --host=https://your-api-endpoint.com --users 10 --spawn-rate 1")