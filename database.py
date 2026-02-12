import pymysql
import pymysql.cursors
import os
import hashlib
import traceback
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import USE_MYSQL, MYSQL_CONFIG, USE_ENCRYPTION, ENCRYPTION_CONFIG

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.db_type = "mysql" if USE_MYSQL else "sqlite"
        self._is_connected = False

        self.use_encryption = bool(USE_ENCRYPTION)
        self.cipher_suite = None
        
        if self.use_encryption:
            self.init_encryption()

    def init_encryption(self):
        try:
            password = ENCRYPTION_CONFIG['password'].encode()
            salt = ENCRYPTION_CONFIG['salt']
            if isinstance(salt, str):
                salt = salt.encode()
                
            iterations = ENCRYPTION_CONFIG.get('iterations', 100000)

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=iterations,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.cipher_suite = Fernet(key)
        except Exception as e:
            print(f"Ошибка инициализации шифрования: {e}")
            self.use_encryption = False 

    def encrypt_data(self, data: str):
        if not data: return data
        if not self.use_encryption or not self.cipher_suite: return data
        try:
            return self.cipher_suite.encrypt(str(data).encode()).decode()
        except Exception as e:
            print(f"Ошибка шифрования: {e}")
            return data

    def decrypt_data(self, encrypted_data):
        if not encrypted_data: return ""
        if not self.use_encryption or not self.cipher_suite: return encrypted_data
        try:
            return self.cipher_suite.decrypt(str(encrypted_data).encode()).decode()
        except Exception:
            return str(encrypted_data)

    def connect(self):
        if self._is_connected and self.connection:
            try:
                self.connection.ping(reconnect=True)
                return True
            except:
                self._is_connected = False

        try:
            print(f"Подключение к TiDB Cloud ({MYSQL_CONFIG['host']})...")
            self.connection = pymysql.connect(
                host=MYSQL_CONFIG['host'],
                port=MYSQL_CONFIG['port'],
                user=MYSQL_CONFIG['user'],
                password=MYSQL_CONFIG['password'],
                database=MYSQL_CONFIG['database'],
                ssl_ca=MYSQL_CONFIG['ssl_ca'],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            self.cursor = self.connection.cursor()
            self._is_connected = True
            print("Успешное подключение!")
            
            return True
        except Exception as e:
            print(f"Ошибка подключения к БД: {e}")
            self._is_connected = False
            return False

    def close(self):
        try:
            if self.cursor: self.cursor.close()
            if self.connection: self.connection.close()
        except Exception:
            pass
        finally:
            self._is_connected = False
            self.cursor = None
            self.connection = None

    def execute_query(self, query, params=None, fetchone=False, fetchall=False):
        if not self.connect():
            return None
        try:
            if self.db_type == "mysql" and "?" in query:
                query = query.replace("?", "%s")

            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            query_lower = query.strip().lower()
            if query_lower.startswith(("select", "show")):
                if fetchone: return self.cursor.fetchone()
                if fetchall: return self.cursor.fetchall()
                return self.cursor.fetchall()
            
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка SQL запроса: {e}\nЗапрос: {query}")
            return None

    def init_database(self):
        """Создает таблицы с учетом MySQL синтаксиса"""
        try:
            create_employees = """
            CREATE TABLE IF NOT EXISTS employees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fio TEXT NOT NULL,
                phone TEXT NOT NULL,
                department TEXT NOT NULL,
                position TEXT NOT NULL,
                campus VARCHAR(100),
                room VARCHAR(100)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """
            
            create_users = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """
            
            self.execute_query(create_employees)
            self.execute_query(create_users)

            self.force_create_test_users()
            
            return True
        except Exception as e:
            print(f"Ошибка при инициализации БД: {e}")
            return False

    def force_create_test_users(self):
        try:
            if not self.user_exists('admin'):
                self.add_user('admin', 'admin123', 'admin')
                print("Создан пользователь: admin")
            if not self.user_exists('user'):
                self.add_user('user', 'user123', 'user')
        except Exception as e:
            print(f"Ошибка создания тестовых юзеров: {e}")


    def hash_password(self, password: str):
        return hashlib.sha256(password.encode()).hexdigest()

    def user_exists(self, username):
        res = self.execute_query("SELECT id FROM users WHERE username = %s", (username,), fetchone=True)
        return res is not None

    def add_user(self, username, password, role="user"):
        p_hash = self.hash_password(password)
        return self.execute_query(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, p_hash, role)
        )

    def get_all_users(self):
        return self.execute_query("SELECT id, username, role, created_at FROM users", fetchall=True)

    def delete_user(self, user_id):
        return self.execute_query("DELETE FROM users WHERE id=%s", (user_id,))


    def get_all_employees(self):
        rows = self.execute_query("SELECT * FROM employees ORDER BY id", fetchall=True)
        if not rows: return []
        
        result = []
        for r in rows:
            result.append((
                r['id'],
                self.decrypt_data(r['fio']),
                self.decrypt_data(r['phone']),
                self.decrypt_data(r['department']),
                self.decrypt_data(r['position']),
                r['campus'],
                r['room']
            ))
        return result

    def add_employee(self, fio, phone, department, position, campus, room):
        return self.execute_query(
            "INSERT INTO employees (fio, phone, department, position, campus, room) VALUES (%s, %s, %s, %s, %s, %s)",
            (self.encrypt_data(fio), self.encrypt_data(phone), self.encrypt_data(department), 
             self.encrypt_data(position), campus, room)
        )

    def update_employee(self, emp_id, fio, phone, department, position, campus, room):
        return self.execute_query(
            "UPDATE employees SET fio=%s, phone=%s, department=%s, position=%s, campus=%s, room=%s WHERE id=%s",
            (self.encrypt_data(fio), self.encrypt_data(phone), self.encrypt_data(department), 
             self.encrypt_data(position), campus, room, emp_id)
        )

    def delete_employee(self, emp_id):
        return self.execute_query("DELETE FROM employees WHERE id=%s", (emp_id,))

    def delete_employees_bulk(self, emp_ids: list):
        """
        Удаляет несколько сотрудников, используя список ID.
        """
        if not emp_ids:
            return True
        placeholders = ', '.join(['%s'] * len(emp_ids))
        
        query = f"DELETE FROM employees WHERE id IN ({placeholders})"
        
        return self.execute_query(query, tuple(emp_ids))