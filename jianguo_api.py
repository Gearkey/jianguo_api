import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime

class Jianguo(object):
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
    DEFAULT_SANDBOX_NAME = "我的坚果云"
    DEFAULT_SHORTCUT_PATH = DEFAULT_SANDBOX_NAME + "/书签"
    MIX_EVENT_PAGE_NUM = 999

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
            return Jianguo.FAILED
        self._max_size = max_size
        return Jianguo.SUCCESS

    # 获取账户基本信息
    def get_user_info(self) -> dict:
        ## fixme：处理后依然是 str
        resp = json.dumps(self._get(self._host_url + "/d/ajax/userop/getUserInfo"))
        return json.loads(resp)

    # 根据某键内容获取单个或多个 sandbox 信息
    def get_snd_info_by(self, is_deleted=False, is_greedy=False, **kwargs) -> list:
        if is_deleted:
            sandboxes = self.get_sandbox_rec_list()
        else:
            ### fixme：因为 get_user_info() 返回的是 str，暂时这样处理
            ### 获取用户信息中 sandbox 部分的内容，断点并且切割
            sandboxes_str = re.findall(r'"sandboxes":(.*?),"freeUpRate"', self.get_user_info())[0]
            sandboxes = json.loads(sandboxes_str)
        
        return self.get_target_result(sandboxes, is_greedy, **kwargs)

    # 分解 path 为 snd_id、snd_magic 和 path
    def path_cut(self, path, is_deleted=False) -> tuple:
        path_debris = path.split("/")
        sandbox_name = path_debris[0]
        if sandbox_name == self.DEFAULT_SANDBOX_NAME: sandbox_name = ""

        path = ""
        for debri in path_debris[1:]:
            path += ("/" + debri)

        info = self.get_snd_info_by(name=sandbox_name, is_deleted=is_deleted)[0]
        return info["sandboxId"], info["magic"], path

    # 获取指定字典列表的筛选结果（默认非贪婪匹配）
    def get_target_result(self, items, is_greedy=False, **kwargs) -> list:
        result = []
        for item in items:
            if is_greedy:
                is_match = False
                for key, value in kwargs.items():
                    if item[key] == value:
                        is_match = True
                        break
            else:
                is_match = True
                for key, value in kwargs.items():
                    if item[key] != value:
                        is_match = False
                        break
            
            if is_match: result.append(item)
        return result
    
    # 获取用户 Cookie
    def get_cookie(self) -> dict:
        return self._cookies

    # 通过cookie登录
    def login_by_cookie(self, cookie: dict) -> int:
        self._cookies = cookie
        self._headers['cookie'] = self._cookies
        self._uesr_info = json.loads(self.get_user_info())

        return Jianguo.SUCCESS

    # 注销
    def logout(self) -> int:
        self._get(self._host_url + "/logout")
        self._cookies = None
        return Jianguo.SUCCESS

    # 通过 uuid 判断操作是否成功
    def is_success_by_uuid(self, path, uuid) -> bool:
        resp = self._get(self._host_url + path + json.loads(uuid)["uuid"])

        if json.loads(resp)["state"] == "SUCCESS": return True
        else: return False
    
    # 新建同步文件夹
    def creat_sandbox(self, name, **kwargs) -> dict:
        data = {
            "acl_anonymous": kwargs.get("acl_anonymous", "0"),
            "acl_signed": kwargs.get("acl_signed", "0"),
            "desc": kwargs.get("desc", ""),
            "do_not_sync": kwargs.get("do_not_sync", "true"),
            "name": name,
        }

        resp = self._post(self._host_url + "/d/ajax/sandbox/create", data)
        return json.loads(resp)
    
    # 删除同步文件夹
    def delete_sandbox(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        self._post(self._host_url + "/d/ajax/sandbox/delete?sndId=" + snd_id + "&sndMagic=" + snd_magic, {})
        return Jianguo.SUCCESS
    
    # 获取同步文件夹回收站列表
    def get_sandbox_rec_list(self) -> dict:
        file_list = self._get(self._host_url + "/d/ajax/sandbox/listTrash")
        return json.loads(file_list)["sandboxes"]

    # 从回收站恢复同步文件夹
    def recovery_sandbox(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path, is_deleted=True)
        
        self._post(self._host_url + "/d/ajax/sandbox/restore?sndId=" + snd_id + "&sndMagic=" + snd_magic, {})
        return Jianguo.SUCCESS
    
    # 获取同步文件夹信息
    def get_sandbox_info(self, path, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        path = "/"

        sandbox_info = self._get(self._host_url + "/d/ajax/sandbox/metaData?path=" + path + "&sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(sandbox_info)
    
    # 修改同步文件夹信息
    def update_sandbox_info(self, original_name, **kwargs) -> int:
        sandbox = self.get_sandbox_info(original_name)
        if sandbox["acls"] == []:
            sandbox["acls"] = [{"acl": {"anonymous": 0, "signed": 0, "users": {}, "userNicks": {}, "groups": []}, "path": "/"}]

        ## 如果某项为空，填充为已有或默认值
        for key, value in kwargs.items():
            sandbox[key] = value

        data = {
            "name": sandbox["name"],
            "do_not_sync": sandbox["doNotSync"],
            "desc": sandbox["desc"],
            "acl_path": sandbox["acls"][0]["path"],
            "id": sandbox["id"],
            "magic": sandbox["magic"],
            "acl_signed": str(sandbox["acls"][0]["acl"]["signed"]),
            "acl_users": str(sandbox["acls"][0]["acl"]["users"])[1:-1],
            "acl_groups": str(sandbox["acls"][0]["acl"]["groups"])[1:-1],
        }

        self._post(self._host_url + "/d/ajax/sandbox/updateMetaData?sndId=" + sandbox["id"] + "&sndMagic=" + sandbox["magic"], data)
        return Jianguo.SUCCESS

    # 新建文件
    def creat_file(self, path, snd_id="", snd_magic="", type="txt") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        if type == "txt": content_uri = "/static/others/empty.txt"
        else: content_uri = "/static/others/empty.txt"
        
        data = {
            "path": path,
            "content_uri": content_uri,
        }

        self._post(self._host_url + "/d/ajax/fileops/create?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return Jianguo.SUCCESS
    
    # 新建文件夹
    def creat_dir(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        data = {
            "path": path,
        }

        self._post(self._host_url + "/d/ajax/dirops/create?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return Jianguo.SUCCESS

    # 删除项目
    def delete(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        file = self.get_file_info(path, snd_id, snd_magic)[0]
        
        data = {
            path: file["rev"],
        }

        if file["isDir"]: delete_path = "/d/ajax/dirops/delete?sndId="
        else: delete_path = "/d/ajax/fileops/delete?sndId="

        self._post(self._host_url + delete_path + snd_id + "&sndMagic=" + snd_magic, data)
        return Jianguo.SUCCESS

    # 彻底删除回收站项目
    def delete_rec(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        version = self.get_rec_file_info(path, snd_id=snd_id, snd_magic=snd_magic)[0]["version"]
        
        data = {
            path: str(version) + " FILE",
        }

        self._post(self._host_url + "/d/ajax/purge?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return Jianguo.SUCCESS

    # 从回收站恢复文件
    def recovery(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        data = {
            path: "",
        }
        
        ## 恢复后返回一个操作的 uuid，通过 uuid 判断操作是否成功
        uuid = self._post(self._host_url + "/d/ajax/restoreDel?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)

        if self.is_success_by_uuid("/d/ajax/restoreProgress?uuid=", uuid): return Jianguo.SUCCESS
        else: return Jianguo.FAILED

    # 获取文件列表
    def get_file_list(self, path, snd_id="", snd_magic="", is_deleted=False) -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        path = urllib.parse.quote(path)

        if is_deleted:
            file_list = self._get(self._host_url + "/d/ajax/listTrashDir" + path + "?sndId=" + snd_id + "&sndMagic=" + snd_magic)
        else:
            file_list = self._get(self._host_url + "/d/ajax/browse" + path + "?sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(file_list)
    
    # 通过条件获取文件信息
    def get_file_info(self, path, snd_id="", snd_magic="", is_deleted=False, is_greedy=False, **kwargs) -> list:
        ## 如果只传入了 path，且没有其他筛选参数，则精确定位 name
        path, name = os.path.split(path)
        kwargs["name"] = kwargs.get("name", name)
        
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        files = self.get_file_list(path, snd_id, snd_magic, is_deleted)["contents"]
        
        return self.get_target_result(files, is_greedy, **kwargs)

    # 移动/复制文件
    # todo：实现路径到路径的操作，目前是路径到目标目录
    # todo：如果没填目标路径则使用 src_path 信息的判断
    def move(self, src_path, dst_dir, is_copy=False, snd_id="", snd_magic="", dst_snd_id="", dst_snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, src_path = self.path_cut(src_path)
        if dst_snd_id == "": dst_snd_id, dst_snd_magic, dst_dir = self.path_cut(dst_dir)
        
        data = {
            "srcSndId": snd_id,
            "srcSndMagic": snd_magic,
            "srcPath": src_path,
            "dstDir": dst_dir,
        }
        
        ## 如果是复制，需要改变地址
        if is_copy: move_path = "/d/ajax/submitCopy?sndId="
        else: move_path = "/d/ajax/submitMove?sndId="
        
        ## 移动后返回一个操作的 uuid，通过 uuid 判断操作是否成功
        uuid = self._post(self._host_url + move_path + dst_snd_id + "&sndMagic=" + dst_snd_magic, data)

        if self.is_success_by_uuid("/d/ajax/moveProgress?uuid=", uuid): return Jianguo.SUCCESS
        else: return Jianguo.FAILED
    
    # 获取文件下载链接
    def get_file_link(self, path, snd_id="", snd_magic="") -> str:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        path = urllib.parse.quote(path)

        resp = self._get(self._host_url + "/d/ajax/dlink?sndId=" + snd_id + "&sndMagic=" + snd_magic + "&path=" + path)
        return self._host_url + json.loads(resp)["url"]

    # 重命名文件
    def rename(self, path, dest_name, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        file = self.get_file_info(path, snd_id, snd_magic)[0]
        
        if file["isDir"]: type = "directory"
        else: type = "file"
        
        data = {
            "path": path,
            "type": type,
            "destName": dest_name,
            "version": file["rev"],
        }

        self._post(self._host_url + "/d/ajax/rename?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return Jianguo.SUCCESS
    
    # 获取文件历史
    def get_file_version_list(self, path, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        version_list = self._get(self._host_url + "/d/ajax/versions" + path + "?sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(version_list)

    # 获取文件历史版本下载链接
    def get_file_version_link(self, path, version, snd_id="", snd_magic="") -> str:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        resp = self._get(self._host_url + "/d/ajax/dlink?sndId=" + snd_id + "&sndMagic=" + snd_magic + "&path=" + path + "&ver=" + version)
        return self._host_url + json.loads(resp)["url"]
    
    # 恢复文件历史版本
    def recovery_file_version(self, path, version, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        data = {
            "path": path,
            "version": version,
        }

        self._post(self._host_url + "/d/ajax/fileops/restore?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return Jianguo.SUCCESS
    
    # 获取应用密码
    def get_asps(self) -> dict:
        resp = self._get(self._host_url + "/d/ajax/userop/getAsps")
        return json.loads(resp)
    
    # 创建应用密码
    def generate_asp(self, asp_name) -> dict:
        data = {
            "asp_name": asp_name,
        }

        resp = self._post(self._host_url + "/d/ajax/userop/generateAsp", data)
        return json.loads(resp)
    
    # 移除应用密码
    def revoke_asp(self, asp_name) -> int:
        data = {
            "asp_name": asp_name,
        }

        self._post(self._host_url + "/d/ajax/userop/revokeAsp", data)
        return Jianguo.SUCCESS

    # 获取书签列表
    def get_shortcut_list(self) -> dict:
        return self.get_file_list(self.DEFAULT_SHORTCUT_PATH)

    # 创建书签
    def create_shortcut(self, path, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, dest_path = self.path_cut(path)
        
        data = {
            "destPath": dest_path,
        }

        resp = self._post(self._host_url + "/d/ajax/fileops/createShortcut?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return json.loads(resp)
    
    # 获取书签位置
    def get_shortcut_location(self, name) -> dict:
        url = self.get_file_link(self.DEFAULT_SHORTCUT_PATH + "/" + name + ".nslnk")
        resp = self._get(url)
        return json.loads(resp)
    
    # 重命名书签
    def rename_shortcut(self, name, dest_name) -> int:
        path = self.DEFAULT_SHORTCUT_PATH + "/" + name + ".nslnk"
        
        self.rename(path, dest_name+".nslnk")
        return Jianguo.SUCCESS

    # 删除书签
    def delete_shortcut(self, name) -> int:
        path = self.DEFAULT_SHORTCUT_PATH + "/" + name + ".nslnk"
        self.delete(path)
        return Jianguo.SUCCESS

    # 创建/编辑分享
    def share(self, path, snd_id="", snd_magic="", **kwargs) -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        ## 对于已存在的分享，默认使用已有信息，对于未存在的分享，使用初始值
        try:
            share_info = self.get_share_info(path, snd_id, snd_magic)
            for key, value in kwargs.items():
                share_info[key] = value
        except:
            pass
        
        data = {
            "path": path,
            "acl_list": share_info.get("aclist", ""),
            "acl": share_info.get("acl", 1),
            "disable_download": share_info.get("downloadDisabled", False),
            "version": share_info.get("version", 1),
            "enable_upload": share_info.get("enableUpload", False),
            "enable_watermark": share_info.get("enableWatermark", False),
            "enable_comment": False,
        }

        resp = self._post(self._host_url + "/d/ajax/dirops/pub?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return json.loads(resp)

    # 移除分享
    def delete_share(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        ## 文件或文件夹需要区分一下
        if self.get_share_list_info(path, snd_id=snd_id, snd_magic=snd_magic)["type"] == "directory": path += "|directory"
        else: path += "|file"

        data = {
            path: "dummy",
        }

        self._post(self._host_url + "/d/ajax/pubops/revoke?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return Jianguo.SUCCESS

    # 获取分享信息
    def get_share_info(self, path, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        resp = self._get(self._host_url + "/d/ajax/pubInfo?path=" + path + "&sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(resp)
    
    # 获取指定 path 的分享列表信息
    def get_share_list_info(self, path, snd_id="", snd_magic="") -> list:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)

        try:
            resp = self._get(self._host_url + "/d/ajax/pubops/list/?sndId=" + snd_id + "&sndMagic=" + snd_magic)
            shares = json.loads(resp)["objects"]
        except:
            pass

        ## 如果 path 仅为 sandbox，则返回其下所有分享信息，否则返回单个分享的信息
        if path == "":
            return shares
        else:
            for share in shares:
                if path == share["path"]: return share

    # 获取 sandbox 操作历史列表，可指定翻页标记 marker 和获取页数 page_num，以及通过属性筛选结果
    def get_event(self, original_path, marker=0, page_num=1, snd_id="", snd_magic="", from_time=None, to_time=None, is_greedy=False, **kwargs) -> list:
        if snd_id == "": snd_id, snd_magic, original_path = self.path_cut(original_path)
        kwargs["path"] = kwargs.get("path", original_path)
        
        ## 如果 marker 不为0，则添加 marker 翻页标记参数
        # print(type(snd_id), type(snd_magic))
        url = self._host_url + "/d/ajax/getEvents?sndId=" + snd_id + "&sndMagic=" + snd_magic
        if marker != 0: url = url + "&marker=" + str(marker)
        
        try:
            resp = json.loads(self._get(url))
            events = resp["events"]
            marker = resp["marker"]
        except:
            pass

        events = self.get_target_result(events, is_greedy, **kwargs)

        ## 时间筛选
        result = []
        for event in events:
            is_match = True

            if from_time != None:
                if event["timestamp"] < from_time: is_match = False ### 起始时间
            if to_time != None:
                if event["timestamp"] >= to_time: is_match = False ### 终止时间
            if is_match: result.append(event)

        ## 如果页数为0，即需要找到能获取结果的第一页
        if page_num == 0: page = -self.MIX_EVENT_PAGE_NUM
        else: page = 1

        ## 递归调用，并合并列表，目前每页100条信息
        while page < page_num:
            if marker == 1: break ### 如果 marker 为1，表示到达最终页，结束循环
            if page_num == 0:
                if result != []: break ### 如果 page_num 为0，且结果已不为空，结束循环
            
            page_result, marker = self.get_event(original_path, marker, page_num, snd_id, snd_magic, from_time, to_time, is_greedy, **kwargs)
            result.extend(page_result)
            page += 1

            # if page_result[-1]["timestamp"] < from_time: break ### 如果本页的最后一个项目的时间已小于 from_time，结束循环
            
        return result, marker

    # 撤销操作历史
    def undo_event(self, path, snd_id="", snd_magic="", **kwargs) -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)

        events = self.get_event(path, snd_id=snd_id, snd_magic=snd_magic, **kwargs)[0]
        for event in events:
            data = {
                "optype": event["opType"],
                "path": event["path"],
                "deleted": str(event["isdel"]),
                "dir": event["isdir"],
                "version": event["version"],
            }

            try:
                resp = self._post(self._host_url + "/d/ajax/fileops/undoEvents?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
            except:
                pass

        return Jianguo.SUCCESS
