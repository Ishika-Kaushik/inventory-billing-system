import tkinter as tk
from tkinter import ttk , messagebox
import sqlite3
from tkinter import filedialog
from PIL import Image, ImageTk
from fpdf import FPDF
import datetime
import random
import os
import sys
import matplotlib.pyplot as plt

##Global variable
PRIMARY = "#2C3E50"
ACCENT = "#3498DB"
SUCCESS = "#27AE60"
DANGER = "#E74C3C"
WARNING = "#F39C12"
BG_COLOR = "#f5f7fa"
current_user = None
current_role = None

##Database Setup

def setup_database():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price REAL,
        quantity INTEGER,
        location TEXT,
        image TEXT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        product TEXT,
        quantity INTEGER,
        time TEXT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        quantity INTEGER,
        price REAL,
        total REAL,
        customer TEXT,
        date TEXT
    )""")
    cursor.execute("PRAGMA table_info(logs)")
    columns = [col[1] for col in cursor.fetchall()]

    if "quantity" not in columns:
        cursor.execute("ALTER TABLE logs ADD COLUMN quantity INTEGER DEFAULT 0")

    # default admin (only once)
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users(username, password, role) VALUES (?, ?, ?)",
            ("admin", "admin123", "admin")
        )
        
    conn.commit()
    conn.close()

def auto_backup():
    backup_folder = "backups"
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    today = datetime.datetime.now().strftime("%Y%m%d")

    for file in os.listdir(backup_folder):
        if file.startswith(today):
            return  

    filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.db")
    path = os.path.join(backup_folder, filename)

    shutil.copy("inventory.db", path)

def clean_old_backups():
    backup_folder = "backups"
    if not os.path.exists(backup_folder):
        return

    files = sorted(
        [os.path.join(backup_folder, f) for f in os.listdir(backup_folder)],
        key=os.path.getmtime
    )

    if len(files) > 7:
        for f in files[:-7]:
            os.remove(f)

def login_screen():
    login_win = tk.Toplevel()
    login_win.title("Login")
    login_win.configure(bg="#f5f7fa")
    
    def center_window(win, width=400, height=350):
        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()

        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))

        win.geometry(f"{width}x{height}+{x}+{y}")

    center_window(login_win, 400, 350)
        
    card = tk.Frame(login_win, bg="white", bd=0, relief="flat")
    card.place(relx=0.5, rely=0.5, anchor="center", width=300, height=260)

    tk.Label(card, text="Welcome Back", font=("Segoe UI", 16, "bold"), bg="white").pack(pady=10)

    

    def clear_placeholder(entry, placeholder, is_password=False):
        def on_focus_in(e):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                if is_password:
                    entry.config(show="*")
                if not username or not password:
                    messagebox.showerror("Error", "Fields cannot be empty")
                    return

        def on_focus_out(e):
            if entry.get() == "":
                entry.insert(0, placeholder)
                if is_password:
                    entry.config(show="")

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    entry_user = tk.Entry(card, font=("Segoe UI", 11))
    entry_user.pack(pady=10, ipady=5)
    entry_user.insert(0, "Username")
    clear_placeholder(entry_user, "Username")

    entry_pass = tk.Entry(card, font=("Segoe UI", 11), show="")
    entry_pass.pack(pady=10, ipady=5)
    entry_pass.insert(0, "Password")
    clear_placeholder(entry_pass, "Password", is_password=True)
    
    def login():
        username = entry_user.get().strip().lower()
        password = entry_pass.get().strip()


        if username == "Username" or password == "Password":
            messagebox.showerror("Error", "Please enter valid credentials")
            return

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT role FROM users WHERE username=? AND password=?",
            (username, password)
        )
        result = cursor.fetchone()
        conn.close()

        global current_user, current_role

        if result:
            current_user = username
            current_role = result[0]
            try:
                auto_backup()
                clean_old_backups()
            except Exception as e:
                print("Backup failed:", e)
            
            login_win.destroy()
            root.deiconify()
            apply_role(current_role)
            show_logged_user(current_user, current_role)
        else:
            messagebox.showerror("Error", "Invalid credentials")

    login_win.bind("<Return>", lambda e: login())
    entry_user.bind("<Return>", lambda e: login())
    entry_pass.bind("<Return>", lambda e: login())

    tk.Button(
        card,
        text="Login",
        bg="#3498DB",
        fg="white",
        font=("Segoe UI", 11, "bold"),
        command=login
    ).pack(pady=15, fill="x", padx=20)

    

def log_action(action, product="", qty=0):
    global current_user

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO logs(user, action, product, quantity, time)
        VALUES (?, ?, ?, ?, ?)
    """, (
        current_user,
        action,
        product,
        qty,
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    
    conn.commit()
    conn.close()

def view_logs():
    log_win = tk.Toplevel(root)
    log_win.title("Activity Logs")

    tree_log = ttk.Treeview(log_win,
        columns=("User", "Action", "Product", "Qty", "Time"),
        show="headings"
    )

    tree_log.heading("User", text="User")
    tree_log.heading("Action", text="Action")
    tree_log.heading("Product", text="Product")
    tree_log.heading("Time", text="Time")
    tree_log.heading("Qty", text="Quantity")

    tree_log.tag_configure("center", anchor="center")

    tree_log.column("User", width=100, anchor="center")
    tree_log.column("Action", width=100, anchor="center")
    tree_log.column("Product", width=100, anchor="center")
    tree_log.column("Time", width=140, anchor="center")
    tree_log.column("Qty", width=60, anchor="center")

    tree_log.pack(fill="both", expand=True)

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user, action, product, quantity, time FROM logs ORDER BY id DESC")

    for row in cursor.fetchall():
        tree_log.insert("", "end", values=row)

    btn_frame = tk.Frame(log_win)
    btn_frame.pack(pady=5)

    tk.Button(btn_frame, text="Export CSV", command=export_logs_csv).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Export PDF", command=export_logs_pdf).pack(side="left", padx=5)

    conn.close()

import csv

def export_logs_csv():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user, action, product, time FROM logs")
    rows = cursor.fetchall()
    conn.close()

    file = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")]
    )

    if not file:
        return

    with open(file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["User", "Action", "Product", "Time"])
        writer.writerows(rows)

    messagebox.showinfo("Success", "Logs exported to CSV!")


