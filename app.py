from flask import Flask, request
from flask_restx import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager,create_access_token,jwt_required,get_jwt_identity
from flask_migrate import Migrate
from sqlalchemy import MetaData
from datetime import timedelta

app = Flask(__name__)
api = Api(app)
jwt=JWTManager(app)
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)
app.config['JWT_SECRET_KEY'] = 'https://jwt.io/#debugger-io?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] =timedelta(days=30) 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todos.db'
db = SQLAlchemy(app,metadata=metadata)
migrate=Migrate(app,db,render_as_batch=True)

# DB Models

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(50),unique=True, nullable=False)
    password=db.Column(db.String(50), nullable=False)
    todos=db.relationship('Todo',backref='user')

    def to_json(self):
        return {'id': self.id, 'username': self.username,'password':self.password}


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100))
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'))

    def to_dict(self):
        return {'id': self.id, 'content': self.content,"user_id":self.user_id}

# User register and login routes
@api.route('/register')
class UserReg(Resource):
    def post(self):
        username=request.json.get('username')
        password=request.json.get('password')
        if not username or not password:
            return {'error':'username or/and password is missing'},400
        existing_user=User.query.filter_by(username=username).first()
        if existing_user:
            return {'error':'username alreayy taken'}
        new_user=User(username=username,password=password)
        db.session.add(new_user)
        db.session.commit()
        return{'message':'user created successfully'},201

@api.route('/login')
class UserLogin(Resource):
    def post(self):
        username=request.json.get('username')
        password=request.json.get('password')
        if not username or not password:
            return {'error':'username and password is missing'},400
        user=User.query.filter_by(username=username).first()
        if user and user.password==password:
            access_token=create_access_token(identity=user.id)
            return {'message':'Login successful','access_token':access_token}
        else:
            return{'error':'Invalid credentials'},401
        
# Secured route
@api.route('/secure')
class Secure(Resource):
    @jwt_required()
    def get(self):
        current_user_id=get_jwt_identity()
        return {'userid':current_user_id}

# Todo routes
@api.route('/todos')
class TodoList(Resource):
    @jwt_required()
    def get(self):
        user_id=get_jwt_identity()
        todos=Todo.query.filter_by(user_id=user_id).all()
        if not todos:
            return{'message':'no todos found for this user.'}
        return [todo.to_dict() for todo in todos]
    
    @jwt_required()
    def post(self):
        current_user_id=get_jwt_identity()
        content = request.json.get('content')
        if not content:
            return {'error': 'Content is missing'}, 400

        todo = Todo(content=content,user_id=current_user_id)
        db.session.add(todo)
        db.session.commit()

        return todo.to_dict(), 201

@api.route('/todos/<int:todo_id>')
class TodoItem(Resource):
    def get(self, todo_id):
        todo = Todo.query.get(todo_id)
        if todo:
            return todo.to_dict(), 200
        else:
            return {'error': 'Todo not found'}, 404

    def put(self, todo_id):
        todo = Todo.query.get(todo_id)
        if todo:
            content = request.json.get('content')
            if content:
                todo.content = content
                db.session.commit()
                return todo.to_dict(), 200
            else:
                return {'error': 'Content is missin'}, 400
        else:
            return {'error': 'Todo not found'}, 404

    def delete(self, todo_id):
        todo = Todo.query.get(todo_id)
        if todo:
            db.session.delete(todo)
            db.session.commit()
            return {'message': 'Todo delted'},
        else:
            return {'error': 'Todo not found'}, 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)