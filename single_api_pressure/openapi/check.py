import json
import logging
import random
import time
from json import JSONDecodeError

import requests
from locust import HttpUser, task, between, constant_throughput, tag, events

from common.api_utils import ApiUtils


class Check(HttpUser):

    @task
    def task1(self):
        endpoint = "/check"
        headers = {}
        biz_body = {
            "a": "a"
        }
        with self.client.post(url=endpoint, headers=headers, json=biz_body,
                              name='order_query'.upper(), catch_response=True) as response:
            print(f'[URL]: {response.request.url}')
            print(f'[REQUEST]: {response.request.body.decode("utf-8")}')
            print(f'[RESPONSE]: {response.text}')