def export_logs_pdf():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user, action, product, time FROM logs")
    rows = cursor.fetchall()
    conn.close()

    file = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")]
    )

    if not file:
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=9)

    pdf.cell(0, 10, "Activity Logs", ln=True, align="C")
    pdf.ln(5)

    for row in rows:
        text = f"User: {row[0]} | Action: {row[1]} | Product: {row[2]} | Time: {row[3]}"
        pdf.multi_cell(0, 8, text)

    pdf.output(file)

    messagebox.showinfo("Success", "Logs exported to PDF!")


selected_id = None
cart = {}

def resource_path(file_name):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, file_name)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)

##root window
setup_database()
root = tk.Tk()
root.title("Inventory & Billing System")
root.geometry("1000x650")
root.configure(bg=BG_COLOR)



main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

topbar = tk.Frame(root, bg="white", height=50)
topbar.pack(side="top", fill="x")

topbar.pack_propagate(False)

SIDEBAR_WIDTH = 200
is_sidebar_open = True

def show_logged_user(username, role):
    label_user = tk.Label(
        topbar,
        text=f"{username} ({role})",
        bg="white",
        fg="#2C3E50",
        font=("Segoe UI", 10, "bold")
    )
    label_user.pack(side="right", padx=15)

def apply_role(role):
    for btn in sidebar.winfo_children():
        text = btn.cget("text")

        if role == "staff":
            # staff restrictions
            if any(x in text for x in ["Delete", "Update", "Add Staff"]):
                btn.pack_forget()
                   # hide buttons completely

        elif role == "admin":
            pass
def logout():
    global current_user
    current_user = None
    root.withdraw()
    login_screen()

def open_register():
    reg_win = tk.Toplevel(root)
    reg_win.title("Add Staff")
    reg_win.geometry("300x250")

    tk.Label(reg_win, text="Add Staff", font=("Segoe UI", 14)).pack(pady=10)

    entry_user = tk.Entry(reg_win)
    entry_user.pack(pady=5)
    entry_user.insert(0, "Username")

    entry_pass = tk.Entry(reg_win, show="*")
    entry_pass.pack(pady=5)
    entry_pass.insert(0, "Password")

    def register():
        username = entry_user.get().strip()
        password = entry_pass.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Fill all fields")
            return

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users(username, password, role) VALUES (?, ?, ?)",
                (username, password, "staff")
            )
            conn.commit()
            messagebox.showinfo("Success", "Staff added!")
            reg_win.destroy()
        except:
            messagebox.showerror("Error", "User already exists")

        conn.close()

        

    tk.Button(reg_win, text="Add Staff", command=register).pack(pady=10)

def animate_sidebar(opening, step=20):
    current_width = sidebar_canvas.winfo_width()

    if opening:
        new_width = current_width + step
        if new_width >= SIDEBAR_WIDTH:
            new_width = SIDEBAR_WIDTH
        sidebar_canvas.config(width=new_width)

        if new_width < SIDEBAR_WIDTH:
            root.after(10, lambda: animate_sidebar(True))

    else:
        new_width = current_width - step
        if new_width <= 0:
            new_width = 0
        sidebar_canvas.config(width=new_width)

        if new_width > 0:
            root.after(10, lambda: animate_sidebar(False))




def toggle_sidebar():
    global is_sidebar_open
    if is_sidebar_open:
        animate_sidebar(opening=False)
        is_sidebar_open = False

    else:
        animate_sidebar(opening=True)
        is_sidebar_open = True



menu_btn = tk.Button(
    topbar,
    text="☰",
    font=("Segoe UI", 16, "bold"),
    bg="white",
    fg="#2C3E50",
    bd=0,
    command=toggle_sidebar,
    cursor="hand2",
    activebackground="#dcdde1"
)
menu_btn.pack(side="left", padx=10, pady=5)
def on_menu_hover(e):
    menu_btn.config(bg="#dcdde1")

def on_menu_leave(e):
    menu_btn.config(bg="white")

menu_btn.bind("<Enter>", on_menu_hover)
menu_btn.bind("<Leave>", on_menu_leave)



title_top = tk.Label(
    topbar,
    text="Inventory Dashboard",
    font=("Segoe UI", 14, "bold"),
    bg="white",
    fg="#2C3E50"
)
title_top.pack(side="left", padx=10)

sidebar_container = tk.Frame(main_frame)
sidebar_container.pack(side="left", fill="y")

sidebar_canvas = tk.Canvas(
    sidebar_container,
    bg="#2C3E50",
    width=SIDEBAR_WIDTH,
    highlightthickness=0
)
sidebar_canvas.pack(side="left", fill="y")

sidebar_scroll = tk.Scrollbar(
    sidebar_container,
    orient="vertical",
    command=sidebar_canvas.yview
)
sidebar_scroll.pack(side="right", fill="y")

sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)

sidebar = tk.Frame(sidebar_canvas, bg="#2C3E50")

sidebar_window = sidebar_canvas.create_window(
    (0, 0),
    window=sidebar,
    anchor="nw"
)

def update_sidebar_scroll(event):
    sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))

sidebar.bind("<Configure>", update_sidebar_scroll)

def sidebar_mousewheel(event):
    sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

sidebar_canvas.bind("<Enter>", lambda e: sidebar_canvas.bind_all("<MouseWheel>", sidebar_mousewheel))
sidebar_canvas.bind("<Leave>", lambda e: sidebar_canvas.unbind_all("<MouseWheel>"))


