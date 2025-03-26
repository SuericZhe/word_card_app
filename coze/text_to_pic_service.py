#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
提供小作文文字转图片的Web服务
通过REST API接口供前端调用
"""

import os
import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from text_to_pic import TextToPicture
import traceback

# 创建Flask应用
app = Flask(__name__)

# 配置CORS以允许跨域请求（如果需要）
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route('/api/text-to-pic', methods=['POST'])
def text_to_pic():
    """
    将文本转换为图片的API
    
    请求JSON格式:
    {
        "text": "要转换的小作文文本",
        "title": "可选的标题",
        "font_size": 36,  // 可选的字体大小
        "line_spacing": 1.5,  // 可选的行间距
        "return_base64": true  // 是否返回Base64编码的图片数据
    }
    
    响应JSON格式:
    {
        "success": true,
        "message": "图片生成成功",
        "image_path": "生成图片的路径",
        "image_url": "图片URL（如果配置了Web访问）",
        "image_base64": "Base64编码的图片（如果请求中return_base64为true）"
    }
    """
    try:
        # 获取请求数据
        data = request.get_json()
        
        # 验证必需参数
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需的参数: text'
            }), 400
        
        # 获取参数
        text = data.get('text')
        title = data.get('title')
        font_size = data.get('font_size')
        line_spacing = data.get('line_spacing')
        return_base64 = data.get('return_base64', False)
        
        # 创建TextToPicture实例
        processor = TextToPicture(font_size=font_size, line_spacing=line_spacing)
        
        # 生成图片
        output_path = processor.create_image(text=text, title=title)
        
        if not output_path:
            return jsonify({
                'success': False,
                'message': '图片生成失败'
            }), 500
        
        # 准备响应数据
        response_data = {
            'success': True,
            'message': '图片生成成功',
            'image_path': output_path,
        }
        
        # 如果需要返回Base64编码的图片
        if return_base64:
            try:
                with open(output_path, 'rb') as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                    response_data['image_base64'] = encoded_image
            except Exception as e:
                print(f"读取图片并编码为Base64时出错: {e}")
                response_data['message'] += '，但Base64编码失败'
        
        # 返回成功响应
        return jsonify(response_data)
        
    except Exception as e:
        # 记录异常
        print(f"处理请求时出错: {e}")
        traceback.print_exc()
        
        # 返回错误响应
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/get-image/<filename>', methods=['GET'])
def get_image(filename):
    """
    提供图片下载的API
    
    URL参数:
    - filename: 图片文件名
    
    返回:
    - 图片文件
    """
    try:
        # 构建图片路径
        # 注意：这里的路径应该限制在指定目录内，以防止任意文件访问
        results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "essays")
        image_path = os.path.join(results_dir, filename)
        
        # 验证文件存在
        if not os.path.exists(image_path):
            return jsonify({
                'success': False,
                'message': f'图片不存在: {filename}'
            }), 404
        
        # 验证文件是否在允许的目录中（防止目录遍历攻击）
        real_path = os.path.realpath(image_path)
        if not real_path.startswith(os.path.realpath(results_dir)):
            return jsonify({
                'success': False,
                'message': '无效的文件路径'
            }), 403
        
        # 返回图片文件
        return send_file(image_path, mimetype='image/png')
        
    except Exception as e:
        # 记录异常
        print(f"获取图片时出错: {e}")
        traceback.print_exc()
        
        # 返回错误响应
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/api/font-list', methods=['GET'])
def list_fonts():
    """
    列出可用字体的API
    
    返回:
    包含可用字体列表的JSON
    """
    try:
        # 获取可用字体
        fonts = TextToPicture.find_available_fonts()
        
        # 过滤和处理字体列表，只保留文件名而不是完整路径
        readable_fonts = []
        for font_path in fonts:
            font_name = os.path.basename(font_path)
            readable_fonts.append({
                "name": font_name,
                "path": font_path
            })
        
        return jsonify({
            'success': True,
            'fonts': readable_fonts
        })
        
    except Exception as e:
        # 记录异常
        print(f"获取字体列表时出错: {e}")
        traceback.print_exc()
        
        # 返回错误响应
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


@app.route('/', methods=['GET'])
def index():
    """API根路径，返回一个简单的HTML页面用于测试"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>小作文转图片服务</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #333; }
            textarea { width: 100%; height: 200px; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; }
            input[type="text"] { width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; }
            button { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background-color: #45a049; }
            #result { margin-top: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background-color: #f9f9f9; }
            img { max-width: 100%; margin-top: 10px; border: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>小作文转图片服务</h1>
            <div>
                <label for="text">输入小作文内容：</label>
                <textarea id="text" placeholder="请输入小作文内容..."></textarea>
            </div>
            <div>
                <label for="title">标题（可选）：</label>
                <input type="text" id="title" placeholder="输入标题...">
            </div>
            <div>
                <label for="fontSize">字体大小（可选）：</label>
                <input type="number" id="fontSize" placeholder="默认为36" value="36">
            </div>
            <div>
                <button onclick="convertToImage()">生成图片</button>
            </div>
            <div id="result" style="display: none;">
                <h3>生成结果：</h3>
                <p id="message"></p>
                <div id="imageContainer"></div>
            </div>
        </div>

        <script>
            function convertToImage() {
                const text = document.getElementById('text').value;
                const title = document.getElementById('title').value;
                const fontSize = document.getElementById('fontSize').value;
                
                if (!text) {
                    alert('请输入小作文内容');
                    return;
                }
                
                // 准备API请求数据
                const requestData = {
                    text: text,
                    return_base64: true
                };
                
                if (title) requestData.title = title;
                if (fontSize) requestData.font_size = parseInt(fontSize);
                
                // 显示加载状态
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                document.getElementById('message').textContent = '图片生成中，请稍候...';
                document.getElementById('imageContainer').innerHTML = '';
                
                // 发送API请求
                fetch('/api/text-to-pic', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('message').textContent = data.message;
                    
                    if (data.success && data.image_base64) {
                        // 显示生成的图片
                        const img = document.createElement('img');
                        img.src = 'data:image/png;base64,' + data.image_base64;
                        document.getElementById('imageContainer').appendChild(img);
                        
                        // 添加下载链接
                        const downloadLink = document.createElement('a');
                        downloadLink.href = img.src;
                        downloadLink.download = 'essay_' + new Date().getTime() + '.png';
                        downloadLink.textContent = '下载图片';
                        downloadLink.style.display = 'block';
                        downloadLink.style.marginTop = '10px';
                        document.getElementById('imageContainer').appendChild(downloadLink);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('message').textContent = '图片生成失败: ' + error.message;
                });
            }
        </script>
    </body>
    </html>
    """


def main():
    """主函数，启动Web服务"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='小作文转图片Web服务')
    parser.add_argument('--host', default='0.0.0.0', help='监听主机地址，默认0.0.0.0')
    parser.add_argument('--port', type=int, default=5001, help='监听端口，默认5001')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 启动Web服务
    print(f"启动小作文转图片Web服务 - http://{args.host}:{args.port}/")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main() 