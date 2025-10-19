from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os
app = Flask(__name__)

# ---------------- DATABASE CONFIG ----------------
# MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Narean%4025@localhost/blog_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
# ---------------- MODELS ----------------

class Post(db.Model):
    __tablename__ = 'posts'
    post_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100))  # store image filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan", lazy=True)

class Comment(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- CREATE TABLES ----------------
with app.app_context():
    db.create_all()  # Creates tables if they don't exist

# ---------------- ROUTES ----------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




@app.route('/')
def index():
    posts = Post.query.order_by(Post.post_id.desc()).all()
    return render_template('index.html', userpost=posts)

@app.route('/add_post', methods=['GET', 'POST'])
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form['author']
        image_file = request.files.get('image')  # get uploaded file
        image_filename = None

        if image_file and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        new_post = Post(title=title, content=content, author=author, image=image_filename)
        db.session.add(new_post)
        db.session.commit()
        return redirect('/')
    return render_template('add_post.html')

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        name = request.form['name']
        comment_text = request.form['comment']
        new_comment = Comment(post_id=post.post_id, name=name, comment=comment_text)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(f'/post/{post_id}')
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.comment_id.asc()).all()
    return render_template('post.html', post=post, comments=comments)

@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect('/')


# @app.route('/asdfg')
# def demo():
#     return render_template('index.html')
# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app.run(debug=True)