canvas = tk.Canvas(main_frame, bg=BG_COLOR, highlightthickness=0)
canvas.pack(side="left", fill="both", expand=True, padx=0, pady=0)

scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")

canvas.configure(yscrollcommand=scrollbar.set)
canvas.config(borderwidth=0, highlightthickness=0)


scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def resize_frame(event):
    canvas.itemconfig(canvas_window, width=event.width)

canvas.bind("<Configure>", resize_frame)

def update_scrollregion(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

print(scrollable_frame.winfo_width(), scrollable_frame.winfo_height())
content = scrollable_frame


def _on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

def enable_canvas_scroll(event):
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

def disable_canvas_scroll(event):
    canvas.unbind_all("<MouseWheel>")
    
def _on_shift_mousewheel(event):
    canvas.xview_scroll(int(-1*(event.delta/120)), "units")

canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)



title = tk.Label(
    content,
    text="Inventory & Billing System",
    font=("Segoe UI", 22, "bold"),
    bg=BG_COLOR,
    fg=PRIMARY
)
title.pack(pady=10)

label_total = None
label_low = None

def create_card(parent):
    return tk.Frame(parent, bg="white", bd=0, highlightthickness=1, highlightbackground="#ddd")

def create_stat_card(parent, title):
    global label_total, label_low

    card = tk.Frame(parent, bg="white", bd=1, relief="solid")
    card.pack(side="left", expand=True, fill="x", padx=10)

    tk.Label(card, text=title, font=("Segoe UI", 12)).pack()

    if title == "Total Products":
        label_total = tk.Label(card, text="0", font=("Segoe UI", 16, "bold"))
        label_total.pack()

    elif title == "Low Stock":
        label_low = tk.Label(card, text="0", font=("Segoe UI", 16, "bold"))
        label_low.pack()

stats_frame = tk.Frame(content, bg=BG_COLOR)
stats_frame.pack(fill="x", padx=20, pady=10)

create_stat_card(stats_frame, "Total Products")
create_stat_card(stats_frame, "Low Stock")

def update_dashboard():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM products")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products WHERE quantity < 5")
    low = cursor.fetchone()[0]

    conn.close()

    if label_total:
        label_total.config(text=str(total))
    if label_total:
        label_low.config(text=str(low))



update_dashboard()

def auto_update():
    update_dashboard()
    root.after(5000, auto_update)

auto_update()





frame_form = create_card(content)
frame_form.pack(padx=20, pady=15, fill="x")
billing_frame = tk.Frame(content, bg="white", bd=1, relief="solid")
billing_frame.pack_forget()

tk.Label(frame_form, text="Product Name*").grid(row=0, column=0, padx=5, pady=(5,5))
entry_name = tk.Entry(frame_form, font=("Segoe UI", 11), bd=1, relief="solid")
entry_name.grid(row=1, column=0, padx=10, pady=5)

tk.Label(frame_form, text="Price*").grid(row=0, column=1, padx=5, pady=(5,5))
entry_price = tk.Entry(frame_form, font=("Segoe UI", 11), bd=1, relief="solid")
entry_price.grid(row=1, column=1, padx=10, pady=5)

tk.Label(frame_form, text="Quantity*").grid(row=0, column=2, padx=5, pady=(5,5))
entry_qty = tk.Entry(frame_form, font=("Segoe UI", 11), bd=1, relief="solid")
entry_qty.grid(row=1, column=2, padx=10, pady=5)

tk.Label(frame_form, text="Sale Quantity").grid(row=0, column=3, padx=5, pady=(5,5))
entry_sale = tk.Entry(frame_form, font=("Segoe UI", 11), bd=1, relief="solid")
entry_sale.grid(row=1, column=3, padx=10, pady=5)

tk.Label(frame_form, text="Search Product").grid(row=0, column=4, padx=5, pady=(5,5))
entry_search = tk.Entry(frame_form, font=("Segoe UI", 11), bd=1, relief="solid")
entry_search.grid(row=1, column=4, padx=10, pady=5)


tk.Label(frame_form, text="Customer Name*").grid(row=2, column=0)
entry_customer = tk.Entry(frame_form, font=("Segoe UI", 11), bd=1, relief="solid")
entry_customer.grid(row=3, column=0, padx=10)

tk.Label(frame_form, text="Phone*").grid(row=2, column=1)
entry_phone = tk.Entry(frame_form, font=("Segoe UI", 11), bd=1, relief="solid")
entry_phone.grid(row=3, column=1, padx=10)

tk.Label(frame_form, text="Stock Location").grid(row=2, column=3)
entry_location = tk.Entry(frame_form)
entry_location.grid(row=3, column=3, padx=10)

tk.Label(frame_form, text="Product Image").grid(row=2, column=4)
entry_image = tk.Entry(frame_form)
entry_image.grid(row=3, column=4, padx=10)

tk.Label(frame_form, text="Discount").grid(row=2, column=2)
frame_discount = tk.Frame(frame_form)
frame_discount.grid(row=3, column=2, padx=10)
entry_discount = tk.Entry(frame_discount, font=("Segoe UI", 11), bd=1, relief="solid")
entry_discount.pack(side="left")

entry_discount.insert(0, "0")

discount_type = ttk.Combobox(
    frame_discount,
    values=["%", "₹"],
    width=5,
    state="readonly"
)
discount_type.pack(side="left", padx=5)
discount_type.set("%")  

result_label = tk.Label(root, text="")
result_label.pack()



##Utility Functions

def clear_fields():
    entry_name.delete(0, tk.END)
    entry_price.delete(0, tk.END)
    entry_qty.delete(0, tk.END)
    entry_sale.delete(0, tk.END)
    entry_search.delete(0, tk.END)
    entry_location.delete(0,tk.END)
    entry_image.delete(0, tk.END)
    


