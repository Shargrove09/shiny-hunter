from tkinter import ttk


def shiny_style():
    style = ttk.Style()
    style.configure('standard.TButton', font=(
        'calibri', 14, 'bold'))

    style.configure('dropdown.TCombobox', font=('calibri', 144))

    style.configure('select.TLabel', font=('calibri', 14))
