import tkinter as tk
from tkinter import ttk, messagebox
from screeninfo import get_monitors
from screeninfo import Monitor
import ctypes
from PIL import ImageGrab, Image, ImageTk
import json

class MonitorSelector:
    def __init__(self, master):
        self.root = tk.Toplevel(master)
        self.root.title("Select Monitor")
        self.selected = None

        self.root.resizable(False, False)

        self.monitors = get_monitors()

        # Scale down for preview
        self.scale = 0.2

        self.images = []

        for i, m in enumerate(self.monitors):
            h = 250
            w = int(h / float(m.height) * m.width)

            # Capture screenshot of monitor
            try:
                img = ImageGrab.grab(bbox=(m.x, m.y, m.x + m.width, m.y + m.height))
                img = img.resize((w, h))
                tk_img = ImageTk.PhotoImage(img)
                self.images.append(tk_img)

                name = f"[{i+1}] {m.name}: {m.width}x{m.height}"

                button = ttk.Button(self.root, compound="top", text=name, image=tk_img, command=lambda: self.select(i))
                row = i // 3
                col = i % 3
                button.grid(row=row, column=col, padx=5, pady=5)

            except Exception:
                pass

    def select(self, idx):
        m = self.monitors[idx]
        self.selected = (m.x, m.y, m.width, m.height)

        data = None
        try:
            with open('settings.json', 'r') as file:
                data = json.load(file)
        
            data['monitor'] = idx
            with open("settings.json", "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open settings.json: {e}")
        
        self.root.destroy()

def select_monitor(master):
    selector = MonitorSelector(master)
    master.wait_window(selector.root)
    return selector.selected

def get_rect(index: int):
    monitors = get_monitors()

    try:
        m = monitors[index]
        return (m.x, m.y, m.width, m.height)

    except:
        m = monitors[0]
        return (m.x, m.y, m.width, m.height)