def highlight_empty_fields():
    for entry in [entry_name, entry_price, entry_qty]:
        if entry.get().strip() == "":
            entry.config(bg="#ffcccc")
        else:
            entry.config(bg="white")


def add_product():
    global selected_id
    name = entry_name.get().strip().lower()
    price = entry_price.get().strip()
    qty = entry_qty.get().strip()
    location = entry_location.get().strip()
    image = entry_image.get().strip()

    

    highlight_empty_fields()
    if not name or not price or not qty :
        messagebox.showerror("Error", "please fill Name , Price and Quantity ")
        return

    try:
        price = float(price)
        qty = int(qty)

        if qty < 0 or qty > 1000000:
            messagebox.showerror("Error", "Quantity must be between 0 and 10,00,000")
            return

        if price < 0 or price > 1000000:
            messagebox.showerror("Error", "Price must be resonable")
            return
    except:
        messagebox.showerror("Error", "Invalid input!")
        return
    
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM products WHERE name=?", (name,))
    existing = cursor.fetchone()

    if existing:
        messagebox.showerror("Error", "Product already exists! Use Update instead.")
        conn.close()
        return

    
    else:    
        cursor.execute("""
             INSERT INTO products(name, price, quantity, location, image)
             VALUES (?, ?, ?, ?, ?)
        """,(name, price, qty, location, image))
        messagebox.showinfo("Success", "Product Added!")
    conn.commit()
    conn.close()

    log_action("Added Product", name, qty)
    selected_id = None
    clear_fields()                    
    view_products()



##Tree View

frame_table = tk.Frame(content)
frame_table.pack(fill="both", expand=True, padx=20, pady=10)
tree = ttk.Treeview(frame_table,
    columns=("SNO", "Name", "Price", "Quantity", "Location", "Image"),
    show="headings"
)
tree.heading("SNO", text="S No.")
tree.heading("Name", text="Name")
tree.heading("Price", text="Price")
tree.heading("Quantity", text="Quantity")
tree.heading("Location", text="Location")
tree.heading("Image", text="Image")

tree.column("Location", width=120)
tree.column("SNO", width=60, anchor="center")
tree.column("Name", width=200)
tree.column("Price", width=100, anchor="center")
tree.column("Quantity", width=100, anchor="center")
tree.column("Image", width=0, stretch=False)

tree.tag_configure("low", background="#ffe6e6")
tree.tag_configure("even", background="#f8f9fa")
tree.tag_configure("odd", background="#ffffff")
tree.tag_configure("search",background="#cce5ff")
tree.config(selectmode="extended")

tree.focus_set()

tree.bind("<Enter>", disable_canvas_scroll)
tree.bind("<Leave>", enable_canvas_scroll)

style = ttk.Style()
style.theme_use("default")
style.configure(
    "Treeview",
    font=("Segoe UI", 10),
    rowheight=28,
    background="white",
    fieldbackground="white"
)
style.map(
    "Treeview",
    background=[("selected", "#3498DB")],
    foreground=[("selected", "white")]
)
    
style.configure(
    "Treeview.Heading",
    font=("Segoe UI", 11, "bold"),
    background=PRIMARY,
    foreground="white"
)

footer = tk.Label(
    content,
    text="Developed by Ishika Kaushik",
    bg=BG_COLOR,
    fg="gray"
)
footer.pack(pady=5)

scrollbar = tk.Scrollbar(frame_table, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)

scrollbar.pack(side="right", fill="y")
tree.pack(side="left", fill="both", expand=True)

image_label = tk.Label(content, bg=BG_COLOR)
image_label.pack(pady=5, anchor="e", padx=20)

import shutil

def browse_image():
    file = filedialog.askopenfilename(
        filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
    )
    if not file:
        return
    
    folder = resource_path("images")
    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = os.path.basename(file)
    dest_path = os.path.join(folder, filename)

    if os.path.abspath(file) != os.path.abspath(dest_path):
        shutil.copy(file, dest_path)

        
        
        entry_image.delete(0, tk.END)
        entry_image.insert(0, filename)

        preview_image()

tk.Button(frame_form, text="Browse", command=browse_image).grid(row=3, column=5)


def show_image_from_db(pid):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT image FROM products WHERE id=?", (pid,))
    result = cursor.fetchone()
    conn.close()

    path = result[0] if result else None

    if path :
        img_path = os.path.join(resource_path("images"), path)
    else:
        img_path = resource_path("assets/default.png")

    try:
        img = Image.open(img_path)
        img = img.resize((120, 120))
        img = ImageTk.PhotoImage(img)

        image_label.config(image=img)
        image_label.image = img
    except:
        image_label.config(text="No Image", image="")
def preview_image(event=None):
    filename = entry_image.get().strip()

    if filename == "":
        image_label.config(image="")
        return
    path = os.path.join(resource_path("images"), filename)
    
    if os.path.exists(path):
        try:
            img = Image.open(path)
            img = img.resize((120, 120))
            img = ImageTk.PhotoImage(img)

            image_label.config(image=img)
            image_label.image = img
        except:
            image_label.config(image="")
    else:
        image_label.config(image="")
            

entry_image.bind("<KeyRelease>", preview_image)
entry_image.bind("<FocusOut>", preview_image)

def select_product(event):
    global selected_id

    selected_items = tree.selection()
    if not selected_items:
        return
    
    if len(selected_items)>1:
        selected_id = None
        print("multiple selected:", selected_items)
        return
    selected = selected_items[0]
    selected_id = int(selected)

    result_label.config(text="")
        
    values = tree.item(selected, "values")

    entry_name.delete(0, tk.END)
    entry_name.insert(0, values[1])

    entry_price.delete(0, tk.END)
    entry_price.insert(0, values[2])

    entry_qty.delete(0, tk.END)
    entry_qty.insert(0, values[3])

    entry_location.delete(0, tk.END)
    entry_location.insert(0, values[4])

    entry_image.delete(0, tk.END)
    entry_image.insert(0, values[5])

    entry_sale.delete(0,tk.END)
    entry_sale.focus()

    show_image_from_db(selected_id)

