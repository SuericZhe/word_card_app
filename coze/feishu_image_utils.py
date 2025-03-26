import os
import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateImageRequest, CreateImageRequestBody, CreateImageResponse
from lark_oapi.api.im.v1 import GetImageRequest, GetImageResponse
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, DEBUG

class FeishuImageUtils:
    """飞书图片工具类，用于上传和下载图片"""
    
    @staticmethod
    def get_client():
        """获取飞书API客户端"""
        log_level = lark.LogLevel.DEBUG if DEBUG else lark.LogLevel.INFO
        return lark.Client.builder() \
            .app_id(FEISHU_APP_ID) \
            .app_secret(FEISHU_APP_SECRET) \
            .log_level(log_level) \
            .build()
    
    @staticmethod
    def upload_image(image_path):
        """上传图片到飞书
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            成功返回image_key，失败返回None
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(image_path):
                print(f"错误：找不到图片文件 {image_path}")
                return None
                
            print(f"正在上传图片：{image_path}")
            
            client = FeishuImageUtils.get_client()
            
            # 构造请求并上传
            with open(image_path, "rb") as file:
                request = CreateImageRequest.builder() \
                    .request_body(CreateImageRequestBody.builder()
                        .image_type("message")
                        .image(file)
                        .build()) \
                    .build()

                # 发起请求
                response = client.im.v1.image.create(request)

                # 处理失败返回
                if not response.success():
                    print(f"上传失败：{response.msg}")
                    return None

                # 获取image_key
                image_key = response.data.image_key
                print(f"上传成功！image_key: {image_key}")
                return image_key
                
        except Exception as e:
            print(f"上传图片时发生错误：{str(e)}")
            return None
    
    @staticmethod
    def download_image(image_key, save_path=None):
        """从飞书下载图片
        
        Args:
            image_key: 飞书图片key
            save_path: 保存路径，如不指定则保存到桌面
            
        Returns:
            成功返回保存路径，失败返回None
        """
        try:
            client = FeishuImageUtils.get_client()
            
            # 构造请求
            request = GetImageRequest.builder() \
                .image_key(image_key) \
                .build()
            
            print(f"正在下载图片，image_key: {image_key}")
            
            # 发起请求
            response = client.im.v1.image.get(request)

            # 处理失败返回
            if not response.success():
                print(f"下载失败：{response.msg}")
                return None

            # 确定保存路径
            if not save_path:
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                save_path = os.path.join(desktop_path, f"feishu_{image_key[-8:]}.png")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                
            # 保存文件
            print(f"下载成功，正在保存到：{save_path}")
            with open(save_path, "wb") as f:
                f.write(response.file.read())
            
            print("文件保存完成！")
            return save_path
                
        except Exception as e:
            print(f"下载图片时发生错误：{str(e)}")
            return None


# 简单测试函数
def test():
    # 上传测试
    image_path = os.path.join(os.path.expanduser("~"), "Desktop", "ant.png")
    image_key = FeishuImageUtils.upload_image(image_path)
    
    if image_key:
        # 下载测试
        FeishuImageUtils.download_image(image_key)


if __name__ == "__main__":
    test() 