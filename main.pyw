import ui
import ctypes

if __name__ == "__main__":
    #disable app scaling
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()

    ui.mainloop()