import subprocess

CREATE_NO_WINDOW = 0x08000000

_original_popen = subprocess.Popen

def hidden_popen(*args, **kwargs):
    kwargs["creationflags"] = CREATE_NO_WINDOW
    return _original_popen(*args, **kwargs)

subprocess.Popen = hidden_popen

import os
import tkinter as tk
from tkinter import messagebox, ttk
from pynput import keyboard
from pdf2image import convert_from_path
from PIL import ImageTk
import PIL
import time
from ctypes import windll
import json
import subprocess

import parser
import photo
import monitor_select
import printer_settings
import printer

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Clock():
    def __init__(self):
        self.restart()

    def elapsed_time(self):
        return time.time() - self.last_time
    
    def restart(self):
        self.last_time = time.time()

class WatchHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.clock = Clock()

    def on_any_event(self, event):
        # ignore rapid duplicate events
        if self.clock.elapsed_time() < 0.3:
            return

        self.clock.restart()
        
        # Schedule UI update safely
        self.app.master.after(100, self.app.load_files)

class AutoScrollbar(tk.Scrollbar):
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.pack_forget()   # hide
        else:
            self.pack(side=tk.RIGHT, fill=tk.Y)  # show
        super().set(lo, hi)

class MainApp:
    def __init__(self, master):
        self.master = master

        master.title("Photo Tool")
        master.geometry(f"{1600}x{900}")
        master.minsize(300, 200)

        self.menu_bar = tk.Menu(master)
        master.config(menu=self.menu_bar)

        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(
            label="Photo & Print", 
            command=self.photo_print,
            accelerator="F1"
        )
        file_menu.add_command(
            label="Photo", 
            command=self.photo_only,
            accelerator="F2"
        )
        file_menu.add_command(
            label="Print", 
            command=self.print_only,
            accelerator="F3"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=master.destroy)

        self.menu_bar.add_cascade(label=" File ", menu=file_menu)

        self.fit_mode = "width"  # "fit", "width", "height", "manual"
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        view_menu.add_command(
            label="Fit Width", 
            command=lambda: (setattr(self, "fit_mode", "width"), self.resize_image(None)), 
            accelerator="Ctrl+W"
        )
        view_menu.add_command(
            label="Fit Height", 
            command=lambda: (setattr(self, "fit_mode", "height"), self.resize_image(None)),
            accelerator="Ctrl+H"
        )
        view_menu.add_command(
            label="Fit Everything", 
            command=lambda: (setattr(self, "fit_mode", "fit"), self.resize_image(None)),
            accelerator="Ctrl+F"
        )
        self.menu_bar.add_cascade(label=" View ", menu=view_menu)

        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        settings_menu.add_command(
            label="Select Monitor...", 
            command=lambda: self.select_monitor(), 
        )
        settings_menu.add_command(
            label="Printer Settings...", 
            command=lambda: printer_settings.pop_up(master)
        )
        self.menu_bar.add_cascade(label=" Settings ", menu=settings_menu)
        
        self.menu_bar.add_cascade(label=" Exit ", command=master.destroy)

        self.paned = tk.PanedWindow(master, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left Frame for listbox
        self.frame_left = tk.Frame(self.paned, width=400)
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0), pady=5)

        # --- Treeview (replaces Listbox) ---
        self.tree_frame = tk.Frame(self.frame_left, width=400)
        self.tree_frame.pack_propagate(False)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=(5,0), pady=5)

        self.scrollbar = AutoScrollbar(self.tree_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_files = ttk.Treeview(
            self.tree_frame,
            show="tree",           # only show file names (no columns)
            selectmode="browse",   # single selection
            yscrollcommand=self.scrollbar.set
        )
        self.tree_files.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar.config(command=self.tree_files.yview)

        # Remove indentation / extra padding
        self.tree_files.column("#0", anchor="w", stretch=True)
        self.tree_files.heading("#0", text="")

        # Key trick: reduce internal padding via style
        style = ttk.Style()
        style.layout("Treeview.Item", [
            ('Treeitem.padding', {'sticky': 'nswe', 'children': [
                ('Treeitem.image', {'side': 'left', 'sticky': ''}),
                ('Treeitem.text', {'side': 'left', 'sticky': ''}),
            ]})
        ])
        style.configure("Treeview", rowheight=28)

        # Bind selection
        self.tree_files.bind("<<TreeviewSelect>>", self.preview_pdf)

        # --- Buttons under the list ---
        self.frame_buttons = tk.Frame(self.frame_left)
        self.frame_buttons.pack(side=tk.BOTTOM, fill=tk.X, padx=(5, 0), pady=5)

        self.btn_photoprint = ttk.Button(self.frame_buttons, text="Photo & Print [F1]", command=self.photo_print)
        self.btn_photo = ttk.Button(self.frame_buttons, text="Photo [F2]", command=self.photo_only)
        self.btn_print = ttk.Button(self.frame_buttons, text="Print [F3]", command=self.print_only)

        self.btn_photoprint.pack(fill=tk.X, pady=(0, 5))
        self.btn_photo.pack(fill=tk.X, pady=(0, 5))
        self.btn_print.pack(fill=tk.X, pady=0)

        self.load_files()

        # Right Frame for preview and buttons
        self.frame_right = tk.Frame(self.paned)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)
        self.frame_right.bind('<Configure>', self.resize_image)

        self.canvas = tk.Canvas(self.frame_right, bg=self.frame_right.cget("bg"), highlightthickness=1, highlightbackground="gray")
        self.canvas.pack(fill=tk.BOTH, side=tk.TOP, expand=True, padx=(0, 5), pady=5)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-1>", self.on_pan_start)
        self.canvas.bind("<B1-Motion>", self.on_pan_move)
        self.image_id = None
        self.canvas_img = None

        self.zoom = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        self.offset_x = 0
        self.offset_y = 0

        self.pan_start = None

        self.master.bind("<Control-f>", lambda e: self.fit_to_screen())
        self.master.bind("<Control-w>", lambda e: self.fit_to_width())
        self.master.bind("<Control-h>", lambda e: self.fit_to_height())

        self.paned.add(self.frame_left, minsize=200)   # minimum width
        self.paned.add(self.frame_right, minsize=200)

        self.paned.configure(sashwidth=10)

        self.selected_rect = [0, 0, 0, 0]
        try:
            with open('settings.json', 'r') as file:
                data = json.load(file)
        
            self.selected_rect = monitor_select.get_rect(data['monitor'])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open settings.json: {e}")
            self.selected_rect = monitor_select.get_rect(0)

        self.pdf_image = None
        self.pdf_image_size = 297*3, 210*3

        self.photo_clock = Clock()

    def __del__(self):
        self.stop_watcher()

    def load_pdf(self):
        selected = self.tree_files.selection()
        if not selected:
            return

        file_name = self.tree_files.item(selected[0], "text")
        file_path = os.path.join('out/', file_name)

        try:
            pages = convert_from_path(file_path, first_page=1, last_page=1, size=(297*10, 210*10))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF: {e}")

        pdf_image = pages[0]
        self.pdf_image = pdf_image

        self.resize_image()

        self.render_pdf()

    def render_pdf(self):
        if self.pdf_image is None:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        img = self.pdf_image.copy()

        # Apply zoom
        w, h = img.size
        new_size = (int(w * self.zoom), int(h * self.zoom))
        img = img.resize(new_size)

        self.canvas_img = ImageTk.PhotoImage(img)

        self.canvas.delete("all")

        self.image_id = self.canvas.create_image(
            canvas_w // 2 + self.offset_x,
            canvas_h // 2 + self.offset_y,
            image=self.canvas_img,
            anchor="center"
        )

    # Function to list PDF files in a selected directory
    def load_files(self):
        self.tree_files.unbind("<<TreeviewSelect>>")

        selected = self.tree_files.selection()
        last_selected = ""

        if selected:
            last_selected = self.tree_files.item(selected[0], "text")

        self.tree_files.delete(*self.tree_files.get_children())

        for file in os.listdir('out/'):
            if file.lower().endswith('.pdf'):
                self.tree_files.insert("", "end", text=file)

        for item in self.tree_files.get_children():
            if self.tree_files.item(item, "text") == last_selected:
                self.tree_files.selection_set(item)
                self.tree_files.focus(item)
                break
        else:
            if hasattr(self, "canvas"):
                self.canvas.delete("all")

        self.tree_files.bind("<<TreeviewSelect>>", self.preview_pdf)

    # Function to preview selected PDF
    def preview_pdf(self, event = None):
        selected = self.tree_files.selection()
        if not selected:
            return

        file_name = self.tree_files.item(selected[0], "text")

        if getattr(self, "_last_previewed", None) == file_name:
            return

        self._last_previewed = file_name

        print('start')
        self.load_pdf()
        print('end')

    def select_monitor(self):
        self.selected_rect = monitor_select.select_monitor(self.master)

    # Button actions
    def photo_print(self):
        self.photo_only()
        self.print_only()

    def photo_after(self):
        self.load_files()

        children = self.tree_files.get_children()
        if children:
            self.tree_files.selection_set(children[-1])
            self.tree_files.focus(children[-1])

    def photo_intern(self):
        rect = parser.extract_black_rectangle_rect("frame.pdf")
        screen_shot = photo.screen_shot(self.selected_rect)

        output_filename = time.strftime("%d-%m-%Y_%H-%M-%S") + '.pdf'

        photo.merge(rect, screen_shot, 'frame.pdf', os.path.join('out/', output_filename))

        self.master.after(0, self.photo_after)

    def photo_only(self):
        import threading
        threading.Thread(target=self.photo_intern).start()

    def print_only(self):
        selected = self.tree_files.selection()
        if not selected:
            messagebox.showerror("Error", f"No File is selected.")
            return

        file_name = self.tree_files.item(selected[0], "text")
        file_path = os.path.join('out/', file_name)

        printer.print_doc(file_path)

    def resize_image(self, event = None):
        if self.pdf_image is None:
            return

        if self.fit_mode == "fit":
            self.fit_to_screen()
        elif self.fit_mode == "width":
            self.fit_to_width()
        elif self.fit_mode == "height":
            self.fit_to_height()
        
        return

    def on_mouse_wheel(self, event):
        if self.pdf_image is None:
            return

        factor = 1.1 if event.delta > 0 else 0.9
        new_zoom = self.zoom * factor

        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.zoom = new_zoom
            self.fit_mode = "manual"
            self.render_pdf()

    def on_pan_start(self, event):
        self.fit_mode = "manual"
        self.pan_start = (event.x, event.y)

    def on_pan_move(self, event):
        if not self.pan_start:
            return

        dx = event.x - self.pan_start[0]
        dy = event.y - self.pan_start[1]

        self.offset_x += dx
        self.offset_y += dy

        self.pan_start = (event.x, event.y)

        self.render_pdf()

    def fit_to_screen(self):
        if self.pdf_image is None:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        img_w, img_h = self.pdf_image.size

        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h

        self.zoom = min(scale_w, scale_h)
        self.offset_x = 0
        self.offset_y = 0
        self.fit_mode = "fit"

        self.render_pdf()

    def fit_to_width(self):
        canvas_w = self.canvas.winfo_width()
        img_w, _ = self.pdf_image.size

        self.zoom = canvas_w / img_w
        self.offset_x = 0
        self.offset_y = 0
        self.fit_mode = "width"

        self.render_pdf()

    def fit_to_height(self):
        canvas_h = self.canvas.winfo_height()
        _, img_h = self.pdf_image.size

        self.zoom = canvas_h / img_h
        self.offset_x = 0
        self.offset_y = 0
        self.fit_mode = "height"

        self.render_pdf()

    def on_press(self, key):
        if self.photo_clock.elapsed_time() < 0.5:
            return
        
        self.photo_clock.restart()

        # schedule update on main thread
        if key == keyboard.Key.f1:
            self.master.after(0, self.photo_print)
        elif key == keyboard.Key.f2:
            self.master.after(0, self.photo_only)
        elif key == keyboard.Key.f3:
            self.master.after(0, self.print_only)

    def start_watcher(self):
        self.observer = Observer()
        handler = WatchHandler(self)
        self.observer.schedule(handler, path="out/", recursive=False)
        self.observer.start()

    def stop_watcher(self):
        if hasattr(self, "observer"):
            self.observer.stop()
            self.observer.join()

def apply_dark_theme(root):
    from tkinter import ttk

    style = ttk.Style()
    style.theme_use("clam")

def mainloop():
    root = tk.Tk()

    apply_dark_theme(root)

    app = MainApp(root)

    listener = keyboard.Listener(on_press=app.on_press)
    listener.start()

    app.start_watcher()

    root.mainloop()

    listener.stop()