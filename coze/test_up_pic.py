import os
import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateImageRequest, CreateImageRequestBody, CreateImageResponse

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

        # 获取桌面路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        image_path = os.path.join(desktop_path, "ant.png")
        
        # 检查文件是否存在
        if not os.path.exists(image_path):
            print(f"错误：找不到图片文件 {image_path}")
            return
            
        print(f"正在处理图片：{image_path}")
        
        # 构造请求对象
        with open(image_path, "rb") as file:
            request: CreateImageRequest = CreateImageRequest.builder() \
                .request_body(CreateImageRequestBody.builder()
                    .image_type("message")
                    .image(file)
                    .build()) \
                .build()

            # 发起请求
            print("正在发送请求...")
            response: CreateImageResponse = client.im.v1.image.create(request)

            # 处理失败返回
            if not response.success():
                print(f"上传失败：")
                print(f"错误代码：{response.code}")
                print(f"错误信息：{response.msg}")
                print(f"日志ID：{response.get_log_id()}")
                print(f"详细响应：\n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
                return

            # 处理业务结果
            print("上传成功！")
            print("响应数据：")
            print(lark.JSON.marshal(response.data, indent=4))

    except Exception as e:
        print(f"发生错误：{str(e)}")

if __name__ == "__main__":
    main()