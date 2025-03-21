import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import hashlib
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
from flask_caching import Cache
import threading
from contextlib import contextmanager
import time
import uuid
import functools
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123456789'  # 修改为更安全的密钥
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['AUDIO_FOLDER'] = 'static/audio'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['LOG_FOLDER'] = 'logs'
app.config['JSON_AS_ASCII'] = False  # 支持中文 JSON
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # 设置会话有效期为24小时
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = False  # 在开发环境中设为False，生产环境设为True
app.config['SESSION_COOKIE_HTTPONLY'] = True  # 阻止JavaScript访问会话cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 防止CSRF攻击
app.config['SESSION_USE_SIGNER'] = True  # 对cookie进行签名

# 配置缓存
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',  # 简单内存缓存
    'CACHE_DEFAULT_TIMEOUT': 300  # 默认缓存时间5分钟
})

# 数据库连接池
class DatabasePool:
    _instance = None
    _lock = threading.Lock()
    _local = threading.local()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabasePool, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._lock = threading.Lock()

    def _create_connection(self):
        """创建新的数据库连接"""
        conn = sqlite3.connect('database.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def get_connection(self):
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = self._create_connection()
        return self._local.connection

    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection

db_pool = DatabasePool()

def get_db_connection():
    """获取数据库连接"""
    return db_pool.get_connection()

# 配置日志
if not os.path.exists(app.config['LOG_FOLDER']):
    os.makedirs(app.config['LOG_FOLDER'])

file_handler = RotatingFileHandler(
    os.path.join(app.config['LOG_FOLDER'], 'app.log'),
    maxBytes=1024 * 1024,  # 1MB
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('应用启动')

# 数据库错误类
class DatabaseError(Exception):
    pass

# 文件操作错误类
class FileOperationError(Exception):
    pass

# 数据库连接装饰器
def with_db_connection(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        conn = get_db_connection()
        try:
            kwargs['conn'] = conn
            return f(*args, **kwargs)
        except sqlite3.Error as e:
            app.logger.error(f'数据库错误: {str(e)}')
            flash('数据库操作失败，请稍后重试', 'error')
            return redirect(url_for('index'))
    return decorated_function

# 文件操作装饰器
def handle_file_operation(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except FileOperationError as e:
            app.logger.error(f'文件操作错误: {str(e)}')
            flash(str(e), 'error')
            return redirect(request.url)
        except Exception as e:
            app.logger.error(f'未知错误: {str(e)}')
            flash('操作失败，请稍后重试', 'error')
            return redirect(request.url)
    return decorated_function

def save_file(file, folder, allowed_extensions):
    """安全地保存文件"""
    if not file or file.filename == '':
        raise FileOperationError('未选择文件')
        
    if not allowed_file(file.filename, allowed_extensions):
        raise FileOperationError('不支持的文件类型')
        
    try:
        filename = secure_filename(file.filename)
        new_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        file.save(os.path.join(folder, new_filename))
        return new_filename
    except Exception as e:
        raise FileOperationError(f'文件保存失败: {str(e)}')

def delete_file(filename, folder):
    """安全地删除文件"""
    if filename:
        try:
            # 分离出文件名部分（不含路径）
            category_path = os.path.dirname(filename)
            file_basename = os.path.basename(filename)
            
            # 组合完整的文件路径
            file_path = os.path.join(folder, category_path, file_basename)
            # 确保路径使用正斜杠
            file_path = file_path.replace('\\', '/')
            
            app.logger.info(f'尝试删除文件: {file_path}')
            if os.path.exists(file_path):
                os.remove(file_path)
                app.logger.info(f'成功删除文件: {file_path}')
            else:
                app.logger.warning(f'文件不存在: {file_path}')
        except Exception as e:
            app.logger.error(f'文件删除失败: {str(e)}')

def allowed_file(filename, allowed_extensions=None):
    """检查文件是否有允许的扩展名"""
    if not allowed_extensions:
        allowed_extensions = ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('文件大小超过限制', 'error')
    return redirect(request.url)

# 艾宾浩斯遗忘曲线复习间隔（天数）
REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30]

# 内容类别
CATEGORIES = {
    'words': '单词',
    'university': '大学之道',
    'music': '音律启蒙',
    'oracle': '甲骨文'
}

# 管理密码
ADMIN_PASSWORD = '1237'

# 设置
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# 添加IP锁定功能相关变量
login_attempts = {}  # 存储登录尝试次数 {ip: {'attempts': 次数, 'locked_until': 时间}}

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            # 用户未登录，重定向到登录页面
            app.logger.info(f"访问受保护的路由 {request.path} 被拒绝: 未登录")
            return redirect(url_for('login', next=request.path))
        
        # 检查会话是否过期（超过24小时）
        if 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            time_elapsed = datetime.now() - login_time
            app.logger.info(f"验证会话: 登录时间={login_time}, 已经过时间={time_elapsed}")
            
            if time_elapsed >= timedelta(hours=24):
                # 会话已过期，清除会话并重定向到登录页面
                app.logger.info("会话已过期，清除会话")
                session.clear()
                flash('您的登录已过期，请重新登录', 'info')
                return redirect(url_for('login', next=request.path))
        else:
            app.logger.warning("会话中缺少登录时间信息")
            session.clear()
            return redirect(url_for('login', next=request.path))
        
        # 通过验证，继续执行原始视图函数
        app.logger.info(f"通过验证，允许访问: {request.path}")
        return view(**kwargs)
    return wrapped_view

def init_db():
    # 使用直接连接而不是上下文管理器
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vocabulary (
        id INTEGER PRIMARY KEY,
        category TEXT NOT NULL,
        chinese_name TEXT,
        pinyin TEXT,
        english_name TEXT,
        image_path TEXT,
        learn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        review_date TIMESTAMP,
        review_count INTEGER DEFAULT 0
    )
    ''')
    
    # 创建contents表以兼容现有代码
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contents (
        id INTEGER PRIMARY KEY,
        category TEXT NOT NULL,
        content_image TEXT,
        content_audio TEXT,
        example_image TEXT,
        example_audio TEXT,
        learn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        next_review_date TIMESTAMP,
        review_count INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

def dict_factory(cursor, row):
    """将 SQLite Row 转换为字典"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    """获取数据库连接"""
    conn = db_pool.get_connection()
    conn.row_factory = dict_factory  # 使用字典工厂
    return conn

def get_categories():
    """返回所有可用的分类"""
    return CATEGORIES

@app.teardown_appcontext
def close_db(error):
    """在应用上下文结束时关闭数据库连接"""
    db_pool.close_connection()

def calculate_next_review_date(review_count):
    """根据艾宾浩斯遗忘曲线计算下次复习日期"""
    if review_count >= len(REVIEW_INTERVALS):
        return None  # 完成所有复习
    return (datetime.now() + timedelta(days=REVIEW_INTERVALS[review_count])).strftime('%Y-%m-%d')

@app.route('/manage')
@login_required
def manage():
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('SELECT * FROM contents ORDER BY id DESC')
        contents = c.fetchall()
        
        # 标准化图片路径，确保使用正斜杠
        for content in contents:
            if content['content_image']:
                content['content_image'] = content['content_image'].replace('\\', '/')
            if content['example_image']:
                content['example_image'] = content['example_image'].replace('\\', '/')
        
        app.logger.info(f"成功获取内容列表，共 {len(contents)} 条记录")
        return render_template('manage.html', contents=contents, categories=CATEGORIES)
    except Exception as e:
        app.logger.error(f"获取内容列表失败: {str(e)}")
        flash(f"获取内容列表失败: {str(e)}", 'error')
        return render_template('manage.html', contents=[], categories=CATEGORIES)

@app.route('/manage2')
@login_required
def manage2():
    """更简单的管理页面测试"""
    try:
        conn = get_db()
        c = conn.cursor()
        # 使用索引优化的查询
        contents = c.execute('''SELECT * FROM contents 
                              ORDER BY learn_date DESC, category, id DESC 
                              LIMIT 100''').fetchall()
        return render_template('manage_simple.html', contents=contents, categories=CATEGORIES)
    except Exception as e:
        app.logger.error(f'简易管理页面加载失败: {str(e)}')
        return f"""
        <html>
        <head><title>错误</title></head>
        <body>
            <h1>加载失败</h1>
            <p>错误信息: {str(e)}</p>
            <a href="/">返回首页</a>
        </body>
        </html>
        """

@app.route('/test')
def test_page():
    """极简测试页面"""
    try:
        return """
        <html>
        <head>
            <title>测试页面</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 2em; }
                .card { border: 1px solid #ddd; padding: 1em; margin: 1em 0; }
            </style>
        </head>
        <body>
            <h1>测试页面</h1>
            <p>如果你能看到这个页面，说明基本渲染正常。</p>
            <div class="card">
                <h3>测试卡片</h3>
                <p>这是一个静态内容。</p>
            </div>
            <p><a href="/">返回首页</a> | <a href="/manage">去管理页面</a> | <a href="/manage2">去简易管理页面</a></p>
        </body>
        </html>
        """
    except Exception as e:
        app.logger.error(f'测试页面加载失败: {str(e)}')
        return f"<h1>错误</h1><p>{str(e)}</p>"

@app.route('/delete/<int:id>')
@login_required
@with_db_connection
def delete(id, conn):
    c = conn.cursor()
    
    # 获取文件信息
    content = c.execute('SELECT * FROM contents WHERE id = ?', (id,)).fetchone()
    
    if content:
        try:
            # 删除文件
            delete_file(content['content_image'], app.config['UPLOAD_FOLDER'])
            delete_file(content['content_audio'], app.config['AUDIO_FOLDER'])
            delete_file(content['example_image'], app.config['UPLOAD_FOLDER'])
            delete_file(content['example_audio'], app.config['AUDIO_FOLDER'])
            
            # 从数据库中删除记录
            c.execute('DELETE FROM contents WHERE id = ?', (id,))
            conn.commit()
            
            # 清除缓存
            cache.delete_memoized(category_view)
            cache.delete('view/index')
            cache.delete('view/manage')
            
            app.logger.info(f'成功删除内容: ID {id}')
            flash('删除成功', 'success')
        except Exception as e:
            app.logger.error(f'删除内容失败: {str(e)}')
            flash('删除失败，请稍后重试', 'error')
    else:
        app.logger.warning(f'尝试删除不存在的内容: ID {id}')
        flash('内容不存在', 'error')
        
    return redirect(url_for('manage'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        try:
            category = request.form['category']
            chinese_name = request.form.get('chinese_name', '')
            pinyin = request.form.get('pinyin', '')
            english_name = request.form.get('english_name', '')
            
            # 创建一个特定目录来保存上传的图片
            upload_folder = os.path.join(app.static_folder, f'uploads/{category}')
            # 确保路径使用正斜杠
            upload_folder = upload_folder.replace('\\', '/')
            os.makedirs(upload_folder, exist_ok=True)
            
            # 生成唯一文件名
            timestamp = int(time.time())
            random_id = uuid.uuid4().hex[:8]
            
            # 处理内容图片上传
            if 'content_image' not in request.files:
                flash('没有选择内容图片', 'danger')
                return redirect(request.url)
            
            file = request.files['content_image']
            if file.filename == '':
                flash('没有选择内容图片', 'danger')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                # 安全地获取文件扩展名
                file_ext = os.path.splitext(file.filename)[1].lower()
                content_image_filename = f"{timestamp}_{random_id}_content{file_ext}"
                file_path = os.path.join(upload_folder, content_image_filename)
                # 确保路径使用正斜杠
                file_path = file_path.replace('\\', '/')
                file.save(file_path)
                app.logger.info(f"已上传内容图片: {file_path}")
                
                # 优化图片
                optimized_path = optimize_image(file_path, quality=85, max_size=(800, 800))
                # 获取优化后的文件名（可能已更改为.webp）
                optimized_filename = os.path.basename(optimized_path)
                # 存储相对路径，包含分类目录
                content_image_path = f'{category}/{optimized_filename}'
                app.logger.info(f"已优化内容图片: {optimized_path}, 存储路径: {content_image_path}")
            else:
                flash('不支持的文件类型，仅支持图片文件', 'danger')
                return redirect(request.url)
            
            # 处理内容音频上传
            content_audio_path = ''
            if 'content_audio' in request.files:
                file = request.files['content_audio']
                if file and file.filename != '':
                    # 创建音频目录
                    audio_folder = os.path.join(app.static_folder, f'audio/{category}')
                    # 确保路径使用正斜杠
                    audio_folder = audio_folder.replace('\\', '/')
                    os.makedirs(audio_folder, exist_ok=True)
                    
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    content_audio_filename = f"{timestamp}_{random_id}_content_audio{file_ext}"
                    file_path = os.path.join(audio_folder, content_audio_filename)
                    # 确保路径使用正斜杠
                    file_path = file_path.replace('\\', '/')
                    file.save(file_path)
                    app.logger.info(f"已上传内容音频: {file_path}")
                    # 修复路径，不要再添加audio前缀
                    content_audio_filename = os.path.basename(file_path)
                    content_audio_path = f'{category}/{content_audio_filename}'
                    app.logger.info(f"音频存储路径: {content_audio_path}")
            
            # 处理例句图片上传
            example_image_path = ''
            if 'example_image' in request.files:
                file = request.files['example_image']
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        file_ext = os.path.splitext(file.filename)[1].lower()
                        example_image_filename = f"{timestamp}_{random_id}_example{file_ext}"
                        file_path = os.path.join(upload_folder, example_image_filename)
                        # 确保路径使用正斜杠
                        file_path = file_path.replace('\\', '/')
                        file.save(file_path)
                        app.logger.info(f"已上传例句图片: {file_path}")
                        
                        # 优化例句图片
                        optimized_path = optimize_image(file_path, quality=85, max_size=(800, 800))
                        # 获取优化后的文件名
                        optimized_filename = os.path.basename(optimized_path)
                        # 存储相对路径，包含分类目录
                        example_image_path = f'{category}/{optimized_filename}'
                        app.logger.info(f"已优化例句图片: {optimized_path}, 存储路径: {example_image_path}")
            
            # 处理例句音频上传
            example_audio_path = ''
            if 'example_audio' in request.files:
                file = request.files['example_audio']
                if file and file.filename != '':
                    # 创建音频目录
                    audio_folder = os.path.join(app.static_folder, f'audio/{category}')
                    # 确保路径使用正斜杠
                    audio_folder = audio_folder.replace('\\', '/')
                    os.makedirs(audio_folder, exist_ok=True)
                    
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    example_audio_filename = f"{timestamp}_{random_id}_example_audio{file_ext}"
                    file_path = os.path.join(audio_folder, example_audio_filename)
                    # 确保路径使用正斜杠
                    file_path = file_path.replace('\\', '/')
                    file.save(file_path)
                    app.logger.info(f"已上传例句音频: {file_path}")
                    # 修复路径，不要再添加audio前缀
                    example_audio_filename = os.path.basename(file_path)
                    example_audio_path = f'{category}/{example_audio_filename}'
                    app.logger.info(f"音频存储路径: {example_audio_path}")
            
            # 获取学习日期参数
            learn_date = request.form.get('learn_date', datetime.now().strftime('%Y-%m-%d'))
            
            # 添加到数据库
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                '''INSERT INTO contents 
                   (category, content_image, content_audio, example_image, example_audio, learn_date) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (category, 
                 content_image_path, 
                 content_audio_path,
                 example_image_path,
                 example_audio_path,
                 learn_date)
            )
            
            conn.commit()
            conn.close()
            
            app.logger.info(f"记录已添加到数据库 contents 表: {category}, {content_image_path}")
            
            # 判断是继续添加还是返回管理页面
            if 'submit_continue' in request.form:
                flash('上传成功！您可以继续添加。', 'success')
                return redirect(url_for('upload', category=category))
            else:
                flash('上传成功！', 'success')
                return redirect(url_for('manage'))
        except Exception as e:
            app.logger.error(f"上传处理错误: {str(e)}")
            flash(f'处理错误: {str(e)}', 'danger')
            return redirect(request.url)
    
    # GET 请求，显示上传表单
    categories = get_categories()
    default_category = request.args.get('category', '')
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('upload.html', 
                         categories=categories, 
                         selected_category=default_category, 
                         today=today,
                         last_category=default_category)  # 添加 last_category 参数

@app.route('/review/<int:id>')
@login_required
def review(id):
    conn = get_db()
    try:
        c = conn.cursor()
        
        # 使用事务确保数据一致性
        with conn:
            content = c.execute('SELECT review_count FROM contents WHERE id = ?', (id,)).fetchone()
            if not content:
                return jsonify({'success': False, 'message': '内容不存在'})
            
            review_count = content['review_count'] + 1
            next_review_date = calculate_next_review_date(review_count)
            
            c.execute('''UPDATE contents 
                        SET review_count = ?, next_review_date = ?
                        WHERE id = ?''',
                     (review_count, next_review_date, id))
            
            # 清除相关缓存
            cache.delete_memoized(category_view)
            cache.delete('view/index')
            cache.delete('view/manage')
            
            return jsonify({'success': True})
    finally:
        pass  # 连接会在线程结束时自动关闭

@app.route('/')
@cache.cached(timeout=60)  # 1分钟缓存
@login_required
def index():
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 使用单个查询获取所有统计数据
        stats = {category: {'new': 0, 'review': 0} for category in CATEGORIES.keys()}
        
        # 获取新内容统计
        c.execute('''SELECT category, COUNT(*) as count 
                    FROM contents 
                    WHERE learn_date = ?
                    GROUP BY category''', (today,))
        for row in c.fetchall():
            stats[row['category']]['new'] = row['count']
        
        # 获取待复习统计
        c.execute('''SELECT category, COUNT(*) as count 
                    FROM contents 
                    WHERE next_review_date <= ? AND next_review_date IS NOT NULL
                    GROUP BY category''', (today,))
        for row in c.fetchall():
            stats[row['category']]['review'] = row['count']
        
        return render_template('category_select.html', categories=CATEGORIES, stats=stats)
    finally:
        pass  # 连接会在线程结束时自动关闭

@app.route('/category/<category>')
@login_required
@cache.cached(timeout=60, query_string=True)  # 添加1分钟缓存，包含查询参数
def category_view(category):
    if category not in CATEGORIES:
        flash('无效的分类', 'error')
        return redirect(url_for('index'))
    
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    
    # 优化查询：使用一个SQL查询获取所有数据
    if show_all:
        # 获取所有内容
        c.execute('''
            SELECT *, 
                CASE 
                    WHEN learn_date = ? THEN 'new'
                    WHEN next_review_date <= ? AND next_review_date IS NOT NULL THEN 'review'
                    ELSE 'past'
                END as item_type
            FROM contents 
            WHERE category = ?
            ORDER BY 
                CASE item_type 
                    WHEN 'new' THEN 1
                    WHEN 'review' THEN 2 
                    ELSE 3
                END,
                id DESC
        ''', (today, today, category))
    else:
        # 只获取今天的新内容和需要复习的内容
        c.execute('''
            SELECT *, 
                CASE 
                    WHEN learn_date = ? THEN 'new'
                    ELSE 'review'
                END as item_type
            FROM contents 
            WHERE category = ? AND (learn_date = ? OR (next_review_date <= ? AND next_review_date IS NOT NULL))
            ORDER BY 
                CASE item_type 
                    WHEN 'new' THEN 1
                    ELSE 2
                END,
                id DESC
        ''', (today, category, today, today))
    
    all_items = c.fetchall()
    
    # 标准化图片路径
    for item in all_items:
        if item['content_image']:
            item['content_image'] = item['content_image'].replace('\\', '/')
        if item['example_image']:
            item['example_image'] = item['example_image'].replace('\\', '/')
    
    # 根据类型分离项目
    new_items = [item for item in all_items if item['item_type'] == 'new']
    review_items = [item for item in all_items if item['item_type'] == 'review']
    
    # 如果显示所有内容，还包括过去的内容
    if show_all:
        past_items = [item for item in all_items if item['item_type'] == 'past']
        new_items.extend(past_items)  # 将过去的内容添加到新内容中显示
    
    return render_template('category_view.html', 
                         category=category, 
                         category_name=CATEGORIES[category], 
                         new_items=new_items, 
                         review_items=review_items,
                         show_all=show_all)

# 添加音频文件访问路由
@app.route('/static/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename)

@app.route('/edit/<int:id>', methods=['POST'])
@login_required
@with_db_connection
def edit(id, conn):
    try:
        content = conn.execute('SELECT * FROM contents WHERE id = ?', (id,)).fetchone()
        if not content:
            return jsonify({'success': False, 'message': '内容不存在'})
        
        # 处理文件上传
        content_image_filename = content['content_image']
        content_audio_filename = content['content_audio']
        example_image_filename = content['example_image']
        example_audio_filename = content['example_audio']
        
        # 处理内容图片
        if 'content_image' in request.files:
            file = request.files['content_image']
            if file and file.filename:
                # 删除旧文件
                delete_file(content_image_filename, app.config['UPLOAD_FOLDER'])
                # 保存新文件
                content_image_filename = save_file(
                    file,
                    app.config['UPLOAD_FOLDER'],
                    {'png', 'jpg', 'jpeg', 'gif'}
                )
        
        # 处理内容音频
        if 'content_audio' in request.files:
            file = request.files['content_audio']
            if file and file.filename:
                delete_file(content_audio_filename, app.config['AUDIO_FOLDER'])
                content_audio_filename = save_file(
                    file,
                    app.config['AUDIO_FOLDER'],
                    {'mp3', 'wav'}
                )
        
        # 处理例句图片
        if 'example_image' in request.files:
            file = request.files['example_image']
            if file and file.filename:
                delete_file(example_image_filename, app.config['UPLOAD_FOLDER'])
                example_image_filename = save_file(
                    file,
                    app.config['UPLOAD_FOLDER'],
                    {'png', 'jpg', 'jpeg', 'gif'}
                )
        
        # 处理例句音频
        if 'example_audio' in request.files:
            file = request.files['example_audio']
            if file and file.filename:
                delete_file(example_audio_filename, app.config['AUDIO_FOLDER'])
                example_audio_filename = save_file(
                    file,
                    app.config['AUDIO_FOLDER'],
                    {'mp3', 'wav'}
                )
        
        # 获取学习日期参数
        learn_date = request.form.get('learn_date', content['learn_date'])
        
        # 更新数据库
        conn.execute('''UPDATE contents 
                       SET content_image = ?,
                           content_audio = ?,
                           example_image = ?,
                           example_audio = ?,
                           learn_date = ?
                       WHERE id = ?''',
                    (content_image_filename,
                     content_audio_filename,
                     example_image_filename,
                     example_audio_filename,
                     learn_date,
                     id))
        conn.commit()
        
        # 清除缓存
        cache.delete_memoized(category_view)
        cache.delete('view/index')
        cache.delete('view/manage')
        
        app.logger.info(f'成功更新内容: ID {id}')
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f'更新内容失败: {str(e)}')
        return jsonify({'success': False, 'message': str(e)})

# 添加登出路由
@app.route('/logout')
def logout():
    app.logger.info(f"用户登出，之前的会话状态: {session}")
    # 清除会话
    session.clear()
    # 创建响应
    response = redirect(url_for('login'))
    # 删除所有会话相关的cookie
    response.delete_cookie('session')
    # 显示登出消息
    flash('您已成功登出', 'info')
    app.logger.info("会话已清除，用户已登出")
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    attempts = 0
    
    app.logger.info(f"登录请求开始，会话状态: {session}")
    
    # 检查用户是否已经登录
    if 'authenticated' in session and session['authenticated'] and 'login_time' in session:
        # 检查登录时间，如果超过24小时则需要重新登录
        login_time = datetime.fromisoformat(session['login_time'])
        time_elapsed = datetime.now() - login_time
        app.logger.info(f"用户已登录，登录时间: {login_time}, 已经过时间: {time_elapsed}")
        
        if time_elapsed < timedelta(hours=24):
            # 如果请求是直接访问登录页面，则重定向到首页
            if not request.args.get('next'):
                app.logger.info("用户已登录且直接访问登录页，重定向到首页")
                return redirect(url_for('index'))
            # 如果是由其他页面重定向过来的，则重定向到那个页面
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                app.logger.info(f"用户已登录，重定向到目标页面: {next_page}")
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            # 会话已过期，清除会话
            app.logger.info("会话已过期，清除会话")
            session.clear()
            flash('您的登录已过期，请重新登录', 'info')
    else:
        app.logger.info("用户未登录或会话信息不完整")
    
    # 获取客户端IP
    client_ip = request.remote_addr
    app.logger.info(f"客户端IP: {client_ip}")
    
    # 检查是否被锁定
    if client_ip in login_attempts and 'locked_until' in login_attempts[client_ip]:
        locked_until = login_attempts[client_ip]['locked_until']
        if datetime.now() < locked_until:
            remaining = int((locked_until - datetime.now()).total_seconds() / 3600)
            app.logger.info(f"IP已被锁定: {client_ip}, 剩余锁定时间: {remaining}小时")
            return render_template('login.html', 
                                  error=f'此IP已被锁定，请在{remaining}小时后再试', 
                                  attempts=3)
    
    # 处理POST请求（登录表单提交）
    if request.method == 'POST':
        password = request.form.get('password')
        app.logger.info(f"接收到登录表单提交，密码长度: {len(password) if password else 0}")
        
        # 初始化IP尝试记录
        if client_ip not in login_attempts:
            login_attempts[client_ip] = {'attempts': 0}
        
        # 密码验证
        if password == ADMIN_PASSWORD:
            # 验证成功，重置尝试次数
            login_attempts[client_ip]['attempts'] = 0
            if 'locked_until' in login_attempts[client_ip]:
                del login_attempts[client_ip]['locked_until']
            
            # 设置会话
            session.clear()
            session['authenticated'] = True
            session['login_time'] = datetime.now().isoformat()  # 记录登录时间
            session.permanent = True  # 启用长期会话，但仍受PERMANENT_SESSION_LIFETIME限制
            app.logger.info(f'用户登录成功: {client_ip}, 会话信息: {session}')
            
            # 强制设置cookie，确保未来请求包含会话信息
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                app.logger.info(f"登录成功，重定向到: {next_page}")
                return redirect(next_page)
            app.logger.info("登录成功，重定向到首页")
            return redirect(url_for('index'))
        else:
            # 验证失败，增加尝试次数
            login_attempts[client_ip]['attempts'] += 1
            attempts = login_attempts[client_ip]['attempts']
            app.logger.warning(f'用户登录失败: {client_ip}, 尝试次数: {attempts}, 输入密码: {password}')
            
            # 超过3次锁定24小时
            if attempts >= 3:
                locked_until = datetime.now() + timedelta(hours=24)
                login_attempts[client_ip]['locked_until'] = locked_until
                error = '密码错误次数过多，此IP已被锁定24小时'
                app.logger.warning(f'IP已被锁定: {client_ip}, 至: {locked_until}')
            else:
                error = f'密码错误，请重试。剩余尝试次数: {3 - attempts}'
    
    # 返回登录页面
    app.logger.info(f"返回登录页面, 错误信息: {error}, 尝试次数: {attempts}")
    return render_template('login.html', error=error, attempts=attempts)

@app.before_request
def check_session():
    """在每个请求之前检查会话状态"""
    if request.endpoint != 'static' and request.endpoint != 'login' and request.endpoint != 'logout':
        app.logger.info(f"请求路径: {request.path}, 会话状态: {'已登录' if 'authenticated' in session and session['authenticated'] else '未登录'}")
        if 'authenticated' in session and session['authenticated'] and 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            time_elapsed = datetime.now() - login_time
            app.logger.info(f"会话信息: 登录时间={login_time}, 已经过时间={time_elapsed}")

# 添加到app.py中的图片处理部分
def optimize_image(file_path, quality=85, max_size=(800, 800)):
    """压缩和优化图片"""
    try:
        # 获取文件名和扩展名
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        file_name_without_ext = os.path.splitext(file_name)[0]
        
        # 确保目录分隔符是正斜杠
        file_dir = file_dir.replace('\\', '/')
        
        img = Image.open(file_path)
        # 调整大小
        img.thumbnail(max_size, Image.LANCZOS)
        # 保存为优化的WebP格式，但使用相同的文件名
        webp_path = os.path.join(file_dir, file_name_without_ext + '.webp')
        img.save(webp_path, 'WEBP', quality=quality)
        # 删除原始图片
        if os.path.abspath(file_path) != os.path.abspath(webp_path):
            os.remove(file_path)
        return webp_path
    except Exception as e:
        app.logger.error(f"图片优化失败: {str(e)}")
        return file_path

# 修改app.py中的静态文件路由
@app.route('/static/<path:filename>')
def serve_static(filename):
    response = send_from_directory(app.static_folder, filename)
    # 添加缓存控制头
    response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response

@app.route('/optimize_all_images')
@login_required
def optimize_all_images():
    """批量优化所有现有图片，减小文件大小，提高加载速度"""
    try:
        # 获取所有图片路径
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, content_image, example_image FROM contents')
        all_images = c.fetchall()
        
        # 统计信息
        total_images = 0
        processed_images = 0
        failed_images = 0
        space_saved = 0  # 节省的空间（字节）
        
        for item in all_images:
            # 处理内容图片
            if item['content_image']:
                total_images += 1
                try:
                    # 获取原始图片路径
                    img_path = os.path.join(app.static_folder, 'uploads', item['content_image'])
                    if os.path.exists(img_path):
                        # 获取原始文件大小
                        original_size = os.path.getsize(img_path)
                        
                        # 优化图片
                        optimized_path = optimize_image(img_path, quality=85, max_size=(800, 800))
                        
                        # 获取优化后的文件大小
                        if os.path.exists(optimized_path):
                            new_size = os.path.getsize(optimized_path)
                            space_saved += (original_size - new_size)
                            
                            # 更新数据库中的文件路径（如果文件名发生了变化）
                            new_filename = os.path.basename(optimized_path)
                            if os.path.basename(img_path) != new_filename:
                                # 确保保持路径结构一致
                                old_path_parts = item['content_image'].split('/')
                                if len(old_path_parts) > 1:
                                    # 保留分类目录
                                    category_dir = old_path_parts[0]
                                    # 使用正斜杠，避免使用Windows反斜杠
                                    new_path = f'{category_dir}/{new_filename}'
                                    # 确保路径中不含有反斜杠
                                    new_path = new_path.replace('\\', '/')
                                else:
                                    new_path = new_filename
                                
                                app.logger.info(f"更新图片路径: 从 {item['content_image']} 到 {new_path}")
                                c.execute('UPDATE contents SET content_image = ? WHERE id = ?', 
                                         (new_path, item['id']))
                            
                            processed_images += 1
                    else:
                        app.logger.warning(f"图片不存在: {img_path}")
                        failed_images += 1
                except Exception as e:
                    app.logger.error(f"优化图片失败: {img_path}, 错误: {str(e)}")
                    failed_images += 1
            
            # 处理例句图片
            if item['example_image']:
                total_images += 1
                try:
                    # 获取原始图片路径
                    img_path = os.path.join(app.static_folder, 'uploads', item['example_image'])
                    if os.path.exists(img_path):
                        # 获取原始文件大小
                        original_size = os.path.getsize(img_path)
                        
                        # 优化图片
                        optimized_path = optimize_image(img_path, quality=85, max_size=(800, 800))
                        
                        # 获取优化后的文件大小
                        if os.path.exists(optimized_path):
                            new_size = os.path.getsize(optimized_path)
                            space_saved += (original_size - new_size)
                            
                            # 更新数据库中的文件路径（如果文件名发生了变化）
                            new_filename = os.path.basename(optimized_path)
                            if os.path.basename(img_path) != new_filename:
                                # 确保保持路径结构一致
                                old_path_parts = item['example_image'].split('/')
                                if len(old_path_parts) > 1:
                                    # 保留分类目录
                                    category_dir = old_path_parts[0]
                                    # 使用正斜杠，避免使用Windows反斜杠
                                    new_path = f'{category_dir}/{new_filename}'
                                    # 确保路径中不含有反斜杠
                                    new_path = new_path.replace('\\', '/')
                                else:
                                    new_path = new_filename
                                
                                app.logger.info(f"更新图片路径: 从 {item['example_image']} 到 {new_path}")
                                c.execute('UPDATE contents SET example_image = ? WHERE id = ?', 
                                         (new_path, item['id']))
                            
                            processed_images += 1
                    else:
                        app.logger.warning(f"图片不存在: {img_path}")
                        failed_images += 1
                except Exception as e:
                    app.logger.error(f"优化图片失败: {img_path}, 错误: {str(e)}")
                    failed_images += 1
        
        # 提交数据库更改
        conn.commit()
        
        # 清除缓存
        cache.clear()
        
        # 计算总节省空间（MB）
        space_saved_mb = space_saved / (1024 * 1024)
        
        # 返回优化结果
        return render_template('optimize_result.html', 
                             total=total_images,
                             processed=processed_images,
                             failed=failed_images,
                             space_saved=space_saved_mb)
    except Exception as e:
        app.logger.error(f"批量优化图片失败: {str(e)}")
        return f"""
        <html>
        <head><title>优化失败</title></head>
        <body>
            <h1>批量优化失败</h1>
            <p>错误信息: {str(e)}</p>
            <a href="/manage">返回管理页面</a>
        </body>
        </html>
        """

if __name__ == '__main__':
    # 清除所有会话数据
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flask_session')
    if os.path.exists(session_dir):
        for file in os.listdir(session_dir):
            try:
                os.remove(os.path.join(session_dir, file))
                app.logger.info(f"已删除会话文件: {file}")
            except Exception as e:
                app.logger.error(f"删除会话文件失败: {file}, 错误: {str(e)}")
    
    # 初始化数据库和目录
    if not os.path.exists('database.db'):
        init_db()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['AUDIO_FOLDER']):
        os.makedirs(app.config['AUDIO_FOLDER'])
    
    app.run(debug=True)