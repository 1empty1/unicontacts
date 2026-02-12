import hashlib

class AuthManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def authenticate(self, username: str, password: str):
        if not username or not password:
            return None
        try:
            row = self.db.execute_query("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,), fetchone=True)
            if not row:
                return None

            if isinstance(row, dict):
                password_hash = row.get('password_hash')
                user_id = row.get('id')
                username = row.get('username')
                role = row.get('role')
            else:
                password_hash = row[2] if len(row) > 2 else ''
                user_id = row[0]
                username = row[1]
                role = row[3] if len(row) > 3 else 'user'

            if hashlib.sha256(password.encode()).hexdigest() == password_hash:
                return {'id': user_id, 'username': username, 'role': role}
            else:
                return None
        except Exception as e:
            print(f"Ошибка в authenticate: {e}")
            return None

    def register_user(self, username: str, password: str, role: str = "user"):
        if not username or not password:
            return False, "Имя пользователя и пароль обязательны"
        if len(username) < 3:
            return False, "Логин должен содержать минимум 3 символа"
        if len(password) < 4:
            return False, "Пароль должен содержать минимум 4 символа"
        try:
            if self.db.user_exists(username):
                return False, "Пользователь с таким именем уже существует"
            ok = self.db.add_user(username, password, role)
            if ok:
                return True, "Пользователь успешно создан"
            else:
                return False, "Ошибка при создании пользователя"
        except Exception as e:
            return False, f"Ошибка: {e}"

    def get_all_users(self):
        return self.db.get_all_users()

    def delete_user(self, user_id):
        return self.db.delete_user(user_id)