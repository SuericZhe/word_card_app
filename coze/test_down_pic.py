import os
import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import GetImageRequest, GetImageResponse

# SDK 使用说明: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python--sdk/preparations-before-development
# 以下示例代码默认根据文档示例值填充，如果存在代码问题，请在 API 调试台填上相关必要参数后再复制代码使用
# 复制该 Demo 后, 需要将 "YOUR_APP_ID", "YOUR_APP_SECRET" 替换为自己应用的 APP_ID, APP_SECRET.
def main():
    try:
        # 创建client
        client = lark.Client.builder() \
            .app_id("cli_a769cd7901ac100e") \
            .app_secret("JaCmFgaAoqvqYnvEiwKBQb2DW5F7CzFf") \
            .log_level(lark.LogLevel.DEBUG) \
            .build()

        # 构造请求对象
        image_key = "img_v3_02ko_de1fe76f-d95f-45db-ad59-a9092454e8cg"
        request: GetImageRequest = GetImageRequest.builder() \
            .image_key(image_key) \
            .build()

        print(f"正在下载图片，image_key: {image_key}")
        
        # 发起请求
        response: GetImageResponse = client.im.v1.image.get(request)

        # 处理失败返回
        if not response.success():
            print("下载失败：")
            print(f"错误代码：{response.code}")
            print(f"错误信息：{response.msg}")
            print(f"日志ID：{response.get_log_id()}")
            print(f"详细响应：\n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # 获取下载目录（使用桌面）
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        file_name = f"downloaded_{image_key}.png"
        file_path = os.path.join(desktop_path, file_name)

        # 处理业务结果
        print(f"下载成功，正在保存到：{file_path}")
        with open(file_path, "wb") as f:
            f.write(response.file.read())
        
        print("文件保存完成！")

    except Exception as e:
        print(f"发生错误：{str(e)}")

if __name__ == "__main__":
    main()