tree.bind("<ButtonRelease-1>", select_product)
tree.bind("<KeyRelease-Up>", select_product)
tree.bind("<KeyRelease-Down>", select_product)

def view_products():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    
    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()
    conn.close()

    for item in tree.get_children():
        tree.delete(item)

    for i, row in enumerate(rows, start=1):
        tag = "even" if i % 2 == 0 else "odd"
        
        if row[3]<5:
            tag = "low"
            tree.insert(
                "", "end",
                values=(i, row[1], row[2], row[3], row[4], row[5]),
                tags=(tag,),
                iid=row[0]
            )
        else:
            tree.insert(
                "", "end",
                values=(i, row[1], row[2], row[3], row[4], row[5]),
                tags=(tag,),
                iid=row[0]
            )

        

def update_product():
    global selected_id

    if selected_id is None:
        result_label.config(text = "Select product first!")
        return
    name = entry_name.get().strip().lower()
    price = entry_price.get().strip()
    qty = entry_qty.get().strip()
    location = entry_location.get().strip()
    image = entry_image.get().strip()
    highlight_empty_fields()

    if not name or not price or not qty:
        messagebox.showerror("Error", "fill Name, Price and Quantity!")
        
    try :
        price = float(price)
        qty= int(qty)
    except:
        messagebox.showerror("Error", "Fill Price and Quantity!")
        return

    try:
        price = float(price)
        qty = int(qty)

        if qty < 0 or qty > 1000000:
            messagebox.showerror("Error", "Quantity must be between 0 and 10,00,000")
            return

        if price < 0 or price > 1000000:
            messagebox.showerror("Error", "Price must be resonable")
            return
    except:
        messagebox.showerror("Error", "Invalid input!")
        return
    
    
            

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM products WHERE name=? AND id!=?", (name, selected_id))
    if cursor.fetchone():
        messagebox.showerror("Error", "Product name already exists!")
        conn.close()
        return        
    
    cursor.execute("""
    UPDATE products
    SET name=?, price=?, quantity=?, location=?, image=?
    WHERE id=?
    """, (name, price, qty, location, image, selected_id))
    
    conn.commit()
    conn.close()

    log_action("Updated Product", name, qty)
    messagebox.showinfo("Success", "Product updated!")
    selected_id = None
    clear_fields()
    view_products()



def delete_product():
    global selected_id

    if selected_id is None:
        result_label.config(text="Select product first!")
        return
    name = entry_name.get()
    confirm = messagebox.askyesno("Confirm", "Delete this product?")
    if not confirm:
        return
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM products WHERE id=?", (selected_id,))

    conn.commit()
    conn.close()

    log_action("Deleted Product", name, 0)
    messagebox.showinfo("Success", "Product deleted!")
    selected_id = None
    clear_fields()
    view_products()
    
    
    


def search_product():
    keyword = entry_search.get().strip().lower()

    if keyword == "":
        view_products()
        return

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT*FROM products WHERE name LIKE ?", ('%' + keyword + '%',))
    rows = cursor.fetchall()
    conn.close()

    for item in tree.get_children():
        tree.delete(item)

    for i, row in enumerate(rows, start=1):
        tree.insert(
            "", "end",
            values=(i, row[1], row[2], row[3], row[4], row[5]),
            iid=row[0],
            tags=("search")
        )

    clear_fields()
    
    

def record_sale():
    global selected_id

    if selected_id is None:
        result_label.config(text="Select product first!")
        return
    qty_sold = entry_sale.get().strip()
    try:
        qty_sold = int(qty_sold)
    except:
        messagebox.showerror("Error", "Enter valid sale quantity!")
        return

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("SELECT quantity FROM products WHERE id=?", (selected_id,))
    current = cursor.fetchone()

    if current:
        if qty_sold <= current[0]:
            new_qty = current[0] - qty_sold
            cursor.execute(
                "UPDATE products SET quantity=? WHERE id=?",
                (new_qty, selected_id)
            )
            messagebox.showinfo("Success", "Sale recorded!")
        else:
            messagebox.showerror("Error", "Not enough stock!")
    else:
        messagebox.showinfo("Error", "Product not found!")

    name = entry_name.get()
    conn.commit()
    conn.close()

    log_action("Sold Product", name, qty_sold)
    
    selected_id = None
    clear_fields()
    entry_sale.delete(0, tk.END)
    view_products()
    
    


    
## Billing

