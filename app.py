from flask import Flask, render_template, request, jsonify ,make_response, redirect, url_for, session
from pymongo import MongoClient
from flask_jwt_extended import *
from flask_bcrypt import Bcrypt
import random
 
app = Flask(__name__)
client = MongoClient('mongodb://__:__@13.125.153.232', 27017)
dblog = client.jungle_food_feed #db명

app.config.update(
			DEBUG = True,
			JWT_SECRET_KEY = "b'\xf6e\xa5S\xef\xd4g\xdbT\xeb\x9d\xc8\x9e\xc6\xab\xcd'"
		)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
app.secret_key = str(random.randrange(1, 100000))

## HTML을 주는 부분
@app.route('/')
def home():
   return render_template('login.html')

@app.route('/main')
def main():
   if not 'id' in session:
     return make_response(redirect(url_for('home'))) 
   print(session['id'])
   return render_template('index.html',id=session['id'])

@app.route('/logOut')
def logOut():
    response = make_response(redirect(url_for('home'))) 
    response.set_cookie('refresh_token_cookie', '', expires=-1) 
    response.set_cookie('access_token_cookie', '', expires=-1) 
    return response


@app.route('/signup', methods=['POST'])
def signup():
    id = request.form['id']
    checkId = list(dblog.login.find({'id':id}))
    if len(checkId) != 0 :
        return jsonify({'result': 'fail', 'msg':'이미 아이디가 존재합니다.'})
    pw = request.form['pw']
    name = request.form['name']

    pw_hash = bcrypt.generate_password_hash(pw)
    dblog.login.insert_one({'id':id,'pw':pw_hash,'name':name})
    return jsonify({'result': 'success', 'msg':'회원 가입에 성공했습니다!'})

@app.route('/login', methods=['POST'])
def login():
    id = request.form['id']
    session['id'] = id
    pw = request.form['pw']
    checkUser = list(dblog.login.find({'id':id}))
    

    access_token = create_access_token(identity=id)
    refresh_token = create_refresh_token(identity=id)

    # Set the JWTs and the CSRF double submit protection cookies
    # in this response

    if len(checkUser) == 0:
        return jsonify({'result': 'fail', 'msg':'아이디가 존재하지 않습니다.'})
    elif not bcrypt.check_password_hash(checkUser[0]['pw'],pw):
        return jsonify({'result': 'fail', 'msg':'비밀번호가 틀렸습니다.'})
    else :
        resp = jsonify({'result': 'success', 'id':id,'msg':'로그인 되었습니다!'})
        set_access_cookies(resp, access_token)
        set_refresh_cookies(resp, refresh_token)
        return resp, 200
    
#like feed
@app.route('/api/like', methods=['POST'])
def like_feed():
   if not 'id' in session:
     return jsonify({'result':'fail', 'msg':'세션이 만료되어 로그아웃 됩니다.'})
   #클라이언트가 전달한 name_give를 name_receive 변수에 넣기 
   name_receive = request.form['name_give']
   loca_receive = request.form['loca_give']
   ID_receive = request.form['ID_give']
   comment_receive = request.form['comment_give']
   print(ID_receive, name_receive, loca_receive,comment_receive)
   #MongoDB에 데이터 넣기
   #find_one으로 일치하는 데이터 있는지 찾고, 있으면 좋아요 +1
   feed = dblog.feeds.find_one({'name':name_receive, 'loca':loca_receive})
   
   if feed:
      print('상호가 카드에 등록되어있지만 ID 체크는 안함')
      #있으면 ID 리스트에서 서버로부터 받은 아이디가 있는지 확인
      checkID = dblog.feeds.find_one({'name':name_receive, 'loca':loca_receive, 'ID':ID_receive})
      print(checkID)
      if checkID:
         print('좋아요 취소')
         #있으면 좋아요 업데이트
         #feed의 like에 1을 빼준 minus_like 변수
         minus_like = feed['like'] - 1
         #마이너스한 좋아요 수 업데이트
         dblog.feeds.update_one({'name': name_receive, 'loca':loca_receive}, {'$set': {'like': minus_like}})
         #댓글삭제
         dblog.feeds.update_one({'name': name_receive, 'loca':loca_receive}, {'$unset': {'Comment.' + str(ID_receive): 1}})
         #DB에서 ID 삭제
         if checkID and isinstance(checkID['ID'], list):
            #배열일 경우 하나만 삭제
            dblog.feeds.update_one({'name': name_receive, 'loca':loca_receive}, {'$pull':{'ID':ID_receive}})
            return jsonify({'result':'cancel','msg':'좋아요를 취소합니다.'})
         else:
            #필드일 경우 삭제
            dblog.feeds.delete_one({'name': name_receive, 'loca':loca_receive, 'ID':ID_receive})
            return jsonify({'result':'cancel', 'msg':'좋아요를 취소합니다.'})

         
      else:
         #없으면 좋아요 업데이트
         #feed의 like에 1을 더해준 plus_like 변수
         print('좋아요 +1')
         plus_like = feed['like'] + 1
         #plus한 좋아요 수 업데이트
         dblog.feeds.update_one({'name': name_receive, 'loca':loca_receive}, {'$set': {'like': plus_like}})
         if comment_receive != '':
            dblog.feeds.update_one({'name': name_receive, 'loca':loca_receive}, {'$set': {f'Comment.{ID_receive}': comment_receive},'$addToSet': {'ID': ID_receive}})
         #DB에서 ID 추가
         dblog.feeds.update_one({'name': name_receive, 'loca':loca_receive}, {'$push':{'ID':ID_receive}})
         return jsonify({'result':'success', 'msg':'이 맛집을 좋아합니다.'})

   else:
      print('카드 최초 업데이트')
      #해당 DB에 최초로 상호가 등록된거니까 바로 insert
      if comment_receive != '':
        dblog.feeds.insert_one({'name':name_receive, 'like':1, 'loca': loca_receive, 'ID':[ID_receive], 'Comment':{ID_receive: comment_receive}})
      else :
         dblog.feeds.insert_one({'name':name_receive, 'like':1, 'loca': loca_receive, 'ID':[ID_receive]})
      return jsonify({'result':'success', 'msg':'이 맛집을 좋아합니다.'})

#feeds 불러오기
@app.route('/api/list', methods=['GET'])
def show_feeds():
   if not 'id' in session:
     return make_response(redirect(url_for('home'))) 
   # 1. db에서 좋아요 0인 데이터 삭제
   dblog.feeds.delete_many({'like' : 0})
   # 2. db에서 feeds 목록 전체를 검색합니다. ID는 제외하고 like 가 많은 순으로 정렬합니다.
   feed = list(dblog.feeds.find({}, {'_id': False}).sort('like', -1))

   #성공하면 feeds_list 목록을 클라이언트에 전달
   return jsonify({'result':'success', 'feeds_list':feed})

@app.route('/api/comment', methods=['POST'])
def show_comment():
   if not 'id' in session:
     return make_response(redirect(url_for('home'))) 
   name_receive = request.form['name_give']
   loca_receive = request.form['loca_give']
   feed = dblog.feeds.find_one({'name':name_receive, 'loca':loca_receive})
   
   comment = feed.get('Comment')
   if comment:
      id_list = []
      
      comment_list = []
      for key, value in comment.items():
         id_list.append(key)
         comment_list.append(value)
      print(comment_list)
      return jsonify({'result':'success', 'id_list':id_list, 'comment_list':comment_list})
   else:
      return jsonify({'result':'None', 'msg': '등록된 댓글이 없습니다'})


if __name__ == '__main__':
    app.run('0.0.0.0',port=5000,debug=True)
