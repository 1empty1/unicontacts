import customtkinter as ctk
from tkinter import ttk, messagebox, Menu, filedialog
import tkinter as tk
from tkinter import font as tkfont
import sys
import os
import traceback
import re
import subprocess
from datetime import datetime
from collections import Counter
import gc

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from database import DatabaseManager
from auth import AuthManager
from exporter import DataExporter

ctk.set_appearance_mode("Dark")

COLOR_BG = "#1a1a1a"
COLOR_SIDEBAR = "#141414"
COLOR_CARD = "#2b2b2b"
COLOR_ACCENT = "#3B8ED0"
COLOR_TEXT = "#EAEAEA"
COLOR_INPUT_BG = "#1f1f1f"

COLOR_SUCCESS = "#27AE60"
COLOR_ERROR = "#E74C3C"
COLOR_WARNING = "#F39C12"

HOVER_GREEN = "#1e4d2b"
HOVER_ORANGE = "#4a3b2a"
HOVER_RED = "#4a2a2a"
HOVER_DARK = "#262626"
HOVER_LOGOUT = "#4a2a3a"


class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None

    def showtip(self, text, x, y):
        self.text = text
        if self.tipwindow or not self.text:
            return
        x += self.widget.winfo_rootx() + 15
        y += self.widget.winfo_rooty() + 10
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        frame = tk.Frame(tw, background="#202020", bd=0, relief=tk.FLAT)
        frame.pack()
        label = tk.Label(frame, text=self.text, justify=tk.LEFT,
                         background="#202020", foreground="#ffffff",
                         font=("Segoe UI", 10), relief=tk.FLAT,
                         padx=10, pady=5, borderwidth=0, highlightthickness=0)
        label.pack()
        tw.attributes("-alpha", 0.95)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw: tw.destroy()


class CustomMessageDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, type_="info"):
        super().__init__(parent)
        self.title(title)
        
        if type_ == "error":
            self.color = COLOR_ERROR
            symbol = "!"
        elif type_ == "success":
            self.color = COLOR_SUCCESS
            symbol = "✓"
        elif type_ == "warning":
            self.color = COLOR_WARNING
            symbol = "!"
        else:
            self.color = COLOR_ACCENT
            symbol = "i"

        w = 400 
        h = 280
        
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        
        self.transient(parent)
        self.grab_set()

        top_bar = ctk.CTkFrame(self, height=8, fg_color=self.color, corner_radius=0)
        top_bar.pack(fill="x")

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text="", height=1).pack(expand=True)

        icon_btn = ctk.CTkButton(main_frame, text=symbol, 
                               font=("Segoe UI Black", 24),
                               width=50, height=50,
                               corner_radius=25,
                               fg_color=self.color,
                               hover=False,
                               state="disabled",
                               text_color_disabled="white")
        icon_btn.pack(pady=(0, 15))

        ctk.CTkLabel(main_frame, text=title, 
                    font=("Segoe UI", 18, "bold"), 
                    text_color="white").pack(pady=(0, 10))
        
        msg_label = ctk.CTkLabel(main_frame, text=message, 
                                font=("Segoe UI", 14), 
                                text_color="#cccccc", 
                                wraplength=350, 
                                justify="center")
        msg_label.pack(pady=(0, 25))

        ctk.CTkButton(main_frame, text="OK", command=self.destroy, 
                     fg_color=self.color, 
                     hover_color=self.adjust_color(self.color), 
                     font=("Segoe UI", 12, "bold"),
                     width=120, height=35).pack()

        ctk.CTkLabel(main_frame, text="", height=1).pack(expand=True)

    def adjust_color(self, hex_color):
        return hex_color

def show_custom_message(parent, title, message, type_="info"):
    CustomMessageDialog(parent, title, message, type_)


class CustomConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, yes_command):
        super().__init__(parent)
        self.yes_command = yes_command
        self.title(title)
        
        w, h = 400, 200
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="❓", font=("Segoe UI", 40), anchor="center").pack(pady=(20, 5), anchor="center")
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 16, "bold"), text_color="white", anchor="center").pack(anchor="center")
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 13), text_color="#cccccc", anchor="center").pack(pady=(5, 20), anchor="center")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10, anchor="center")

        ctk.CTkButton(btn_frame, text="Да", command=self.on_yes, fg_color=COLOR_ERROR, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Нет", command=self.destroy, fg_color="#3a3a3a", width=100).pack(side="left", padx=10)

    def on_yes(self):
        self.destroy()
        self.yes_command()


class AuthDialog(ctk.CTkToplevel):
    def __init__(self, parent, auth_manager):
        super().__init__(parent)
        self.parent = parent
        self.auth_manager = auth_manager
        self.user_data = None
        self.is_login_mode = True

        self.title("Аутентификация")
        self.geometry("500x520")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.bind("<Return>", lambda e: self.login() if self.is_login_mode else self.register())

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(main_frame, text="Вход в систему", font=("Segoe UI", 24, "bold"))
        self.title_label.pack(pady=(30, 20))

        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=50, pady=10)

        ctk.CTkLabel(form_frame, text="Логин:", font=("Segoe UI", 14), anchor="w").pack(anchor="w", pady=(0, 5))
        self.username_entry = ctk.CTkEntry(form_frame, font=("Segoe UI", 14), height=40, fg_color=COLOR_INPUT_BG)
        self.username_entry.pack(fill="x", pady=(0, 15))
        self.username_entry.focus_set()

        ctk.CTkLabel(form_frame, text="Пароль:", font=("Segoe UI", 14), anchor="w").pack(anchor="w", pady=(0, 5))
        self.password_entry = ctk.CTkEntry(form_frame, font=("Segoe UI", 14), height=40, show="•", fg_color=COLOR_INPUT_BG)
        self.password_entry.pack(fill="x", pady=(0, 15))

        self.confirm_password_label = ctk.CTkLabel(form_frame, text="Подтверждение пароля:", font=("Segoe UI", 14), anchor="w")
        self.confirm_password_entry = ctk.CTkEntry(form_frame, font=("Segoe UI", 14), height=40, show="•", fg_color=COLOR_INPUT_BG)

        self.button_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=25)

        self.action_button = ctk.CTkButton(self.button_frame, text="Войти", command=self.login,
                                           fg_color=COLOR_ACCENT, font=("Segoe UI", 14, "bold"), height=40)
        self.action_button.pack(fill="x", pady=(0, 15))

        self.bottom_btn_frame = ctk.CTkFrame(self.button_frame, fg_color="transparent")
        self.bottom_btn_frame.pack(fill="x")

        self.guest_btn = ctk.CTkButton(self.bottom_btn_frame, text="Войти как Гость", command=self.guest_login,
                      fg_color="transparent", border_width=1, border_color="#2a4b2a", 
                      text_color="#8edfae", font=("Segoe UI", 12), width=120, height=30)
        self.guest_btn.pack(side="left")

        self.switch_mode_button = ctk.CTkButton(self.bottom_btn_frame, text="Регистрация", command=self.switch_mode,
                                                fg_color="transparent", text_color="gray70", hover_color="#2b2b2b",
                                                font=("Segoe UI", 12, "underline"), width=100, height=30)
        self.switch_mode_button.pack(side="right")

        self.test_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.test_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(self.test_frame, text="Тестовые пользователи:", font=("Segoe UI", 12), text_color="gray70").pack(anchor="w")
        ctk.CTkLabel(self.test_frame, text="admin/admin123 (полные права)", font=("Segoe UI", 10), text_color="gray50").pack(anchor="w")

    def switch_mode(self):
        self.is_login_mode = not self.is_login_mode
        if self.is_login_mode:
            self.geometry("500x520")
            self.title_label.configure(text="Вход в систему")
            self.action_button.configure(text="Войти", command=self.login)
            self.switch_mode_button.configure(text="Регистрация")
            self.confirm_password_label.pack_forget()
            self.confirm_password_entry.pack_forget()
            self.guest_btn.pack(side="left")
            self.test_frame.pack(fill="x", pady=10)
        else:
            self.geometry("500x620") 
            self.title_label.configure(text="Регистрация")
            self.action_button.configure(text="Создать аккаунт", command=self.register)
            self.switch_mode_button.configure(text="Я уже зарегистрирован")
            self.guest_btn.pack_forget()
            self.test_frame.pack_forget()
            self.confirm_password_label.pack(anchor="w", pady=(0, 5))
            self.confirm_password_entry.pack(fill="x", pady=(0, 20))
            self.button_frame.pack_forget()
            self.button_frame.pack(fill="x", pady=25)

        self.password_entry.delete(0, 'end')
        self.confirm_password_entry.delete(0, 'end')

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            show_custom_message(self, "Ошибка", "Введите логин и пароль!", "error")
            return
        try:
            user_data = self.auth_manager.authenticate(username, password)
            if user_data:
                self.user_data = user_data
                self.destroy()
            else:
                show_custom_message(self, "Ошибка", "Неверный логин или пароль!", "error")
        except Exception as e:
            show_custom_message(self, "Ошибка", f"Ошибка аутентификации: {str(e)}", "error")

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()
        if not username or not password:
            show_custom_message(self, "Ошибка", "Заполните все поля!", "error")
            return
        if len(username) < 3:
            show_custom_message(self, "Ошибка", "Логин должен содержать минимум 3 символа!", "error")
            return
        if len(password) < 4:
            show_custom_message(self, "Ошибка", "Пароль должен содержать минимум 4 символа!", "error")
            return
        if password != confirm_password:
            show_custom_message(self, "Ошибка", "Пароли не совпадают!", "error")
            return
        try:
            success, message = self.auth_manager.register_user(username, password)
            if success:
                show_custom_message(self, "Успех", message, "success")
                self.is_login_mode = True
                self.switch_mode()
                self.username_entry.delete(0, 'end')
                self.username_entry.insert(0, username)
                self.password_entry.focus_set()
            else:
                show_custom_message(self, "Ошибка", message, "error")
        except Exception as e:
            show_custom_message(self, "Ошибка", f"Ошибка регистрации: {str(e)}", "error")

    def guest_login(self):
        self.user_data = {'id': 0, 'username': 'guest', 'role': 'guest'}
        self.destroy()


