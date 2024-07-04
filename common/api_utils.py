import datetime
import random
import uuid

from lipkg.rsa import signer


class ApiUtils:
    def __init__(self, env):
        dev_info = {
            "appid": "28lpm3781001",
            "pri_key": "/Users/lizhankang/Documents/shouqianba/pems/dev/1024/clientPriKey.pem",
            "pub_key": "/Users/lizhankang/Documents/shouqianba/pems/dev/sysPubKey.pem",
        }
        prod_info = {
            "appid": "28lpm0000002",
            "pri_key": "/Users/lizhankang/Documents/shouqianba/pems/prod/700001/clientPriKey.pem",
            "pub_key": "/Users/lizhankang/Documents/shouqianba/pems/prod/sysPubKey.pem",
        }
        self._domain_info = prod_info if env == 'prod' else dev_info

    def signed_body(self, biz_body):
        request_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
        body = {
            "request": {
                "head": {"appid": self._domain_info.get('appid'), "request_time": request_time, "sign_type": "SHA256",
                         "version": "1.0.0"},
                "body": biz_body
            },
            "signature": None
        }
        body['signature'] = signer(body['request'], self._domain_info.get('pri_key'))
        return body

    @classmethod
    def random_num_str(cls, length: int) -> str:
        """
        返回一个长度为 length 的纯数字字符串
        :param length:
        :return:
        """
        num = uuid.uuid4().int
        len_num = len(str(num))
        start_index = random.choice(range(len_num - length + 1))
        end_index = start_index + length
        return str(num)[start_index:end_index]

    @classmethod
    def unique_random(cls, length: int) -> str:
        """
        生成一个长度为 leng_unique 的随机数(不保证绝绝对对唯一，但是基本上不会出现重复的情况)
        :param length: 期望随机数的长度
        :return:
        :return type: str
        """
        num = uuid.uuid4().int
        len_num = len(str(num))
        start_index = random.choice(range(len_num - length + 1))
        end_index = start_index + length
        return str(num)[start_index:end_index]

    @classmethod
    def date_time(cls, days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0):
        """
        获取 过期时间点
        :param days:
        :param seconds:
        :param microseconds:
        :param milliseconds:
        :param minutes:
        :param hours:
        :param weeks:
        :return:
        """
        dtd = datetime.timedelta(days=days, seconds=seconds, microseconds=microseconds, milliseconds=milliseconds,
                                 minutes=minutes, hours=hours, weeks=weeks)
        return (datetime.datetime.now() + dtd).strftime("%Y-%m-%dT%H:%M:%S+08:00")
