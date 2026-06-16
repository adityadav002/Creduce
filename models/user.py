from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id):
        self.id = id

def register_user_loader(login_manager):
    @login_manager.user_loader
    def load_user(user_id):
        return User(user_id)