class UltimatePhoneBook(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("University Database System")
        self.geometry("1280x800")
        self.minsize(1000, 650)
        self.configure(fg_color=COLOR_BG)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._is_closing = False
        self.table_font = tkfont.Font(family="Segoe UI", size=12)
        self.header_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")

        self.db_manager = DatabaseManager()
        if not self.db_manager.init_database():
            messagebox.showerror("Ошибка", "Не удалось инициализировать базу данных!")
            self.destroy()
            return

        self.auth_manager = AuthManager(self.db_manager)
        try:
            auth_dialog = AuthDialog(self, self.auth_manager)
            self.wait_window(auth_dialog)
            if not auth_dialog.user_data:
                self.destroy()
                return

            self.current_user = auth_dialog.user_data
            self.exporter = DataExporter(self.db_manager)

            if not self.db_manager.connect():
                messagebox.showerror("Ошибка", "Не удалось подключиться к БД!")
                self.destroy()
                return

            self.column_settings = {
                "id": {"text": "ID", "min": 30, "max": 100, "width": 50, "stretch": False},
                "fio": {"text": "ФИО Сотрудника", "min": 250, "max": 5000, "width": 300, "stretch": True},
                "phone": {"text": "Телефон", "min": 150, "max": 1000, "width": 150, "stretch": False},
                "dept": {"text": "Отдел", "min": 200, "max": 5000, "width": 250, "stretch": True},
                "pos": {"text": "Должность", "min": 150, "max": 5000, "width": 200, "stretch": True},
                "campus": {"text": "Корпус", "min": 60, "max": 2000, "width": 70, "stretch": False},
                "room": {"text": "Каб.", "min": 50, "max": 500, "width": 60, "stretch": False}
            }
            
            self.active_frame = None
            self.employee_frame = None
            self.users_frame = None

            self.create_sidebar()
            self.create_main_container()
            self.show_employee_list() 
            self.create_context_menu() 

            self.tooltip = ToolTip(self.tree)
            self.tree.bind("<Double-1>", self.on_double_click)
            self.tree.bind("<Motion>", self.on_tree_motion)
            self.tree.bind("<Leave>", lambda e: self.tooltip.hidetip())
            self.bind("<Button-1>", self.on_window_click)
            self.main_container.bind("<Button-1>", self.on_empty_area_click)
            self.refresh_data()
            self.update_clock()
            
        except Exception as e:
            if "application has been destroyed" not in str(e):
                messagebox.showerror("Ошибка", f"Не удалось запустить приложение: {str(e)}")
                print(f"Ошибка запуска: {traceback.format_exc()}")
            self.destroy()

    def on_window_click(self, event):
        """Обработчик клика по окну для снятия фокуса"""
        if not self._is_closing:
            try:
                widget = event.widget
                
                if hasattr(self, 'search_entry') and widget != self.search_entry and not self.is_child_of(widget, self.search_entry):
                    self.focus_set()
                    
            except Exception:
                pass

    def on_empty_area_click(self, event):
        """Обработчик клика по пустой области для снятия выделения"""
        if not self._is_closing:
            try:
                widget = event.widget
                
                if hasattr(self, 'search_entry'):
                    self.focus_set()
                
                if hasattr(self, 'tree') and widget != self.tree and not self.is_child_of(widget, self.tree):
                    self.tree.selection_remove(self.tree.selection())
                    
            except Exception:
                pass

    def is_child_of(self, widget, parent):
        """Проверяет, является ли widget дочерним элементом parent"""
        try:
            while widget:
                if widget == parent:
                    return True
                widget = widget.master
            return False
        except:
            return False

    def update_clock(self):
        if not self._is_closing:
            try:
                now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                self.clock_label.configure(text=f"🕒 {now}")
                self.after(1000, self.update_clock)
            except:
                pass

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(side="top", fill="x", padx=0, pady=0)
        
        self.logo_label = ctk.CTkButton(logo_frame, text="UNI\nCONTACTS", font=("Segoe UI Black", 28), 
                                        text_color=COLOR_ACCENT, fg_color="transparent", hover=False, 
                                        anchor="w", command=self.show_employee_list)
        self.logo_label.pack(side="left", padx=20, pady=(40, 20))

        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=30)
        
        self.create_menu_btn(bottom_frame, "🚪", "Выйти", self.logout, HOVER_LOGOUT)

        self.status_label = ctk.CTkLabel(bottom_frame, text=f"● {self.current_user['username']} ({self.current_user['role']})",
                                         font=("Consolas", 13, "bold"), text_color="#27AE60", anchor="w")
        self.status_label.pack(anchor="w", pady=(10, 0))
        
        self.clock_label = ctk.CTkLabel(bottom_frame, text="🕒 --:--:--", font=("Consolas", 13), text_color="#A0A0A0", anchor="w")
        self.clock_label.pack(anchor="w", pady=(0, 0))

        db_type = "MySQL" if self.db_manager.db_type == "mysql" else "SQLite"
        self.db_status_label = ctk.CTkLabel(bottom_frame, text=f"● БД: {db_type} (✓)",
                                            font=("Consolas", 11), text_color="#27AE60", anchor="w")
        self.db_status_label.pack(anchor="w", pady=(0, 0))

        self.menu_scroll_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        self.menu_scroll_frame.pack(side="top", fill="both", expand=True)
        
        self.create_menu_btn(self.menu_scroll_frame, "📋", "Список сотрудников", self.show_employee_list, HOVER_DARK)
        
        sep1 = ctk.CTkFrame(self.menu_scroll_frame, height=2, fg_color="#333333")
        sep1.pack(fill="x", padx=20, pady=5)

        self.create_menu_btn(self.menu_scroll_frame, "➕", "Новый сотрудник", self.open_add_dialog, HOVER_GREEN)
        self.create_menu_btn(self.menu_scroll_frame, "✏️", "Редактировать", self.edit_record, HOVER_ORANGE)
        self.create_menu_btn(self.menu_scroll_frame, "🗑", "Удалить запись", self.delete_record, HOVER_RED)
        
        sep2 = ctk.CTkFrame(self.menu_scroll_frame, height=2, fg_color="#333333")
        sep2.pack(fill="x", padx=20, pady=10)
        
        self.create_menu_btn(self.menu_scroll_frame, "🔄", "Обновить базу", self.refresh_data, HOVER_DARK)
        self.create_menu_btn(self.menu_scroll_frame, "📊", "Экспорт в Excel", self.export_data, HOVER_DARK)
        
        if HAS_MATPLOTLIB:
             self.create_menu_btn(self.menu_scroll_frame, "📈", "Статистика", self.show_statistics_view, HOVER_DARK)

        if self.current_user.get('role') == 'admin':
            self.create_menu_btn(self.menu_scroll_frame, "👥", "Пользователи", self.show_users_view, HOVER_DARK)

        self.create_menu_btn(self.menu_scroll_frame, "ℹ️", "О программе", self.show_about_view, HOVER_DARK)
        self.create_menu_btn(self.menu_scroll_frame, "❓", "Справка", self.show_help_view, HOVER_DARK)

    def create_menu_btn(self, parent, icon, text, command, hover_color):
        btn_frame = ctk.CTkFrame(parent, height=50, corner_radius=10, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=5)
        
        btn_frame.grid_columnconfigure(0, minsize=50)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        lbl_icon = ctk.CTkLabel(btn_frame, text=icon, font=("Segoe UI", 20), text_color="#cccccc")
        lbl_icon.grid(row=0, column=0, pady=10)
        
        lbl_text = ctk.CTkLabel(btn_frame, text=text, font=("Segoe UI Semibold", 15), text_color="#cccccc", anchor="w")
        lbl_text.grid(row=0, column=1, sticky="ew", pady=10)
        
        def on_enter(e):
            if not self._is_closing: btn_frame.configure(fg_color=hover_color)
        def on_leave(e):
            if not self._is_closing: btn_frame.configure(fg_color="transparent")
        def on_click(e):
            if not self._is_closing: command()
            
        for widget in [btn_frame, lbl_icon, lbl_text]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)

    def create_context_menu(self):
        self.context_menu = Menu(self, tearoff=0, bg="#2b2b2b", fg="white", 
                                 activebackground=COLOR_ACCENT, activeforeground="white",
                                 font=("Segoe UI", 10))
        self.context_menu.add_command(label="✏️ Редактировать", command=self.edit_record)
        self.context_menu.add_command(label="🗑 Удалить", command=self.delete_record)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔄 Обновить", command=self.refresh_data)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def create_main_container(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

    def switch_to_view(self, new_view):
        if self.active_frame is not None:
            self.active_frame.destroy()
            self.active_frame = None

        if new_view:
            if self.employee_frame:
                self.employee_frame.pack_forget()
            self.active_frame = new_view
            self.active_frame.pack(fill="both", expand=True)
        else:
            if self.employee_frame:
                self.employee_frame.pack(fill="both", expand=True)

    def show_employee_list(self):
        if self.employee_frame is None:
            self.create_employee_frame()
        self.switch_to_view(None)

    def create_employee_frame(self):
        self.employee_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        self.employee_frame.grid_columnconfigure(0, weight=1)
        self.employee_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self.employee_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(header_frame, text="База данных персонала", font=("Segoe UI", 24, "bold")).pack(side="left")

        search_card = ctk.CTkFrame(self.employee_frame, fg_color=COLOR_CARD, corner_radius=15, height=80)
        search_card.grid(row=0, column=0, sticky="ew", pady=(50, 20))
        search_card.pack_propagate(False)
        inner_search = ctk.CTkFrame(search_card, fg_color="transparent")
        inner_search.pack(fill="both", expand=True, padx=20, pady=20)

        self.search_entry = ctk.CTkEntry(inner_search, placeholder_text="🔍  Введите запрос для поиска...",
                                         height=40, font=("Segoe UI", 14), border_width=0, fg_color=COLOR_INPUT_BG)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.search_entry.bind("<Return>", lambda e: self.perform_search())
        self.search_entry.bind("<KeyRelease>", self.on_search_change)

        self.search_indicator = ctk.CTkLabel(inner_search, text="", width=20, font=("Segoe UI", 14), text_color="#E67E22")
        self.search_indicator.pack(side="left", padx=(0, 10))

        self.filter_segment = ctk.CTkSegmentedButton(inner_search, values=["Все", "Телефон", "ФИО", "Отдел"],
                                                     font=("Segoe UI", 12, "bold"), height=40, corner_radius=10,
                                                     fg_color=COLOR_INPUT_BG, selected_color=COLOR_ACCENT,
                                                     command=self.on_filter_change)
        self.filter_segment.set("Все")
        self.filter_segment.pack(side="left", padx=(0, 15))

        ctk.CTkButton(inner_search, text="НАЙТИ", width=100, height=40, command=self.perform_search,
                      font=("Segoe UI", 12, "bold"), fg_color=COLOR_ACCENT).pack(side="left", padx=(0, 10))
        ctk.CTkButton(inner_search, text="✖", width=40, height=40, command=self.reset_search,
                      font=("Segoe UI", 14, "bold"), fg_color="#3a3a3a", hover_color="#4a2a2a").pack(side="left")

        table_card = ctk.CTkFrame(self.employee_frame, fg_color=COLOR_CARD, corner_radius=15)
        table_card.grid(row=1, column=0, sticky="nsew")
        
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(table_card, text="📋  Список сотрудников", font=("Segoe UI", 16, "bold"), text_color="gray70").grid(row=0, column=0, sticky="w", padx=25, pady=15)

        tree_container = ctk.CTkFrame(table_card, fg_color="transparent")
        tree_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self.setup_tree_style()
        columns = list(self.column_settings.keys())
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="extended")

        for col_id in columns:
            settings = self.column_settings[col_id]
            self.tree.heading(col_id, text=settings["text"], command=self.autosize_columns)
            anchor = "center" if col_id in ["id", "campus", "room"] else "w"
            should_stretch = settings.get("stretch", False)
            self.tree.column(col_id, width=settings["width"], minwidth=settings["min"], stretch=should_stretch, anchor=anchor)

        self.tree.grid(row=0, column=0, sticky="nsew")
        
        self.vsb = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.tree.yview)
        self.vsb.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        
        self.hsb = ctk.CTkScrollbar(tree_container, orientation="horizontal", command=self.tree.xview)
        self.hsb.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        self.count_label = ctk.CTkLabel(table_card, text="Всего записей: 0", font=("Segoe UI", 12), text_color="gray50")
        self.count_label.grid(row=2, column=0, sticky="e", padx=20, pady=10)

    def show_statistics_view(self):
        if not HAS_MATPLOTLIB:
             show_custom_message(self, "Ошибка", "Библиотека matplotlib не установлена!", "error")
             return

        employees = self.db_manager.get_all_employees()
        if not employees:
            show_custom_message(self, "Инфо", "Нет данных для статистики", "warning")
            return
        
        depts = [e[3] for e in employees]
        campuses = [e[5] for e in employees]
        dept_counts = Counter(depts)
        campus_counts = Counter(campuses)

        stats_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        ctk.CTkLabel(stats_frame, text="📈 Статистика базы данных", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 20))

        plt.style.use("dark_background")
        fig = plt.figure(figsize=(10, 6), facecolor=COLOR_BG)
        
        ax1 = fig.add_subplot(121)
        colors = ["#3B8ED0", "#27AE60", "#E67E22", "#E74C3C", "#8E44AD", "#F1C40F"]
        
        wedges, texts, autotexts = ax1.pie(campus_counts.values(), labels=campus_counts.keys(), autopct="%1.1f%%", 
                startangle=90, colors=colors, wedgeprops=dict(width=0.5, edgecolor=COLOR_BG), pctdistance=0.75)
        
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(9)
            autotext.set_fontweight("bold")
            
        ax1.set_title("Сотрудники по корпусам", color="white", pad=20, fontsize=14)

        ax2 = fig.add_subplot(122)
        dept_names = list(dept_counts.keys())
        dept_vals = list(dept_counts.values())
        
        bars = ax2.barh(dept_names, dept_vals, color=COLOR_ACCENT, height=0.6)
        ax2.set_title("Сотрудники по отделам", color="white", pad=20, fontsize=14)
        
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.spines["left"].set_color("#444444")
        ax2.spines["bottom"].set_color("#444444")
        
        for bar in bars:
            width = bar.get_width()
            ax2.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                     f"{int(width)}", ha="left", va="center", color="white", fontweight="bold")

        ax2.grid(axis="x", linestyle="--", alpha=0.3)

        for ax in [ax1, ax2]:
            ax.set_facecolor(COLOR_BG)
            ax.tick_params(colors="white")

        fig.tight_layout(pad=3.0)

        canvas_frame = ctk.CTkFrame(stats_frame, fg_color=COLOR_CARD, corner_radius=15)
        canvas_frame.pack(fill="both", expand=True)
        
        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

        self.switch_to_view(stats_frame)

    def show_help_view(self):
        help_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        ctk.CTkLabel(help_frame, text="❓ Справка", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 20))
        
        text_box = ctk.CTkTextbox(help_frame, font=("Segoe UI", 14), fg_color=COLOR_CARD, corner_radius=15)
        text_box.pack(fill="both", expand=True)
        
        help_text = ("РУКОВОДСТВО ПОЛЬЗОВАТЕЛЯ\n\n"
                     "1. ПОИСК И ФИЛЬТРАЦИЯ\n"
                     "   Используйте строку поиска в верхней части экрана. Выберите критерий фильтрации "
                     "(Телефон, ФИО, Отдел) для точного поиска.\n\n"
                     "2. УПРАВЛЕНИЕ СОТРУДНИКАМИ\n"
                     "   - Добавление: Нажмите кнопку '+' в меню слева.\n"
                     "   - Редактирование: Дважды кликните по строке в таблице или используйте кнопку '✏️'.\n"
                     "   - Удаление: Выберите строку и нажмите '🗑' или используйте контекстное меню (ПКМ).\n\n"
                     "3. ЭКСПОРТ ДАННЫХ\n"
                     "   Кнопка 'Экспорт в Excel' создает файл .xlsx в папке с программой на основе шаблона template.xlsx.\n\n"
                     "4. АДМИНИСТРИРОВАНИЕ\n"
                     "   Доступно только пользователям с ролью 'admin'. Позволяет добавлять пользователей и менять их права.\n\n"
                     "5. БЕЗОПАСНОСТЬ\n"
                     "   Все персональные данные (ФИО, Телефон) хранятся в базе данных в зашифрованном виде.")
        
        text_box.insert("0.0", help_text)
        text_box.configure(state="disabled") 
        
        self.switch_to_view(help_frame)

    def show_users_view(self):
        if self.current_user.get("role") != "admin":
             show_custom_message(self, "Ошибка", "Доступ запрещен!", "warning")
             return

        users_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        top_bar = ctk.CTkFrame(users_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(top_bar, text="👥 Управление пользователями", font=("Segoe UI", 24, "bold")).pack(side="left")
        
        ctk.CTkButton(top_bar, text="+ Добавить пользователя", command=self.open_add_user_dialog,
                      fg_color=COLOR_SUCCESS, hover_color=HOVER_GREEN, font=("Segoe UI", 12, "bold")).pack(side="right")

        table_card = ctk.CTkFrame(users_frame, fg_color=COLOR_CARD, corner_radius=15)
        table_card.pack(fill="both", expand=True)

        tree_container = ctk.CTkFrame(table_card, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        columns = ("id", "username", "role", "created")
        users_tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="extended")
        
        users_tree.heading("id", text="ID")
        users_tree.heading("username", text="Логин")
        users_tree.heading("role", text="Роль")
        users_tree.heading("created", text="Дата создания")
        
        users_tree.column("id", width=50, anchor="center")
        users_tree.column("username", width=200)
        users_tree.column("role", width=150, anchor="center")
        users_tree.column("created", width=200)
        
        users_tree.pack(side="left", fill="both", expand=True)
        
        vsb = ctk.CTkScrollbar(tree_container, orientation="vertical", command=users_tree.yview)
        vsb.pack(side="right", fill="y")
        users_tree.configure(yscrollcommand=vsb.set)

        action_frame = ctk.CTkFrame(table_card, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(action_frame, text="Сменить роль выбранного на:", font=("Segoe UI", 12)).pack(side="left", padx=(0, 10))
        role_var = ctk.StringVar(value="user")
        role_combo = ctk.CTkComboBox(action_frame, values=["admin", "operator", "user"], variable=role_var, width=120, state="readonly")
        role_combo.pack(side="left", padx=(0, 10))
        
        def change_role_action():
            selection = users_tree.selection()
            if not selection:
                show_custom_message(self, "Ошибка", "Выберите пользователя!", "warning")
                return
            item = selection[0]
            u_data = users_tree.item(item, "values")
            if u_data[1] == self.current_user["username"]:
                show_custom_message(self, "Ошибка", "Нельзя менять свою роль!", "error")
                return
            
            new_role = role_var.get()
            if self.db_manager.execute_query("UPDATE users SET role = ? WHERE id = ?", (new_role, u_data[0])):
                show_custom_message(self, "Успех", "Роль обновлена", "success")
                refresh_users_list()
            else:
                show_custom_message(self, "Ошибка", "Сбой БД", "error")

        ctk.CTkButton(action_frame, text="Применить", command=change_role_action, width=100, fg_color=COLOR_ACCENT).pack(side="left")

        def delete_user_action():
            selection = users_tree.selection()
            if not selection:
                show_custom_message(self, "Ошибка", "Выберите пользователя!", "warning")
                return
            item = selection[0]
            u_data = users_tree.item(item, "values")
            if u_data[1] == self.current_user["username"]:
                show_custom_message(self, "Ошибка", "Нельзя удалить себя!", "error")
                return
            
            def confirm_del():
                if self.auth_manager.delete_user(u_data[0]):
                    show_custom_message(self, "Успех", "Пользователь удален", "success")
                    refresh_users_list()
                else:
                    show_custom_message(self, "Ошибка", "Сбой удаления", "error")

            CustomConfirmDialog(self, "Удаление", f"Удалить {u_data[1]}?", confirm_del)

        ctk.CTkButton(action_frame, text="Удалить выбранного", command=delete_user_action, 
                      fg_color=COLOR_ERROR, hover_color=HOVER_RED).pack(side="right")

        def refresh_users_list():
            for i in users_tree.get_children(): users_tree.delete(i)
            users = self.auth_manager.get_all_users()
            for u in users:
                c_at = str(u["created_at"])[:19] if u["created_at"] else ""
                users_tree.insert("", "end", values=(u["id"], u["username"], u["role"], c_at))

        refresh_users_list()
        self.switch_to_view(users_frame)

    def open_add_user_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Новый пользователь")
        dialog.geometry("400x450")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        main_fr = ctk.CTkFrame(dialog, fg_color=COLOR_CARD, corner_radius=15)
        main_fr.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_fr, text="Создание пользователя", font=("Segoe UI", 18, "bold")).pack(pady=(20, 20))
        
        ctk.CTkLabel(main_fr, text="Логин", anchor="w").pack(fill="x", padx=30)
        u_entry = ctk.CTkEntry(main_fr, fg_color=COLOR_INPUT_BG)
        u_entry.pack(fill="x", padx=30, pady=(5, 15))
        
        ctk.CTkLabel(main_fr, text="Пароль", anchor="w").pack(fill="x", padx=30)
        p_entry = ctk.CTkEntry(main_fr, fg_color=COLOR_INPUT_BG)
        p_entry.pack(fill="x", padx=30, pady=(5, 15))
        
        ctk.CTkLabel(main_fr, text="Роль", anchor="w").pack(fill="x", padx=30)
        r_var = ctk.StringVar(value="user")
        r_combo = ctk.CTkComboBox(main_fr, values=["admin", "operator", "user"], variable=r_var, state="readonly")
        r_combo.pack(fill="x", padx=30, pady=(5, 25))
        
        def submit():
            login = u_entry.get().strip()
            password = p_entry.get().strip()
            role = r_var.get()
            
            if len(login) < 3 or len(password) < 4:
                show_custom_message(dialog, "Ошибка", "Логин от 3х, пароль от 4х символов", "error")
                return
            
            try:
                if self.db_manager.user_exists(login):
                    show_custom_message(dialog, "Ошибка", "Пользователь уже существует", "error")
                    return
                
                if self.db_manager.add_user(login, password, role):
                    show_custom_message(self, "Успех", f"Пользователь {login} создан!", "success")
                    dialog.destroy()
                    self.show_users_view()
                else:
                    show_custom_message(dialog, "Ошибка", "Ошибка БД", "error")
            except Exception as e:
                show_custom_message(dialog, "Ошибка", str(e), "error")

        ctk.CTkButton(main_fr, text="Создать", command=submit, fg_color=COLOR_SUCCESS, hover_color=HOVER_GREEN).pack(pady=10)


    def show_about_view(self):
        about_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        ctk.CTkLabel(about_frame, text="ℹ️ О программе", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 20))
        
        info_card = ctk.CTkFrame(about_frame, fg_color=COLOR_CARD, corner_radius=15)
        info_card.pack(fill="both", expand=True)
        
        info_text = ("Университетская Телефонная Книга\n"
                     "Версия: 1.0 Release\n\n"
                     "Разработано в рамках курсового проекта.\n\n"
                     "Стек технологий:\n"
                     "• Python 3.10+\n"
                     "• CustomTkinter (GUI)\n"
                     "• SQLite / MySQL (Data Storage)\n"
                     "• Matplotlib (Analytics)\n"
                     "• OpenPyXL (Reporting)\n\n"
                     "© 2025 Все права защищены.")
        
        label = ctk.CTkLabel(info_card, text=info_text, font=("Segoe UI", 16), justify="left", anchor="nw")
        label.pack(padx=40, pady=40, fill="both", expand=True)
        
        self.switch_to_view(about_frame)

    def setup_tree_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure("Treeview", background="#2b2b2b", foreground="#ffffff", fieldbackground="#2b2b2b", rowheight=45,
                        font=("Segoe UI", 12), borderwidth=0, highlightthickness=0, relief="flat")
        style.configure("Treeview.Heading", background="#202020", foreground="#b0b0b0", font=("Segoe UI", 12, "bold"),
                        relief="flat", borderwidth=0)
        style.map("Treeview.Heading", background=[('active', '#333333')])
        style.map("Treeview", background=[('selected', COLOR_ACCENT)], foreground=[('selected', 'white')])

    def load_data_from_db(self):
        try:
            self.tree.delete(*self.tree.get_children())
            employees = self.db_manager.get_all_employees()
            for emp in employees:
                self.tree.insert("", "end", values=emp)
            self.count_label.configure(text=f"Всего записей: {len(employees)}")
        except Exception as e:
            if not self._is_closing: show_custom_message(self, "Ошибка", f"Не удалось загрузить данные: {str(e)}", "error")

    def autosize_columns(self):
        if self._is_closing: return
        padding = 25
        for col_index, col_id in enumerate(self.column_settings.keys()):
            settings = self.column_settings[col_id]
            header_text = settings["text"]
            max_width = self.header_font.measure(header_text) + padding
            for item in self.tree.get_children():
                cell_value = str(self.tree.item(item, 'values')[col_index])
                text_width = self.table_font.measure(cell_value) + padding
                if text_width > max_width: max_width = text_width
            final_width = max(settings["min"], max_width)
            self.tree.column(col_id, width=final_width)

    def on_search_change(self, event=None):
        self.after(500, self.perform_search)

    def on_filter_change(self, value):
        self.perform_search()

    def perform_search(self):
        if self.active_frame is not None:
             self.show_employee_list()
             
        search_text = self.search_entry.get().strip()
        filter_type = self.filter_segment.get()
        if not search_text:
            self.refresh_data()
            self.search_indicator.configure(text="")
            return
        try:
            self.tree.delete(*self.tree.get_children())
            employees = self.db_manager.get_all_employees()
            filtered = []
            for emp in employees:
                if filter_type == "Все":
                    if (search_text.lower() in emp[1].lower() or search_text.lower() in emp[2].lower() or search_text.lower() in emp[3].lower()):
                        filtered.append(emp)
                elif filter_type == "ФИО":
                    if search_text.lower() in emp[1].lower(): filtered.append(emp)
                elif filter_type == "Телефон":
                    if search_text.lower() in emp[2].lower(): filtered.append(emp)
                elif filter_type == "Отдел":
                    if search_text.lower() in emp[3].lower(): filtered.append(emp)
            for emp in filtered:
                self.tree.insert("", "end", values=emp)
            self.count_label.configure(text=f"Найдено записей: {len(filtered)}")
            self.search_indicator.configure(text=f"{len(filtered)}")
        except Exception as e:
            show_custom_message(self, "Ошибка", f"Ошибка поиска: {str(e)}", "error")

    def reset_search(self):
        self.search_entry.delete(0, 'end')
        self.filter_segment.set("Все")
        self.refresh_data()
        self.show_employee_list()

    def on_tree_motion(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            item_id = self.tree.identify_row(event.y)
            column_id = self.tree.identify_column(event.x)
            if item_id and column_id:
                col_index = int(column_id.replace('#', '')) - 1
                values = self.tree.item(item_id, 'values')
                if col_index < len(values):
                    text = values[col_index]
                    if text:
                        self.tooltip.hidetip()
                        self.tooltip.showtip(text, event.x, event.y)
                        return
        self.tooltip.hidetip()

    def on_double_click(self, event):
        if self.tree.identify_region(event.x, event.y) in ["cell", "tree"] and self.tree.selection():
            self.edit_record()

    def open_add_dialog(self):
        if self.active_frame is not None:
            self.show_employee_list()
            return
        if not self.db_manager.connect():
            show_custom_message(self, "Ошибка", "Нет подключения к базе данных!", "error")
            return
        if self.current_user.get('role') not in ['admin', 'operator']:
            show_custom_message(self, "Ошибка", "Недостаточно прав!", "warning")
            return
        dialog = EmployeeDialog(self, "Добавить нового сотрудника", self.db_manager)
        dialog.wait_window()
        self.show_employee_list()

    def edit_record(self):
        if self.active_frame is not None:
            self.show_employee_list()
            return
        if not self.db_manager.connect():
            show_custom_message(self, "Ошибка", "Нет подключения к базе данных!", "error")
            return
        if self.current_user.get('role') not in ['admin', 'operator']:
            show_custom_message(self, "Ошибка", "Недостаточно прав!", "warning")
            return
        
        if self.active_frame is not None:
             show_custom_message(self, "Инфо", "Перейдите в список сотрудников для выбора записи.", "info")
             self.show_employee_list()
             return

        selection = self.tree.selection()
        if not selection:
            show_custom_message(self, "Предупреждение", "Выберите запись!", "warning")
            return
        if len(selection) > 1:
            show_custom_message(self, "Ошибка", "Для редактирования выберите только одного сотрудника!", "warning")
            return
        item = selection[0]
        employee_data = self.tree.item(item, 'values')
        dialog = EmployeeDialog(self, "Редактировать сотрудника", self.db_manager, employee_data)
        dialog.wait_window()

    def delete_record(self):
        if self.active_frame is not None:
            self.show_employee_list()
            return
        
        if self.current_user.get('role') not in ['admin', 'operator']:
            show_custom_message(self, "Ошибка", "У вас недостаточно прав для удаления записей!", "warning")
            return
            
        selected_items = self.tree.selection() 
            
        if not selected_items:
            show_custom_message(self, "Ошибка", "Выберите одну или несколько записей для удаления.", "warning")
            return
                
        def confirm_and_delete():
            emp_ids_to_delete = []
            for item in selected_items:
                try:
                    emp_id = int(self.tree.item(item, 'values')[0]) 
                    emp_ids_to_delete.append(emp_id)
                except (IndexError, ValueError):
                    continue
                
            if not emp_ids_to_delete:
                show_custom_message(self, "Ошибка", "Не удалось извлечь ID выбранных записей.", "error")
                return

            try:
                if self.db_manager.delete_employees_bulk(emp_ids_to_delete):
                    show_custom_message(self, "Успех", f"Успешно удалено {len(emp_ids_to_delete)} записей.", "success")
                    self.refresh_data() 
                else:
                    show_custom_message(self, "Ошибка", "Не удалось удалить записи из базы данных.", "error")
            except Exception as e:
                import traceback
                traceback.print_exc()
                show_custom_message(self, "Ошибка", f"Произошла ошибка при удалении: {str(e)}", "error")

        CustomConfirmDialog(
            self, 
            "Подтверждение удаления", 
            f"Вы уверены, что хотите удалить {len(selected_items)} выбранных записей?",
            confirm_and_delete
        )


    def refresh_data(self):
        try:
            self.load_data_from_db()
            self.autosize_columns()
            self.status_label.configure(text=f"● {self.current_user['username']} ({self.current_user['role']})")
            if self.active_frame is None:
                self.show_employee_list()
        except Exception as e:
            if not self._is_closing: show_custom_message(self, "Ошибка", f"Ошибка обновления: {str(e)}", "error")


    def export_data(self):
        if not self.db_manager.connect():
            show_custom_message(self, "Ошибка", "Нет подключения к базе данных!", "error")
            return
        
        default_filename = f"Employee_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        file_path = tk.filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        initialfile=default_filename,
        filetypes=[("Excel files", "*.xlsx")],
        title="Выберите место и имя для сохранения отчета"
    )

        if not file_path:
            return

        employees = self.db_manager.get_all_employees()
        exporter = DataExporter(self.db_manager)

        success, message = exporter.export_to_excel(employees, out_path=file_path)

        if success:
            show_custom_message(self, "Успех", message, "success")
        else:
            show_custom_message(self, "Ошибка", message, "error")


    def logout(self):
        def do_logout():
            self.withdraw()  # Скрываем текущее окно
            auth_dialog = AuthDialog(self, self.auth_manager)
            self.wait_window(auth_dialog)
            if auth_dialog.user_data:
                self.current_user = auth_dialog.user_data
                self.status_label.configure(text=f"● {self.current_user['username']} ({self.current_user['role']})")
                self.refresh_data()
                self.deiconify()  # Показываем главное окно снова
            else:
                self.destroy()  # Пользователь закрыл диалог входа — закрываем приложение
        CustomConfirmDialog(self, "Выход", "Вы точно хотите выйти?", do_logout)


    def on_closing(self):
        if self._is_closing: return
        self._is_closing = True
        try:
            if hasattr(self, 'db_manager'): self.db_manager.close()
        except: pass
        finally:
            try:
                self.quit()
                self.destroy()
            except:
                import os
                os._exit(0)


class EmployeeDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, db_manager, employee_data=None):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.employee_data = employee_data
        self.title(title)
        self.geometry("500x600")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        self.transient(parent)
        self.grab_set()
        self.create_widgets()
        if employee_data: self.fill_form()
        self.bind("<Return>", lambda e: self.save_employee())
        self.bind("<Escape>", lambda e: self.cancel())

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(main_frame, text=self.title(), font=("Segoe UI", 20, "bold")).pack(pady=20)
        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=30, pady=10)
        self.fio_entry = self.create_form_field(form_frame, "ФИО сотрудника:*", 0)
        self.phone_entry = self.create_form_field(form_frame, "Телефон:*", 1)
        self.department_entry = self.create_form_field(form_frame, "Отдел:*", 2)
        self.position_entry = self.create_form_field(form_frame, "Должность:*", 3)
        self.campus_entry = self.create_form_field(form_frame, "Корпус:*", 4)
        self.room_entry = self.create_form_field(form_frame, "Кабинет:*", 5)
        button_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        button_frame.grid(row=6, column=0, columnspan=2, pady=30, sticky="ew")
        ctk.CTkButton(button_frame, text="Сохранить", command=self.save_employee,
                      fg_color=COLOR_ACCENT, font=("Segoe UI", 14, "bold")).pack(side="right", padx=(10, 0))
        ctk.CTkButton(button_frame, text="Отмена", command=self.cancel,
                      fg_color="#3a3a3a", font=("Segoe UI", 14)).pack(side="right")

    def create_form_field(self, parent, label, row):
        ctk.CTkLabel(parent, text=label, font=("Segoe UI", 14), anchor="w").grid(row=row, column=0, sticky="w", pady=(15, 5))
        entry = ctk.CTkEntry(parent, font=("Segoe UI", 14), height=40, fg_color=COLOR_INPUT_BG)
        entry.grid(row=row, column=1, sticky="ew", pady=(15, 5), padx=(10, 0))
        return entry

    def fill_form(self):
        if self.employee_data:
            self.fio_entry.insert(0, self.employee_data[1])
            self.phone_entry.insert(0, self.employee_data[2])
            self.department_entry.insert(0, self.employee_data[3])
            self.position_entry.insert(0, self.employee_data[4])
            self.campus_entry.insert(0, self.employee_data[5])
            self.room_entry.insert(0, self.employee_data[6])

    def save_employee(self):
        fio = self.fio_entry.get().strip()
        phone = self.phone_entry.get().strip()
        department = self.department_entry.get().strip()
        position = self.position_entry.get().strip()
        campus = self.campus_entry.get().strip()
        room = self.room_entry.get().strip()

        if not all([fio, phone, department, position, campus, room]):
            show_custom_message(self, "Ошибка", "Все поля обязательны для заполнения!", "error")
            return

        if not re.match(r"^\+?[0-9\-\(\)\s]{5,20}$", phone):
             show_custom_message(self, "Ошибка", "Некорректный формат телефона!\nПример: +7(999)123-45-67", "warning")
             return

        room_clean = "".join(c for c in room if c.isalnum()).upper()
        if not room_clean:
            show_custom_message(self, "Ошибка", "Кабинет не может быть пустым после очистки.", "error")
            return
        room = room_clean

        try:
            if self.employee_data:
                success = self.db_manager.update_employee(self.employee_data[0], fio, phone, department, position, campus, room)
                action = "обновлена"
            else:
                success = self.db_manager.add_employee(fio, phone, department, position, campus, room)
                action = "добавлена"
            if success:
                msg_dialog = CustomMessageDialog(self, "Успех", f"Запись успешно {action}!", "success")
                self.wait_window(msg_dialog) 
                self.parent.refresh_data()
                self.destroy()
            else:
                show_custom_message(self, "Ошибка", f"Не удалось {action} запись!", "error")
        except Exception as e:
            show_custom_message(self, "Ошибка", f"Произошла ошибка: {str(e)}", "error")

    def cancel(self):
        self.destroy()


if __name__ == "__main__":
    try:
        app = UltimatePhoneBook()
        if app.winfo_exists():
            app.mainloop()
    except Exception as e:
        if "application has been destroyed" not in str(e):
            print(f"Критическая ошибка: {traceback.format_exc()}")
            try: messagebox.showerror("Ошибка", f"Критическая ошибка: {str(e)}")
            except: pass