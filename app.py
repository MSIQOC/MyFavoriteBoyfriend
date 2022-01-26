import functools

from flask import Flask, render_template, jsonify, request, url_for, redirect, session, g
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo import MongoClient

app = Flask(__name__)
app.config.update(
    SECRET_KEY='SPARTA_SECRET_KEY'
)


client = MongoClient('localhost', 27017)
db = client.boyfriends


#로그인 app.py 만들기
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect('/login')

        return view(**kwargs)

    return wrapped_view


@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    g.user = None

    if user_id is None:
        g.user = None
    else:
        try:
            g.user = db.users.find_one({
                'user_id': user_id
            })
        except:
            pass


@app.get('/login')
def get_login():
    return render_template('login.html')


@app.post('/login')
def post_login():
    user_id = request.form['user_id']
    password = request.form['password']

    error = None

    user = db.users.find_one({
        'user_id': user_id
    })

    if user is None:
        error = 'Incorrect user id.'
    elif not check_password_hash(user['password'], password):
        error = 'Incorrect password.'

    if error is None:
        session.clear()
        session['user_id'] = user['user_id']
        return redirect('/')

    return redirect('/login')


@app.get('/signup')
def get_signup():
    return render_template('signup.html')


@app.post('/signup')
def post_signup():
    user_id = request.form['user_id']
    username = request.form['username']
    password = request.form['password']

    error = None

    if not user_id:
        error = 'User ID is required.'
    elif not username:
        error = 'Username is required.'
    elif not password:
        error = 'Password is required.'
    elif db.users.find_one({'user_id': user_id}) is not None:
        error = 'User {} is already registered.'.format(username)

    if error is None:
        user = {
            'user_id': user_id,
            'password': generate_password_hash(password),
            'username': username
        }

        db.users.insert_one(user)

        return redirect('/login')

    return redirect('/signup')


@app.get('/logout')
def get_logout():
    session.clear()
    return redirect('/')


# HTML 화면 보여주기
@app.get('/')
@login_required
def home():
    return render_template('favorite.html')


@app.get('/add')
def add():
    return render_template('add.html')


@app.get('/chats')
def chat():
    return render_template('chatting.html')


@app.post('/findchat')
def findchat():
    form = request.form
    val = form['_val']
    name = form['name']
    boyfriend = list(db.chats.find({
        'name': name,
        'question': val
    }, {'_id': False}))
    if not boyfriend:
        return jsonify({
            'result': 'failed'
        })
    return jsonify({
        'result': 'success',
        'chat': boyfriend
    })


@app.post('/addchat')
def addchat():
    form = request.form
    question = form['question']
    answer = form['answer']
    name = form['name']
    db.chats.insert_one({
        'name': name,
        'question': question,
        'answer': answer
    })
    return jsonify({'msg': '저장성공!'})


# 여기서부터 파이몽고 활용
# 새로운 남자친구 추가
@app.post('/adding')
def adding():
    form = request.form
    name = form['name']
    personality = form['personality']
    age = form['age']
    hobby = form['hobby']
    blood_type = form['bloodType']

    boyfriend = db.boyfriends.find_one({'name': name, 'user_id': g.user['user_id']})
    if boyfriend:
        return jsonify({'result': 'failed', 'msg': '다른 남자친구 이름으로 써주세요!'})
    else:
        db.boyfriends.insert_one({
            'user_id': g.user['user_id'],
            'name': name,
            'personality': personality,
            'age': age,
            'hobby': hobby,
            'blood_type': blood_type,
            'like': 0
        })

    return jsonify({'result': 'success', 'msg': '추가가 완료됐습니다!'})


@app.get('/api/list')
def show_boyfriends():
    boyfriends_list = list(db.boyfriends.find({'user_id': g.user['user_id']}, {'_id': False}).sort('like', -1))
    return jsonify({
        'result': 'success', 'msg': 'hello',
        'boyfriends_list': boyfriends_list
    })


@app.post('/api/like')
def chat_star():
    name = request.form['name'] #클라이언트가 보내줬다고 가정(index.html에서 data에 name을 넘겨준다.)
    db.boyfriends.update_one({'name': name}, {'$inc': {'like': 1}}) #이렇게 해주는게 더 안전하게 올려줄 수 있다.
    db.boyfriends.find().sort({'like': 1, 'name': 1})
    return jsonify({'result': 'success'})


@app.post('/api/delete')
def delete_star():
    # 1. 클라이언트가 전달한 name_give를 name_receive 변수에 넣습니다.
    name = request.form['name']
    # 2. mystar 목록에서 delete_one으로 name이 name_receive와 일치하는 star를 제거합니다.
    db.boyfriends.delete_one({'name': name, 'user_id': g.user['user_id']})
    db.chats.delete_many({'name': name})
    # 3. 성공하면 success 메시지를 반환합니다.
    return jsonify({'result': 'success', 'msg': '삭제가 완료됐습니다!'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)