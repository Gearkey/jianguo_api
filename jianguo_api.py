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

    # 通过 uuid 判断操作是否成功
    def is_success_by_uuid(self, path, uuid) -> bool:
        resp = self._get(self._host_url + path + json.loads(uuid)["uuid"])

        if json.loads(resp)["state"] == "SUCCESS": return True
        else: return False
    
    # 新建同步文件夹
    def creat_sandbox(self, name, acl_anonymous="0", acl_signed="0", desc="", do_not_sync="false") -> dict:
        data = {
            "acl_anonymous": acl_anonymous, ### to_know：是否匿名
            "acl_signed": acl_signed, ### to_know：是否签名
            "desc": desc, ### 同步文件夹描述
            "do_not_sync": do_not_sync, ### 是否不同步到本地
            "name": name, ### 同步文件夹名称
        }

        resp = self._post(self._host_url + "/d/ajax/sandbox/create", data)
        return json.loads(resp)
    
    # 删除同步文件夹
    def delete_sandbox(self, snd_id, snd_magic) -> int:
        self._post(self._host_url + "/d/ajax/sandbox/delete?sndId=" + snd_id + "&sndMagic=" + snd_magic, {})
        return jianguo_api.SUCCESS
    
    # 获取同步文件夹回收站列表
    def get_sandbox_rec_list(self) -> dict:
        file_list = self._get(self._host_url + "/d/ajax/sandbox/listTrash")
        return json.loads(file_list)

    # 从回收站恢复同步文件夹
    def recovery_sandbox(self, snd_id, snd_magic) -> int:
        self._post(self._host_url + "/d/ajax/sandbox/restore?sndId=" + snd_id + "&sndMagic=" + snd_magic, {})
        return jianguo_api.SUCCESS
    
    # 获取同步文件夹信息
    def get_sandbox_info(self, snd_id, snd_magic, path="/"):
        sandbox_info = self._get(self._host_url + "/d/ajax/sandbox/metaData?path=" + path + "&sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(sandbox_info)
    
    # 修改同步文件夹信息
    def update_sandbox_info(self, snd_id, snd_magic, name, do_not_sync, desc, acl_path, id, magic, acl_signed, acl_users, acl_groups) -> int:
        data = {
            "name": name,
            "do_not_sync": do_not_sync,
            "desc": desc,
            "acl_path": acl_path,
            "id": id,
            "magic": magic,
            "acl_signed": acl_signed,
            "acl_users": acl_users,
            "acl_groups": acl_groups,
        }

        self._post(self._host_url + "/d/ajax/sandbox/updateMetaData?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS

    # 新建文件
    def creat_file(self, snd_id, snd_magic, path, type="txt") -> int:
        if type == "txt": content_uri = "/static/others/empty.txt"
        else: content_uri = "/static/others/empty.txt"
        
        data = {
            "path": path,
            "content_uri": content_uri,
        }

        self._post(self._host_url + "/d/ajax/fileops/create?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS
    
    # 新建文件夹
    def creat_dir(self, snd_id, snd_magic, path) -> int:
        data = {
            "path": path,
        }

        self._post(self._host_url + "/d/ajax/dirops/create?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS

    # 删除项目
    def delete(self, snd_id, snd_magic, path, version, is_dir=False) -> int:
        data = {
            path: version,
        }

        if is_dir: delete_path = "/d/ajax/dirops/delete?sndId="
        else: delete_path = "/d/ajax/fileops/delete?sndId="

        self._post(self._host_url + delete_path + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS

    # 获取回收站文件列表
    def get_rec_file_list(self, snd_id, snd_magic, path) -> dict:
        file_list = self._get(self._host_url + "/d/ajax/listTrashDir" + path + "?sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(file_list)

    # 彻底删除回收站项目
    def delete_rec(self, snd_id, snd_magic, path, version) -> int:
        data = {
            path: version + " FILE",
        }

        self._post(self._host_url + "/d/ajax/purge?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS

    # 从回收站恢复文件
    def recovery(self, snd_id, snd_magic, path) -> int:
        data = {
            path: "",
        }
        
        ## 恢复后返回一个操作的 uuid，通过 uuid 判断操作是否成功
        uuid = self._post(self._host_url + "/d/ajax/restoreDel?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)

        if self.is_success_by_uuid("/d/ajax/restoreProgress?uuid=", uuid): return jianguo_api.SUCCESS
        else: return jianguo_api.FAILED

    # 获取文件列表
    def get_file_list(self, snd_id, snd_magic, path) -> dict:
        file_list = self._get(self._host_url + "/d/ajax/browse" + path + "?sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(file_list)

    # 移动/复制文件
    def move(self, snd_id, snd_magic, src_path, dst_dir, dst_snd_id="", dst_snd_magic="", is_copy=False) -> int:
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
        
        ## 如果是复制，需要改变地址
        if is_copy: move_path = "/d/ajax/submitCopy?sndId="
        else: move_path = "/d/ajax/submitMove?sndId="
        
        ## 移动后返回一个操作的 uuid，通过 uuid 判断操作是否成功
        uuid = self._post(self._host_url + move_path + dst_snd_id + "&sndMagic=" + dst_snd_magic, data)

        if self.is_success_by_uuid("/d/ajax/moveProgress?uuid=", uuid): return jianguo_api.SUCCESS
        else: return jianguo_api.FAILED

    # 重命名文件
    def rename(self, snd_id, snd_magic, path, dest_name, version, is_dir=False) -> int:
        if is_dir: type = "directory"
        else: type = "file"
        
        data = {
            "path": path,
            "type": type,
            "destName": dest_name,
            "version": version,
        }

        self._post(self._host_url + "/d/ajax/rename?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS
    