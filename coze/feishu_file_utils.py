import os
import json
import requests
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, DEBUG

class FeishuFileUtils:
    """飞书文件工具类，用于上传和下载各种类型的文件，使用消息附件API"""
    
    @staticmethod
    def get_tenant_access_token():
        """获取租户访问令牌，直接使用HTTP请求"""
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {
                "Content-Type": "application/json"
            }
            data = {
                "app_id": FEISHU_APP_ID,
                "app_secret": FEISHU_APP_SECRET
            }
            
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    return result.get("tenant_access_token")
                else:
                    print(f"获取令牌失败: {result.get('msg')}")
                    return None
            else:
                print(f"获取令牌请求失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"获取令牌时出错: {e}")
            return None
    
    @staticmethod
    def upload_file(file_path, file_name=None):
        """上传文件到飞书，使用消息附件API
        
        Args:
            file_path: 文件本地路径
            file_name: 上传后的文件名称，默认使用原文件名
            
        Returns:
            成功返回文件信息字典，失败返回None
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"错误：找不到文件 {file_path}")
                return None
                
            # 确定上传文件名
            if not file_name:
                file_name = os.path.basename(file_path)
                
            print(f"正在上传文件：{file_path} 到飞书，文件名: {file_name}")
            
            # 获取访问令牌
            token = FeishuFileUtils.get_tenant_access_token()
            if not token:
                return None
                
            # 构造请求头和数据
            url = "https://open.feishu.cn/open-apis/im/v1/files"
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            # 确定文件类型
            file_type = "stream"  # 默认为流文件
            extension = os.path.splitext(file_path)[1].lower()
            if extension in ['.jpg', '.jpeg', '.png', '.gif']:
                file_type = "image"
            elif extension in ['.mp3', '.wav', '.ogg']:
                file_type = "opus"  # 飞书音频类型
            
            # 构造表单数据
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name, f),
                    'file_type': (None, file_type),
                    'file_name': (None, file_name)
                }
                
                # 发送请求
                response = requests.post(url, headers=headers, files=files)
                
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    file_data = result.get("data", {})
                    file_info = {
                        "file_key": file_data.get("file_key"),
                        "name": file_name,
                        "type": file_type,
                        "size": os.path.getsize(file_path)
                    }
                    print(f"上传成功！文件key: {file_info['file_key']}")
                    return file_info
                else:
                    print(f"上传失败：{result.get('msg')}")
                    return None
            else:
                print(f"上传请求失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"上传文件时发生错误：{str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def download_file(file_key, save_path=None):
        """从飞书下载文件，使用消息附件API
        
        Args:
            file_key: 飞书文件key
            save_path: 保存路径，如不指定则保存到results文件夹
            
        Returns:
            成功返回保存路径，失败返回None
        """
        try:
            # 获取访问令牌
            token = FeishuFileUtils.get_tenant_access_token()
            if not token:
                return None
                
            # 构造请求头和URL
            url = f"https://open.feishu.cn/open-apis/im/v1/files/{file_key}"
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            print(f"正在下载文件，文件key: {file_key}")
            
            # 发送请求
            response = requests.get(url, headers=headers, stream=True)
            
            # 处理响应
            if response.status_code == 200:
                # 获取文件名（如果有）
                content_disposition = response.headers.get('Content-Disposition')
                filename = None
                if content_disposition and 'filename=' in content_disposition:
                    # 提取文件名
                    filename = content_disposition.split('filename=')[1].strip('"\'')
                
                # 确定保存路径
                if not save_path:
                    # 默认保存到results文件夹
                    results_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
                    os.makedirs(results_path, exist_ok=True)
                    
                    # 使用文件名或key
                    if filename:
                        save_path = os.path.join(results_path, filename)
                    else:
                        # 根据Content-Type推断扩展名
                        content_type = response.headers.get('Content-Type', '')
                        extension = FeishuFileUtils._get_extension_from_content_type(content_type)
                        save_path = os.path.join(results_path, f"feishu_file_{file_key[-8:]}{extension}")
                
                # 确保目录存在
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                    
                # 保存文件
                print(f"下载成功，正在保存到：{save_path}")
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print("文件保存完成！")
                return save_path
            else:
                try:
                    response_data = response.json()
                    print(f"下载失败：{response_data.get('msg')}")
                except:
                    print(f"下载失败：HTTP状态码 {response.status_code}")
                return None
                
        except Exception as e:
            print(f"下载文件时发生错误：{str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _get_extension_from_content_type(content_type):
        """根据Content-Type推断文件扩展名"""
        content_type = content_type.lower()
        
        # 常见MIME类型映射
        content_type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
            'video/mp4': '.mp4',
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'application/json': '.json',
            'text/plain': '.txt',
            'text/html': '.html',
            'text/css': '.css',
            'text/javascript': '.js',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        }
        
        return content_type_map.get(content_type, '.bin')


# 简单测试函数
def test_upload():
    # 上传测试
    file_path = os.path.join(os.path.expanduser("~"), "Desktop", "giraffe.mp3")
    file_info = FeishuFileUtils.upload_file(file_path)
    
    if file_info:
        print(json.dumps(file_info, indent=2, ensure_ascii=False))
        return file_info["file_key"]
    return None

def test_download(file_key):
    # 下载测试
    if file_key:
        save_path = FeishuFileUtils.download_file(file_key)
        print(f"下载保存路径: {save_path}")


if __name__ == "__main__":
    file_key = test_upload()
    if file_key:
        test_download(file_key) 