def generate_bill():
    global cart

    customer = entry_customer.get().strip()
    phone = entry_phone.get().strip()

    if not customer or not phone:
        messagebox.showerror("Error", "Enter customer details!")
        return

    if not cart:
        messagebox.showerror("Error", "Cart is empty!")
        return

    invoice_no = generate_invoice_no()
    date = datetime.datetime.now().strftime("%d-%m-%y %H:%M")
    
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    invoice_data = []
    subtotal = 0

    for pid, item in cart.items():
        qty = item["qty"]
        price = item["price"]

        cursor.execute("SELECT name, quantity FROM products WHERE id=?", (pid,))
        result = cursor.fetchone()

        if not result:
            continue
        


        name, stock_qty = result

        if qty > stock_qty:
            messagebox.showerror("Error", f"Not enough stock for {name}!")
            conn.close()
            return

        total = price * qty
        subtotal += total
        invoice_data.append((pid, name, price, qty, total))

    discount_value = entry_discount.get().strip()
    dtype = discount_type.get()

    try:
        discount_value = float(discount_value)
    except:
        messagebox.showerror("Error", "Invalid discount!")
        return

    if discount_value < 0:
        messagebox.showerror("Error", "Discount cannot be negative!")
        return


    if dtype == "%":
        discount_amount = (subtotal * discount_value) / 100
    else:  
        discount_amount = discount_value


    if discount_amount > subtotal:
        messagebox.showerror("Error", "Discount too large!")
        return

    after_discount = subtotal - discount_amount
    gst = after_discount * 0.18
    grand_total = after_discount + gst
    
    
    bill_window = tk.Toplevel(root)
    bill_window.title("Invoice")

    bill_frame = tk.Frame(bill_window, bg="white", bd=2, relief="solid")
    bill_frame.pack(padx=10, pady=10)

    bill_text = tk.Text(
        bill_frame,
        width=60,
        height=25,
        font=("Courier New", 11),
        bg="white",
        bd=0
    )
    bill_text.pack()

    bill_text.insert(tk.END, "      SALONI INTERIORS\n")
    bill_text.insert(tk.END, "   Interior & Decor Solutions\n")
    bill_text.insert(tk.END, "-"*50 + "\n")

    bill_text.insert(tk.END, f"Invoice No : {invoice_no}\n")
    bill_text.insert(tk.END, f"Date       : {date}\n")
    bill_text.insert(tk.END, f"Customer   : {customer}\n")
    bill_text.insert(tk.END, f"Phone      : {phone}\n")

    bill_text.insert(tk.END, "-"*50 + "\n")
    bill_text.insert(tk.END, f"{'Item':15}{'Qty':5}{'Price':10}{'Total':10}\n")
    bill_text.insert(tk.END, "-"*50 + "\n")

    for _, name, price, qty, total in invoice_data:
        bill_text.insert(tk.END, f"{name[:15]:15}{qty:<5}{price:<10}{total:<10}\n")

    bill_text.insert(tk.END, "-"*50 + "\n")
    bill_text.insert(tk.END, f"Subtotal       : Rs.{subtotal}\n")

    if dtype == "%":
        discount_text = f"{discount_value}%"
    else:
        discount_text = f"Rs.{discount_value}"

    bill_text.insert(tk.END, f"Discount ({discount_text}) : -Rs.{discount_amount}\n")
    bill_text.insert(tk.END, f"After Discount : Rs.{after_discount}\n")
    bill_text.insert(tk.END, f"GST (18%)      : Rs.{gst}\n")
    bill_text.insert(tk.END, "-"*50 + "\n")
    bill_text.insert(tk.END, f"Grand Total    : Rs.{grand_total}\n")
    bill_text.insert(tk.END, "-"*50 + "\n")

    bill_text.insert(tk.END, "   Thank You! Visit Again 🙏\n")

    bill_text.config(state="disabled")
    
    log_action("Generated Bill", customer)
    
    def save_pdf():
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        
        pdf = FPDF()
        pdf.add_page()
        

        try:
            logo_path = resource_path("logo.PNG")

            if os.path.exists(logo_path):
                pdf.image(logo_path, x=10, y=8, w=30)
            else:
                print("Logo not found:", logo_path)
        except:
            pass

        
        pdf.ln(20)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Invoice", ln=True, align="C")

        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Invoice No: {invoice_no}", ln=True)
        pdf.cell(0, 10, f"Date: {date}", ln=True)
        pdf.cell(0, 10, f"Customer: {customer}", ln=True)
        pdf.cell(0, 10, f"Phone: {phone}", ln=True)
        pdf.ln(5)

        for _, name, price, qty, total in invoice_data:
            pdf.cell(0, 8, f"{name} | Rs.{price} x {qty} | Rs.{total}", ln=True)

        pdf.ln(5)
        pdf.cell(0, 10, f"Subtotal: {subtotal}", ln=True)
        if dtype == "%":
            discount_text = f"{discount_value}%"
        else:
            discount_text = f"Rs.{discount_value}"

        pdf.cell(0, 10, f"Discount ({discount_text}): -{discount_amount}", ln=True)
        pdf.cell(0, 10, f"After Discount: {after_discount}", ln=True)
        pdf.cell(0, 10, f"GST: {gst}", ln=True)
        pdf.cell(0, 10, f"Grand Total: Rs.{grand_total}", ln=True)
        pdf.cell(0, 10, "Saloni Interiors", ln=True, align="C")
        pdf.cell(0, 10, "Thank you for visiting!", ln=True, align="C")

        pdf.output(f"{invoice_no}.pdf")

        
        for pid, item in cart.items():
            qty = item["qty"]

            cursor.execute("SELECT quantity FROM products WHERE id=?", (pid,))
            stock = cursor.fetchone()[0]

            new_qty = stock - qty
            cursor.execute("UPDATE products SET quantity=? WHERE id=?", (new_qty, pid))

        for _, name, price, qty, total in invoice_data:
            cursor.execute("""
                INSERT INTO sales(product, quantity, price, total, customer, date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                qty,
                price,
                total,
                customer,
                datetime.datetime.now().strftime("%Y-%m-%d")
            ))
        conn.commit()
        conn.close()

        messagebox.showinfo("Saved", "Invoice saved as PDF!")
        bill_window.destroy()
        view_products()
        cart.clear()

        clear_fields()
        entry_customer.delete(0, tk.END)
        entry_phone.delete(0, tk.END)

    
    tk.Button(bill_window, text="Save as PDF", bg="green", fg="white", command=save_pdf).pack(pady=5)    
                      

def generate_invoice_no():
    now = datetime.datetime.now().strftime("%Y%m%d%H%M")
    return f"INV{now}"

def add_to_cart():
    global cart

    selected_items = tree.selection()

    if not selected_items:
        messagebox.showerror("Error", "Select a product!")
        return

    try:
        qty = int(entry_sale.get())
        if qty <= 0:
            raise ValueError
    except:
        messagebox.showerror("Error", "Enter valid quantity!")
        return
    
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    for item in selected_items:
        pid = int(item)

        cursor.execute("SELECT quantity, name FROM products WHERE id=?", (pid,))
        result = cursor.fetchone()

        if not result:
            continue
        stock_qty, name = result
       

        if qty > stock_qty:
            messagebox.showerror("Error", f"Not enough stock for {name}")
            
            continue

        if pid in cart:
            cart[pid]["qty"] += qty
        else:
            cursor.execute("SELECT price FROM products WHERE id=?", (pid,))
            price = cursor.fetchone()[0]

            cart[pid] = {
                "qty": qty,
                "price": price
            }

    conn.close()

    messagebox.showinfo("Cart", "Items added to cart!")
    entry_sale.delete(0, tk.END)




def view_cart():
    global cart
     
    if not cart:
        messagebox.showinfo("Cart", "Cart is empty!")
        return

    cart_win = tk.Toplevel(root)
    cart_win.title("Cart Manager")

    tree_cart = ttk.Treeview(cart_win, columns=("Name", "Price", "Qty", "Total"), show="headings")
    tree_cart.heading("Name", text="Name")
    tree_cart.heading("Price", text="Price")
    tree_cart.heading("Qty", text="Qty")
    tree_cart.heading("Total", text="Total")
    tree_cart.pack(fill="both", expand=True)

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    for pid, item in cart.items():
        qty = item["qty"]
        price = item["price"]
        cursor.execute("SELECT name FROM products WHERE id=?", (pid,))
        result = cursor.fetchone()

        if not result:
            continue


        name = result[0]
        total = price * qty
        
        tree_cart.insert("", "end", iid=pid, values=(name, price, qty, total))

    conn.close()


    def remove_item():
        selected = tree_cart.focus()
        if not selected:
            return
        del cart[int(selected)]
        tree_cart.delete(selected)

    def update_item():
        selected = tree_cart.focus()
        if not selected:
            return
        try:
            new_qty = int(entry_new_qty.get())
            if new_qty <= 0:
                raise ValueError
            
        except:
            messagebox.showerror("Error", "Enter valid quantity!")
            return
        pid = int(selected)

        cart[pid]["qty"] = new_qty
        
        messagebox.showinfo("Updates", "Cart updated!")
        
        cart_win.destroy()
        view_cart()
        
    entry_new_qty = tk.Entry(cart_win)
    entry_new_qty.pack(pady=5)
    entry_new_qty.insert(0, "Entry Qty")
    clear_fields()

    tk.Button(cart_win, text="Update Quantity", command=update_item).pack(pady=5)
    tk.Button(cart_win, text="Remove Item", command=remove_item).pack(pady=5)

def open_billing():
    billing_frame.pack(padx=20, pady=10, fill="x")
    generate_bill()

def sales_graph():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, SUM(total)
        FROM sales
        GROUP BY date
        ORDER BY date
    """)

    data = cursor.fetchall()
    conn.close()

    if not data:
        messagebox.showinfo("Info", "No sales data!")
        return

    dates = [row[0] for row in data]
    totals = [row[1] for row in data]

    plt.figure()
    plt.plot(dates, totals, marker='o')
    plt.title("Sales Trend")
    plt.xlabel("Date")
    plt.ylabel("Sales (Rs)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def top_products():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product, SUM(quantity) as qty
        FROM sales
        GROUP BY product
        ORDER BY qty DESC
        LIMIT 5
    """)

    rows = cursor.fetchall()
    conn.close()

    win = tk.Toplevel(root)
    win.title("Top Products")

    text = tk.Text(win, width=50, height=20)
    text.pack()

    text.insert(tk.END, "🏆 Top Selling Products\n\n")

    for i, row in enumerate(rows, start=1):
        text.insert(tk.END, f"{i}. {row[0]} → {row[1]} sold\n")

    text.config(state="disabled")

def top_customers():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT customer, SUM(total) as spend
        FROM sales
        GROUP BY customer
        ORDER BY spend DESC
        LIMIT 5
    """)

    rows = cursor.fetchall()
    conn.close()

    win = tk.Toplevel(root)
    win.title("Top Customers")

    text = tk.Text(win, width=50, height=20)
    text.pack()

    text.insert(tk.END, "👤 Top Customers\n\n")

    for i, row in enumerate(rows, start=1):
        text.insert(tk.END, f"{i}. {row[0]} → Rs.{row[1]}\n")

    text.config(state="disabled")

