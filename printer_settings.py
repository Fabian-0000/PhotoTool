import tkinter as tk
from tkinter import ttk, messagebox
import win32print
import json

class PrinterSettings:
    def __init__(self, master):
        self.root = tk.Toplevel(master)
        self.root.geometry(f"{400}x{400}")
        self.root.minsize(100, 100)
        self.root.title("Printer Settings")
        self.root.focus_set()
        self.selected = None

        self.tree_frame = tk.Frame(self.root)
        self.tree_frame.pack_propagate(False)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(self.tree_frame, show="tree", selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))

        self.btn_ok = ttk.Button(self.button_frame, text="Ok", default="active", command=lambda: self.select_printer())
        self.btn_ok.pack(side=tk.RIGHT, padx=0, pady=0)
        self.btn_cancel = ttk.Button(self.button_frame, text="Cancel", command=lambda: self.root.destroy())
        self.btn_cancel.pack(side=tk.RIGHT, padx=(0, 5), pady=0)

        self.populate_listbox()

        self.root.bind("<Return>", lambda e: self.select_printer())
        
    @staticmethod
    def get_printers():
        # Returns a list of printer names
        return [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]

    def populate_listbox(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        printers = PrinterSettings.get_printers()
        
        # Add printers
        for p in printers:
            self.tree.insert("", "end", text=p)  # text is what shows in treeview

        data = None
        
        # Open the JSON file
        try:
            with open('settings.json', 'r') as file:
                data = json.load(file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open settings.json: {e}")
            self.root.destroy()
            return
        
        printer = data['printer']

        for item in self.tree.get_children():
            if self.tree.item(item, "text") == printer:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
                break

    def select_printer(self):
        selected = self.tree.selection()
        if selected:
            printer_name = self.tree.item(selected[0], "text")
            # Open the JSON file
            data = None
            try:
                with open('settings.json', 'r') as file:
                    data = json.load(file)
            
                data['printer'] = self.tree.item(selected[0], "text")

                with open("settings.json", "w") as file:
                    json.dump(data, file, indent=4)

            except Exception as e:
                messagebox.showerror("Error", f"Failed to open settings.json: {e}")
            
            self.root.destroy()
            

def pop_up(master):
    selector = PrinterSettings(master)
    master.wait_window(selector.root)
    return selector.selected