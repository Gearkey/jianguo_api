import os
import re
import json
import urllib.request
import urllib.parse
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
            return jianguo_api.FAILED
        self._max_size = max_size
        return jianguo_api.SUCCESS

    # 获取账户基本信息
    def get_user_info(self) -> dict:
        ## fixme：处理后依然是 str
        resp = json.dumps(self._get(self._host_url + "/d/ajax/userop/getUserInfo"))
        return json.loads(resp)

    # 根据某键内容获取单个或多个 sandbox 信息
    def get_snd_info_by(self, name=None, snd_id=None, magic=None, owner=None, permission=None, caps=None, exclusive_user=None, is_default=None, is_owner=None, desc=None, used_space=None, is_deleted=False) -> list:
        if is_deleted:
            sandboxes = self.get_sandbox_rec_list()
        else:
            ### fixme：因为 get_user_info() 返回的是 str，暂时这样处理
            ### 获取用户信息中 sandbox 部分的内容，断点并且切割
            sandboxes_str = re.findall(r'"sandboxes":(.*?),"freeUpRate"', self.get_user_info())[0]
            sandboxes = json.loads(sandboxes_str)

        ## 根据输入条件筛选结果并返回（全部条件匹配）
        result = []
        for sandbox in sandboxes:
            is_match = True
            
            if (name != None) & (sandbox["name"] != name): is_match = False ### 名称，【我的坚果云】为空，str
            if (snd_id != None) & (sandbox["sandboxId"] != snd_id): is_match = False ### id，str
            if (magic != None) & (sandbox["magic"] != magic): is_match = False ### magic，str
            if not is_deleted:
                if (owner != None) & (sandbox["owner"] != owner): is_match = False ### 所有者，是邮件地址，str
                if (permission != None) & (sandbox["permission"] != permission): is_match = False ### toknow：权限等级，int
                if (caps != None) & (sandbox["caps"] != caps): is_match = False ### toknow：int
                if (exclusive_user != None) & (sandbox["exclusiveUser"] != exclusive_user): is_match = False ### 是否用户专属，一般情况仅【我的坚果云】，bool
                if (is_default != None) & (sandbox["isDefault"] != is_default): is_match = False ### toknow：是否默认位置，一般情况仅【我的坚果云】，bool
                if (is_owner != None) & (sandbox["isOwner"] != is_owner): is_match = False ### 是否为所有者，bool
                if (desc != None) & (sandbox["desc"] != desc): is_match = False ### 描述，默认为空，str
                if (used_space != None) & (sandbox["usedSpace"] != used_space): is_match = False ### 已用空间，单位 Byte，int
            
            if is_match: result.append(sandbox)
        return result

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
    
    # 获取用户 Cookie
    def get_cookie(self) -> dict:
        return self._cookies

    # 通过cookie登录
    def login_by_cookie(self, cookie: dict) -> int:
        self._cookies = cookie
        self._headers['cookie'] = self._cookies
        self._uesr_info = json.loads(self.get_user_info())

        return jianguo_api.SUCCESS

    # todo：账号密码登录
    def login(self, email, password) -> int:
        data = {
            "login_email": email,
            "login_password": password,
            "remember_me": "on",
            "login_dest_uri": "/d/home",
            "custom_ticket": "",
            "sig": "",
            "reusable": "false",
        }
        self._post(self._host_url + "/d/login", data)
        return jianguo_api.SUCCESS

    # 注销
    def logout(self) -> int:
        self._get(self._host_url + "/logout")
        self._cookies = None
        return jianguo_api.SUCCESS

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
    def delete_sandbox(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        self._post(self._host_url + "/d/ajax/sandbox/delete?sndId=" + snd_id + "&sndMagic=" + snd_magic, {})
        return jianguo_api.SUCCESS
    
    # 获取同步文件夹回收站列表
    def get_sandbox_rec_list(self) -> dict:
        file_list = self._get(self._host_url + "/d/ajax/sandbox/listTrash")
        return json.loads(file_list)["sandboxes"]

    # 从回收站恢复同步文件夹
    def recovery_sandbox(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path, is_deleted=True)
        
        self._post(self._host_url + "/d/ajax/sandbox/restore?sndId=" + snd_id + "&sndMagic=" + snd_magic, {})
        return jianguo_api.SUCCESS
    
    # 获取同步文件夹信息
    def get_sandbox_info(self, path, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        path = "/"

        sandbox_info = self._get(self._host_url + "/d/ajax/sandbox/metaData?path=" + path + "&sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(sandbox_info)
    
    # 修改同步文件夹信息
    def update_sandbox_info(self, name, new_name=None, do_not_sync=None, desc=None, acl_path=None, id=None, magic=None, acl_signed=None, acl_users=None, acl_groups=None) -> int:
        sandbox = self.get_sandbox_info(name)
        if sandbox["acls"] == []:
            sandbox["acls"] = [{"acl": {"anonymous": 0, "signed": 0, "users": {}, "userNicks": {}, "groups": []}, "path": "/"}]

        ## 如果某项为空，填充为已有或默认值
        if new_name == None: new_name = name ### sandbox 名称，str
        if do_not_sync == None: do_not_sync = sandbox["doNotSync"] ### 是否同步，str
        if desc == None: desc = sandbox["desc"] ### 描述，str
        if acl_path == None: acl_path = sandbox["acls"][0]["path"] ### fixme：权限位置，str
        if id == None: id = sandbox["id"] ### snd_id，str
        if magic == None: magic = sandbox["magic"] ### snd_magic，str
        if acl_signed == None: acl_signed = str(sandbox["acls"][0]["acl"]["signed"]) ### 未知，默认填充
        if acl_users == None: acl_users = str(sandbox["acls"][0]["acl"]["users"])[1:-1] ### fixme：用户
        if acl_groups == None: acl_groups = str(sandbox["acls"][0]["acl"]["groups"])[1:-1] ### fixme：用户组

        data = {
            "name": new_name,
            "do_not_sync": do_not_sync,
            "desc": desc,
            "acl_path": acl_path,
            "id": id,
            "magic": magic,
            "acl_signed": acl_signed,
            "acl_users": acl_users,
            "acl_groups": acl_groups,
        }

        self._post(self._host_url + "/d/ajax/sandbox/updateMetaData?sndId=" + sandbox["id"] + "&sndMagic=" + sandbox["magic"], data)
        return jianguo_api.SUCCESS

    # 新建文件
    def creat_file(self, path, type="txt", snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        if type == "txt": content_uri = "/static/others/empty.txt"
        else: content_uri = "/static/others/empty.txt"
        
        data = {
            "path": path,
            "content_uri": content_uri,
        }

        self._post(self._host_url + "/d/ajax/fileops/create?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS
    
    # 新建文件夹
    def creat_dir(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        data = {
            "path": path,
        }

        self._post(self._host_url + "/d/ajax/dirops/create?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS

    # todo：上传文件
    def upload_file(self, path, name, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        dir_name = os.path.split(path)[1]
        resp = self._post(self._host_url + "/d/ajax/fileops/uploadXHRV2?path=" + path + "&dirName=" + dir_name + "&sndId=" + snd_id + "&sndMagic=" + snd_magic + "&name=" + name, {})
        return json.loads(resp)

    # todo：上传文件夹
    def upload_dir(self, path, snd_id="", snd_magic="") -> int:
        self.creat_dir(path)
        return jianguo_api.SUCCESS

    # 删除项目
    def delete(self, path, is_dir=False, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        version = self.get_file_info(path, snd_id=snd_id, snd_magic=snd_magic)[0]["rev"]
        
        data = {
            path: version,
        }

        if is_dir: delete_path = "/d/ajax/dirops/delete?sndId="
        else: delete_path = "/d/ajax/fileops/delete?sndId="

        self._post(self._host_url + delete_path + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS

    # 获取回收站文件列表
    def get_rec_file_list(self, path, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        file_list = self._get(self._host_url + "/d/ajax/listTrashDir" + path + "?sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(file_list)

    # 彻底删除回收站项目
    # todo：建立获取回收站文件信息函数，自动获取文件版本
    def delete_rec(self, path, version, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        data = {
            path: version + " FILE",
        }

        self._post(self._host_url + "/d/ajax/purge?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)
        return jianguo_api.SUCCESS

    # 从回收站恢复文件
    def recovery(self, path, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        data = {
            path: "",
        }
        
        ## 恢复后返回一个操作的 uuid，通过 uuid 判断操作是否成功
        uuid = self._post(self._host_url + "/d/ajax/restoreDel?sndId=" + snd_id + "&sndMagic=" + snd_magic, data)

        if self.is_success_by_uuid("/d/ajax/restoreProgress?uuid=", uuid): return jianguo_api.SUCCESS
        else: return jianguo_api.FAILED

    # 获取文件列表
    def get_file_list(self, path, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        path = urllib.parse.quote(path)

        file_list = self._get(self._host_url + "/d/ajax/browse" + path + "?sndId=" + snd_id + "&sndMagic=" + snd_magic)
        return json.loads(file_list)
    
    # 通过条件获取文件信息
    def get_file_info(self, path, name=None, rev=None, is_dir=None, is_deleted=None, mtime=None, size=None, tbl_uri=None, aux_info=None, snd_id="", snd_magic="") -> list:
        ## 如果只传入了 path，则精确定位 name
        if (name == None) & (name==None) & (rev==None) & (is_dir==None) & (is_deleted==None) & (mtime==None) & (size==None) & (tbl_uri==None) & (aux_info==None):
            path, name = os.path.split(path)
        
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        files = self.get_file_list(path, snd_id=snd_id, snd_magic=snd_magic)["contents"]

        ## 根据输入条件筛选结果并返回（全部条件匹配）
        result = []
        for file in files:
            is_match = True
            
            if (name != None) & (file["name"] != name): is_match = False
            if (rev != None) & (file["rev"] != rev): is_match = False
            if (is_dir != None) & (file["isDir"] != is_dir): is_match = False
            if (is_deleted != None) & (file["isDeleted"] != is_deleted): is_match = False
            if (mtime != None) & (file["mtime"] != mtime): is_match = False
            if (size != None) & (file["size"] != size): is_match = False
            if (tbl_uri != None) & (file["tblUri"] != tbl_uri): is_match = False
            if (aux_info != None) & (file["auxInfo"] != aux_info): is_match = False
            
            if is_match: result.append(file)
        return result
    
    # 获取文件版本信息
    def get_file_version(self, path, is_deleted=False, snd_id="", snd_magic=""):
        if is_deleted: pass
        else: return self.get_file_info(path, snd_id=snd_id, snd_magic=snd_magic)[0]["rev"]

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

        if self.is_success_by_uuid("/d/ajax/moveProgress?uuid=", uuid): return jianguo_api.SUCCESS
        else: return jianguo_api.FAILED
    
    # 获取文件下载链接
    def get_file_link(self, path, snd_id="", snd_magic="") -> str:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        path = urllib.parse.quote(path)

        resp = self._get(self._host_url + "/d/ajax/dlink?sndId=" + snd_id + "&sndMagic=" + snd_magic + "&path=" + path)
        return self._host_url + json.loads(resp)["url"]

    # 重命名文件
    def rename(self, path, dest_name, is_dir=False, snd_id="", snd_magic="") -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        version = self.get_file_info(path, snd_id=snd_id, snd_magic=snd_magic)[0]["rev"]
        
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
        return jianguo_api.SUCCESS
    
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
        return jianguo_api.SUCCESS

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
        return jianguo_api.SUCCESS

    # 删除书签
    def delete_shortcut(self, name) -> int:
        path = self.DEFAULT_SHORTCUT_PATH + "/" + name + ".nslnk"
        self.delete(path)
        return jianguo_api.SUCCESS

    # 创建/编辑分享
    def share(self, path, acl_list=None, acl=None, disable_download=None, enable_upload=None, enable_watermark=None, enable_comment=None, snd_id="", snd_magic="") -> dict:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        ## 对于已存在的分享，默认使用已有信息，对于未存在的分享，使用初始值
        try:
            share_info = self.get_share_info(path, snd_id=snd_id, snd_magic=snd_magic)
            version = str(share_info["version"])
            if acl_list == None: acl_list = str(share_info["aclist"])
            if acl == None: acl = str(share_info["acl"])
            if disable_download == None: disable_download = str(share_info["downloadDisabled"])
            if enable_upload == None: enable_upload = str(share_info["enableUpload"])
            if enable_watermark == None: enable_watermark = str(share_info["enableWatermark"])
            if enable_comment == None: enable_comment = str(share_info["aclist"])
        except:
            version = str(self.get_file_version(path, snd_id=snd_id, snd_magic=snd_magic))
            if acl_list == None: acl_list = ""
            if acl == None: acl = "1"
            if disable_download == None: disable_download = "false"
            if enable_upload == None: enable_upload = "false"
            if enable_watermark == None: enable_watermark = "false"
            if enable_comment == None: enable_comment = "false"

        data = {
            "path": path,
            "acl_list": acl_list,
            "acl": acl,
            "disable_download": disable_download,
            "version": version,
            "enable_upload": enable_upload,
            "enable_watermark": enable_watermark,
            "enable_comment": enable_comment,
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
        return jianguo_api.SUCCESS

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
    def get_event(self, path, marker=0, page_num=1, snd_id="", snd_magic="", id=None, op_type=None, isdir=None, isdel=None, size=None, version=None, src_machine_name=None, editor_nick_name=None, editor_account=None, timestamp=None, is_virus=None, from_time=None, to_time=None) -> list:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)
        
        ## 如果 marker 不为0，则添加 marker 翻页标记参数
        url = self._host_url + "/d/ajax/getEvents?sndId=" + snd_id + "&sndMagic=" + snd_magic
        if marker != 0: url = url + "&marker=" + str(marker)
        
        try:
            resp = json.loads(self._get(url))
            events = resp["events"]
            marker = resp["marker"]
        except:
            pass

        ## 根据输入条件筛选结果并返回（全部条件匹配）
        result = []
        for event in events:
            is_match = True
            
            if (id != None) & (event["id"] != id): is_match = False ### id，操作唯一标识，str
            if (op_type != None) & (event["opType"] != op_type): is_match = False ### 操作类型，添加为 ADD，删除为 DELETE，编辑为 EDIT，重命名为 RENAME，恢复为 RESTORE，str
            if (path != "") & (event["path"] != path): is_match = False ### 文件路径，str
            if (isdir != None) & (event["isdir"] != isdir): is_match = False ### 是否为目录，bool
            if (isdel != None) & (event["isdel"] != isdel): is_match = False ### 是否已删除，bool
            if (size != None) & (event["size"] != size): is_match = False ### 文件大小，单位 Byte，int
            if (version != None) & (event["version"] != version): is_match = False ### 文件版本，str
            if (src_machine_name != None) & (event["srcMachineName"] != src_machine_name): is_match = False ### 执行操作的机器名称，客户端为一个 UUID，网页端为 "WebConsole"，str
            if (editor_nick_name != None) & (event["editorNickName"] != editor_nick_name): is_match = False ### 编辑者昵称，str
            if (editor_account != None) & (event["editorAccount"] != editor_account): is_match = False ### 编辑者账号邮箱，str
            if (timestamp != None) & (event["timestamp"] != timestamp): is_match = False ### 时间戳，int
            if (is_virus != None) & (event["isVirus"] != is_virus): is_match = False ### toknow：是否为病毒，bool
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
            
            page_result, marker = self.get_event(path, marker=marker, snd_id=snd_id, snd_magic=snd_magic, id=id, op_type=op_type, isdir=isdir, isdel=isdel, size=size, version=version, src_machine_name=src_machine_name, editor_nick_name=editor_nick_name, editor_account=editor_account, timestamp=timestamp, is_virus=is_virus, from_time=from_time, to_time=to_time)
            result.extend(page_result)
            page += 1

            if page_result[-1]["timestamp"] < from_time: break ### 如果本页的最后一个项目的时间已小于 from_time，结束循环
            
        return result, marker

    # 撤销操作历史
    def undo_event(self, path, page_num=0, snd_id="", snd_magic="", id=None, op_type=None, isdir=None, isdel=None, size=None, version=None, src_machine_name=None, editor_nick_name=None, editor_account=None, timestamp=None, is_virus=None, from_time=None, to_time=None) -> int:
        if snd_id == "": snd_id, snd_magic, path = self.path_cut(path)

        events = self.get_event(path, page_num=page_num, snd_id=snd_id, snd_magic=snd_magic, id=id, op_type=op_type, isdir=isdir, isdel=isdel, size=size, version=version, src_machine_name=src_machine_name, editor_nick_name=editor_nick_name, editor_account=editor_account, timestamp=timestamp, is_virus=is_virus, from_time=from_time, to_time=to_time)[0]
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

        return jianguo_api.SUCCESS