def custom_report():
    win = tk.Toplevel(root)
    win.title("Custom Report")

    tk.Label(win, text="Start Date (YYYY-MM-DD)").pack()
    entry_start = tk.Entry(win)
    entry_start.pack()

    tk.Label(win, text="End Date (YYYY-MM-DD)").pack()
    entry_end = tk.Entry(win)
    entry_end.pack()

    def generate():
        start = entry_start.get()
        end = entry_end.get()

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT product, SUM(quantity), SUM(total)
            FROM sales
            WHERE date BETWEEN ? AND ?
            GROUP BY product
        """, (start, end))

        rows = cursor.fetchall()

        cursor.execute("""
            SELECT SUM(total) FROM sales
            WHERE date BETWEEN ? AND ?
        """, (start, end))

        total = cursor.fetchone()[0] or 0
        conn.close()

        result = tk.Toplevel(win)
        result.title("Custom Report")

        text = tk.Text(result, width=60, height=25)
        text.pack()

        text.insert(tk.END, f"Report ({start} to {end})\n")
        text.insert(tk.END, "-"*50 + "\n")

        for row in rows:
            text.insert(tk.END, f"{row[0]} | Qty:{row[1]} | Rs.{row[2]}\n")

        text.insert(tk.END, "-"*50 + "\n")
        text.insert(tk.END, f"Total: Rs.{total}")

        text.config(state="disabled")

    tk.Button(win, text="Generate", command=generate).pack(pady=10)


def daily_report():
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product, SUM(quantity), SUM(total)
        FROM sales
        WHERE date=?
        GROUP BY product
    """, (today,))

    rows = cursor.fetchall()

    cursor.execute("""
        SELECT SUM(total) FROM sales WHERE date=?
    """, (today,))
    total_sales = cursor.fetchone()[0] or 0

    conn.close()

    report_win = tk.Toplevel(root)
    report_win.title("Daily Sales Report")

    text = tk.Text(report_win, width=60, height=25)
    text.pack()

    text.insert(tk.END, f"📅 Daily Report ({today})\n")
    text.insert(tk.END, "-"*50 + "\n")

    for row in rows:
        text.insert(tk.END, f"{row[0]} | Qty: {row[1]} | Sales: Rs.{row[2]}\n")

    text.insert(tk.END, "-"*50 + "\n")
    text.insert(tk.END, f"Total Sales: Rs.{total_sales}")

    text.config(state="disabled")

    

