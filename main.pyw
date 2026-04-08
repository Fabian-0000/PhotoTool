import ui
from ctypes import windll

if __name__ == "__main__":
    #disable app scaling
    user32 = windll.user32
    user32.SetProcessDPIAware()

    ui.mainloop()