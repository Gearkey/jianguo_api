import os
import re
import json
import urllib.request
from datetime import datetime

class jianguo_api(object):
    FAILED = -1
    SUCCESS = 0
    ID_ERROR = 1
    PASSWORD_ERROR = 2
    LACK_PASSWORD = 3
    ZIP_ERROR = 4
    MKDIR_ERROR = 5
    URL_INVALID = 6
    FILE_CANCELLED = 7
    PATH_ERROR = 8
    NETWORK_ERROR = 9
    CAPTCHA_ERROR = 10
    OFFICIAL_LIMITED = 11

    def __init__(self):
        self._host_url = "https://www.jianguoyun.com"
        self._cookies = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Referer": "https://www.jianguoyun.com/",
            "TE": "Trailers",
        }
    
    def _get(self, url):
        request = urllib.request.Request(url=url, headers=self._headers)
        response = urllib.request.urlopen(request)

        return response.read().decode("utf-8")
    
    def _post(self, url, data):
        datas = urllib.parse.urlencode(data).encode("utf-8")
        
        request = urllib.request.Request(url=url, headers=self._headers, data=datas)
        response = urllib.request.urlopen(request)

        return response.read().decode("utf-8")

    # 设置单文件大小限制（网页版限制500M）
    def set_max_size(self, max_size=500) -> int:
        if max_size < 500:
            return jianguo_api.FAILED
        self._max_size = max_size
        return jianguo_api.SUCCESS

    # 获取账户基本信息
    def get_user_info(self) -> dict:
        return self._get(self._host_url + "/d/ajax/userop/getUserInfo")
    
    # 获取 snd_magic
    def get_snd_magic(self) -> str:
        snd_magic = ""

        return snd_magic
    
    # 获取用户 Cookie
    def get_cookie(self) -> dict:
        return self._cookies

    # 通过cookie登录
    def login_by_cookie(self, cookie: dict) -> int:
        self._cookies = cookie
        self._headers['cookie'] = self._cookies
        self._uesr_info = json.loads(self.get_user_info())

        return jianguo_api.SUCCESS

    # 注销
    def logout(self) -> int:
        pass

    # 删除项目
    def delete(self, fid, is_file=True) -> int:
        return jianguo_api.SUCCESS

    # 从回收站恢复指定项目
    def clean_rec(self) -> int:
        pass

    # 获取回收站文件夹列表
    def get_rec_dir_list(self) -> list:
        pass

    # 彻底删除回收站项目
    def delete_rec(self, fid, is_file=True) -> int:
        pass

    # 从回收站恢复文件
    def recovery(self, fid, is_file=True) -> int:
        pass

    # 获取文件列表
    def get_file_list(self, snd_id, snd_magic, path) -> dict:
        file_list = self._get(self._host_url + "/d/ajax/browse" + path + "?sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(file_list)

    # 移动文件
    def move_file(self, snd_id, snd_magic, src_path, dst_dir, dst_snd_id="", dst_snd_magic="") -> int:
        data = {
            "srcSndId": snd_id,
            "srcSndMagic": snd_magic,
            "srcPath": src_path,
            "dstDir": dst_dir,
        }

        ## 如果没填目标根文件夹的 snd_id 和 snd_magic，即在本根目录内移动
        if dst_snd_id == "":
            dst_snd_id = snd_id
            dst_snd_magic = snd_magic
        
        ## 移动后返回一个操作的 uuid，通过 uuid 判断操作是否成功
        uuid = self._post(self._host_url + "/d/ajax/submitMove?sndId=" + dst_snd_id + "&sndMagic=" + dst_snd_magic, data)
        resp = self._get(self._host_url + "/d/ajax/moveProgress?uuid=" + json.loads(uuid)["uuid"])

        if json.loads(resp)["state"] == "SUCCESS": return jianguo_api.SUCCESS
        else: return jianguo_api.FAILED

    # 重命名文件
    def rename_file(self, folder_id, folder_name) -> int:
        pass
    
    # 重命名文件夹
    def rename_dir(self, folder_id, folder_name) -> int:
        pass
    