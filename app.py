import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta

app = Flask(__name__)
# 使用绝对路径来避免路径问题
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.secret_key = 'your-secret-key-here'

# 艾宾浩斯遗忘曲线复习间隔（天数）
REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30]

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS words 
                (id INTEGER PRIMARY KEY, 
                word_image TEXT, 
                sentence_image TEXT,
                image_type TEXT,
                learn_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews 
                (id INTEGER PRIMARY KEY, 
                word_id INTEGER, 
                review_date TEXT,
                review_count INTEGER DEFAULT 0,
                next_review_date TEXT)''')
    conn.commit()
    conn.close()

def calculate_next_review_date(review_count):
    """根据艾宾浩斯遗忘曲线计算下次复习日期"""
    if review_count >= len(REVIEW_INTERVALS):
        return None  # 完成所有复习
    return (datetime.now() + timedelta(days=REVIEW_INTERVALS[review_count])).strftime('%Y-%m-%d')

@app.route('/manage')
def manage():
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM words ORDER BY learn_date DESC")
        words = c.fetchall()
        conn.close()
        return render_template('manage.html', words=words)
    except Exception as e:
        flash(f'加载数据失败：{str(e)}', 'error')
        return render_template('manage.html', words=[])

@app.route('/delete/<int:word_id>', methods=['POST'])
def delete_word(word_id):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        # 获取图片路径
        c.execute("SELECT word_image, sentence_image FROM words WHERE id=?", (word_id,))
        result = c.fetchone()
        if result:
            word_image = result[0]
            sentence_image = result[1]
            # 删除物理文件
            if word_image:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], word_image)
                if os.path.exists(file_path):
                    os.remove(file_path)
            if sentence_image:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], sentence_image)
                if os.path.exists(file_path):
                    os.remove(file_path)
            # 删除数据库记录
            c.execute("DELETE FROM reviews WHERE word_id=?", (word_id,))
            c.execute("DELETE FROM words WHERE id=?", (word_id,))
            conn.commit()
            flash('闪卡删除成功！', 'success')
        conn.close()
    except Exception as e:
        flash(f'删除失败：{str(e)}', 'error')
    return redirect(url_for('manage'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        try:
            word_image = request.files.get('word_image')
            sentence_image = request.files.get('sentence_image')
            essay_image = request.files.get('essay_image')
            image_type = request.form.get('image_type')
            learn_date = request.form.get('learn_date')
            
            if not learn_date:
                flash('请选择学习日期', 'error')
                return redirect(url_for('upload'))
            
            if image_type == 'word' and (not word_image or not sentence_image):
                flash('请上传单词图片和句子图片', 'error')
                return redirect(url_for('upload'))
            
            if image_type == 'essay' and not essay_image:
                flash('请上传作文图片', 'error')
                return redirect(url_for('upload'))
            
            # 确保上传目录存在
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            
            if image_type == 'word':
                word_filename = secure_filename(word_image.filename)
                sentence_filename = secure_filename(sentence_image.filename)
                
                word_image.save(os.path.join(app.config['UPLOAD_FOLDER'], word_filename))
                sentence_image.save(os.path.join(app.config['UPLOAD_FOLDER'], sentence_filename))
                
                c.execute("INSERT INTO words (word_image, sentence_image, image_type, learn_date) VALUES (?, ?, ?, ?)",
                         (word_filename, sentence_filename, image_type, learn_date))
            else:
                essay_filename = secure_filename(essay_image.filename)
                essay_image.save(os.path.join(app.config['UPLOAD_FOLDER'], essay_filename))
                
                c.execute("INSERT INTO words (word_image, image_type, learn_date) VALUES (?, ?, ?)",
                         (essay_filename, image_type, learn_date))
            
            word_id = c.lastrowid
            # 设置第一次复习日期为明天
            next_review_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            c.execute("INSERT INTO reviews (word_id, review_date, review_count, next_review_date) VALUES (?, ?, ?, ?)",
                     (word_id, learn_date, 0, next_review_date))
            conn.commit()
            conn.close()
            
            flash('闪卡上传成功！', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'上传失败：{str(e)}', 'error')
            return redirect(url_for('upload'))
    return render_template('upload.html')

@app.route('/review/<int:word_id>', methods=['POST'])
def review_word(word_id):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # 获取当前复习次数
        c.execute("SELECT review_count FROM reviews WHERE word_id=?", (word_id,))
        result = c.fetchone()
        if result:
            review_count = result[0]
            next_review_date = calculate_next_review_date(review_count)
            
            if next_review_date:
                # 更新复习次数和下次复习日期
                c.execute("UPDATE reviews SET review_count=?, next_review_date=? WHERE word_id=?",
                         (review_count + 1, next_review_date, word_id))
            else:
                # 完成所有复习，删除复习记录
                c.execute("DELETE FROM reviews WHERE word_id=?", (word_id,))
            
            conn.commit()
            flash('复习完成！', 'success')
        conn.close()
    except Exception as e:
        flash(f'复习失败：{str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/')
def index():
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 获取新单词
        c.execute("SELECT * FROM words WHERE learn_date=? AND image_type='word'", (today,))
        new_words = c.fetchall()
        
        # 获取新作文
        c.execute("SELECT * FROM words WHERE learn_date=? AND image_type='essay'", (today,))
        new_essays = c.fetchall()
        
        # 获取需要复习的单词
        c.execute("""
            SELECT w.* FROM words w 
            JOIN reviews r ON w.id=r.word_id 
            WHERE r.next_review_date=? AND w.image_type='word'
        """, (today,))
        review_words = c.fetchall()
        
        # 获取需要复习的作文
        c.execute("""
            SELECT w.* FROM words w 
            JOIN reviews r ON w.id=r.word_id 
            WHERE r.next_review_date=? AND w.image_type='essay'
        """, (today,))
        review_essays = c.fetchall()
        
        conn.close()
        return render_template('index.html', 
                             new_words=new_words, 
                             new_essays=new_essays,
                             review_words=review_words,
                             review_essays=review_essays)
    except Exception as e:
        flash(f'加载数据失败：{str(e)}', 'error')
        return render_template('index.html', 
                             new_words=[], 
                             new_essays=[],
                             review_words=[],
                             review_essays=[])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)