def monthly_report():
    month = datetime.datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product, SUM(quantity), SUM(total)
        FROM sales
        WHERE date LIKE ?
        GROUP BY product
    """, (month + "%",))

    rows = cursor.fetchall()

    cursor.execute("""
        SELECT SUM(total) FROM sales WHERE date LIKE ?
    """, (month + "%",))
    total_sales = cursor.fetchone()[0] or 0

    conn.close()

    report_win = tk.Toplevel(root)
    report_win.title("Monthly Sales Report")

    text = tk.Text(report_win, width=60, height=25)
    text.pack()

    text.insert(tk.END, f"📅 Monthly Report ({month})\n")
    text.insert(tk.END, "-"*50 + "\n")

    for row in rows:
        text.insert(tk.END, f"{row[0]} | Qty: {row[1]} | Sales: Rs.{row[2]}\n")

    text.insert(tk.END, "-"*50 + "\n")
    text.insert(tk.END, f"Total Sales: Rs.{total_sales}")

    text.config(state="disabled")


def backup_database():
    file = filedialog.asksaveasfilename(
        defaultextension=".db",
        filetypes=[("Database Files", "*.db")]
    )

    if not file:
        return

    try:
        shutil.copy("inventory.db", file)
        messagebox.showinfo("Success", "Backup created successfully!")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def restore_database():
    file = filedialog.askopenfilename(
        filetypes=[("Database Files", "*.db")]
    )

    if not file:
        return

    confirm = messagebox.askyesno(
        "Warning",
        "This will overwrite current database. Continue?"
    )

    if not confirm:
        return

    try:
        shutil.copy(file, "inventory.db")
        messagebox.showinfo("Success", "Database restored! Restart app.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

##Button Frame


def load_icon(path, size=(20, 20)):
    try:
        
        img = Image.open(resource_path(path))
        img = img.resize(size)
        return ImageTk.PhotoImage(img)
    except:
        return None

icon_add = load_icon("assets/add.png")
icon_view = load_icon("assets/view.png")
icon_update = load_icon("assets/update.png")
icon_delete = load_icon("assets/delete.png")
icon_sale = load_icon("assets/sale.png")
icon_add_to_cart = load_icon("assets/add_to_cart.png")
icon_bill = load_icon("assets/bill.png")
icon_search = load_icon("assets/search.png")
icon_view_cart = load_icon("assets/view_cart.png")
    
def create_sidebar_button(parent, text, command, icon):
    btn = tk.Button(
        parent,
        text="  " + text,
        image=icon,
        compound="left",
        bg="#2C3E50",
        fg="white",
        font=("Segoe UI", 10),
        bd=0,
        padx=20,
        pady=12,
        anchor="w",
        command=command,
        cursor="hand2",
        activebackground="#1ABC9C",
        relief="flat"
    )
    def on_enter(e):
        btn.config(bg="#1ABC9C")

    def on_leave(e):
        btn.config(bg="#2C3E50")

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)

    btn.image = icon
    return btn
create_sidebar_button(sidebar, "Add Product", add_product, icon_add).pack(fill="x")
create_sidebar_button(sidebar, "View Products", view_products, icon_view).pack(fill="x")
create_sidebar_button(sidebar, "Delete Product", delete_product, icon_delete).pack(fill="x")
create_sidebar_button(sidebar, "Record Sale", record_sale, icon_sale).pack(fill="x")
create_sidebar_button(sidebar, "Update Product", update_product, icon_update).pack(fill="x")
create_sidebar_button(sidebar, "Search", search_product, icon_search).pack(fill="x")
create_sidebar_button(sidebar, "Add to Cart", add_to_cart, icon_add_to_cart).pack(fill="x")
create_sidebar_button(sidebar, "View Cart", view_cart, icon_view_cart).pack(fill="x")
create_sidebar_button(sidebar, "Generate Bill", open_billing, icon_bill).pack(fill="x")
create_sidebar_button(sidebar, "Add Staff", open_register, icon_add).pack(fill="x")
create_sidebar_button(sidebar, "View Logs", view_logs, icon_view).pack(fill="x")
create_sidebar_button(sidebar, "Sales Graph", sales_graph, icon_view).pack(fill="x")
create_sidebar_button(sidebar, "Top Products", top_products, icon_view).pack(fill="x")
create_sidebar_button(sidebar, "Top Customers", top_customers, icon_view).pack(fill="x")
create_sidebar_button(sidebar, "Custom Report", custom_report, icon_view).pack(fill="x")    
create_sidebar_button(sidebar, "Daily Report", daily_report, icon_view).pack(fill="x")
create_sidebar_button(sidebar, "Monthly Report", monthly_report, icon_view).pack(fill="x")         
create_sidebar_button(sidebar, "Backup Data", backup_database, icon_view).pack(fill="x")
create_sidebar_button(sidebar, "Restore Data", restore_database, icon_view).pack(fill="x")


root.withdraw()
login_screen()
root.mainloop()
