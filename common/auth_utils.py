import datetime
import json
import base64
import random
import uuid

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5


def read_key_file(key_file_path):
    print("Reading private key from {}".format(key_file_path))
    if key_file_path == "":
        print("请输入密钥路径")
        return
    with open(key_file_path, mode='rb') as f:
        key = RSA.import_key(f.read())
    return key


def sign(key, data: dict):
    pkcs = PKCS1_v1_5.new(key)
    sha256_hash = SHA256.new(json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
    return base64.b64encode(pkcs.sign(sha256_hash)).decode('utf-8')


dev_pri_key = read_key_file("/Users/lizhankang/Documents/shouqianba/pems/dev/1024/clientPriKey.pem")
# dev_pri_key = ""
prod_pri_key = read_key_file("/Users/lizhankang/Documents/shouqianba/pems/prod/700001/clientPriKey.pem")
# prod_pri_key = ""


class AuthUtils(object):
    # dev_pri_key = read_key_file("/Users/lizhankang/Documents/shouqianba/pems/dev/1024/clientPriKey.pem")
    # prod_pri_key = read_key_file("/Users/lizhankang/Documents/shouqianba/pems/prod/700001/clientPriKey.pem")

    def __init__(self, environment):
        self.environment = environment
        self.appid = "28lpm3781001" if self.environment != "prod" else "28lpm0000002"

    def signature(self, data: dict):
        request_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
        body = {
            "request": {
                "head": {"appid": self.appid, "request_time": request_time, "sign_type": "SHA256",
                         "version": "1.0.0"},
                "body": data
            },
            "signature": None
        }
        pri_key = dev_pri_key if self.environment != "prod" else prod_pri_key
        body['signature'] = sign(pri_key, body['request'])
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


# class AuthUtils2(object):
#     dev_pri_key = read_key_file("/Users/lizhankang/Documents/shouqianba/pems/dev/1024/clientPriKey.pem")
#     prod_pri_key = read_key_file("/Users/lizhankang/Documents/shouqianba/pems/prod/700001/clientPriKey.pem")
#
#     def __init__(self, environment):
#         self.envir = environment
#         self.appid = "28lpm3781001" if self.envir != "prod" else "28lpm0000002"
#
#     def signature(self, data: dict):
#         request_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
#         body = {
#             "request": {
#                 "head": {"appid": self.appid, "request_time": request_time, "sign_type": "SHA256",
#                          "version": "1.0.0"},
#                 "body": data
#             },
#             "signature": None
#         }
#         body['signature'] = sign(AuthUtils2.dev_pri_key, body['request'])
#         return body
#
#     @classmethod
#     def random_num_str(cls, length: int) -> str:
#         """
#         返回一个长度为 length 的纯数字字符串
#         :param length:
#         :return:
#         """
#         num = uuid.uuid4().int
#         len_num = len(str(num))
#         start_index = random.choice(range(len_num - length + 1))
#         end_index = start_index + length
#         return str(num)[start_index:end_index]
#
#     @classmethod
#     def unique_random(cls, length: int) -> str:
#         """
#         生成一个长度为 leng_unique 的随机数(不保证绝绝对对唯一，但是基本上不会出现重复的情况)
#         :param length: 期望随机数的长度
#         :return:
#         :return type: str
#         """
#         num = uuid.uuid4().int
#         len_num = len(str(num))
#         start_index = random.choice(range(len_num - length + 1))
#         end_index = start_index + length
#         return str(num)[start_index:end_index]
#
#     @classmethod
#     def date_time(cls, days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0):
#         """
#         获取 过期时间点
#         :param days:
#         :param seconds:
#         :param microseconds:
#         :param milliseconds:
#         :param minutes:
#         :param hours:
#         :param weeks:
#         :return:
#         """
#         dtd = datetime.timedelta(days=days, seconds=seconds, microseconds=microseconds, milliseconds=milliseconds,
#                                  minutes=minutes, hours=hours, weeks=weeks)
#         return (datetime.datetime.now() + dtd).strftime("%Y-%m-%dT%H:%M:%S+08:00")




