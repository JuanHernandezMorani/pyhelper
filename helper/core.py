import ast
import asyncio
import csv
import inspect
import json
import math
import os
import re
import struct
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sqlalchemy as sa
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PyPDF2 import PdfReader
from scipy.stats import kurtosis, norm, skew
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sqlalchemy import Column, MetaData, Table, create_engine, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import xml.etree.ElementTree as ET
import geopandas as gpd
import warnings

try:
    from IPython.display import Markdown, display
except ImportError:
    display = None
    Markdown = None

from .submodules.pyswitch import Switch, switch

def is_jupyter_notebook():
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is None:
            return False

        shell_name = ip.__class__.__name__
        if shell_name == "ZMQInteractiveShell":
            return True
        else:
            return False
    except ImportError:
        return False

IN_JUPYTER = is_jupyter_notebook()

CONFIG_LANG = "en"
NORMAL_SIZE = (10, 6)
BIG_SIZE = (12, 8)
BG_COLOR = "#2d2d2d"
TEXT_COLOR = "#ffffff"
BTN_BG = "#3d3d3d"
HIGHLIGHT_COLOR = "#4e7cad"

config = {"verbose": True, "default_timeout": 5, "counter": 0}

def load_gui_config():
    """Carga la configuración de la GUI desde un archivo JSON."""
    config_path = os.path.join(os.getcwd(), "gui_config.json")
    default_config = {
        "bg_color": "#2b2b2b",
        "text_color": "#ffffff",
        "btn_bg": "#3c3f41",
        "highlight_color": "#4e5254",
        "preview_bg": "#f0f0f0"
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                return {**default_config, **user_config}
    except:
        pass
    
    return default_config

def save_gui_config(config):
    """Guarda la configuración de la GUI en un archivo JSON."""
    config_path = os.path.join(os.getcwd(), "gui_config.json")
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error guardando configuración: {str(e)}")

def show_gui_popup(
    title, content, fig=None, plot_function=None, plot_args=None, 
    preview_mode=False, export_callback=None, table_data=None
):
    # Usar Switch para traducciones
    translations = {
        "copy": "copy",
        "close": "close", 
        "save": "save",
        "content": "content",
        "preview": "preview",
        "error_in_gui": "error_in_gui",
        "export": "export",
        "light_theme": "light_theme",
        "dark_theme": "dark_theme",
        "settings": "settings"
    }
    
    # Traducir usando Switch
    copy_text = Switch(translations["copy"])(
        lambda x: "copy", lambda: t("copy"),
        "default", lambda: "Copy"
    )
    
    close_text = Switch(translations["close"])(
        lambda x: "close", lambda: t("close"),
        "default", lambda: "Close"
    )
    
    save_text = Switch(translations["save"])(
        lambda x: "save", lambda: t("save"),
        "default", lambda: "Save"
    )
    
    content_text = Switch(translations["content"])(
        lambda x: "content", lambda: t("content"),
        "default", lambda: "Content"
    )
    
    preview_text = Switch(translations["preview"])(
        lambda x: "preview", lambda: t("preview"),
        "default", lambda: "Preview"
    )
    
    gui_error_text = Switch(translations["error_in_gui"])(
        lambda x: "error_in_gui", lambda: t("error_in_gui"),
        "default", lambda: "GUI Error"
    )
    
    export_text = Switch(translations["export"])(
        lambda x: "export", lambda: t("export"),
        "default", lambda: "Export"
    )
    
    light_theme_text = Switch(translations["light_theme"])(
        lambda x: "light_theme", lambda: t("light_theme"),
        "default", lambda: "Light Theme"
    )
    
    dark_theme_text = Switch(translations["dark_theme"])(
        lambda x: "dark_theme", lambda: t("dark_theme"),
        "default", lambda: "Dark Theme"
    )
    
    settings_text = Switch(translations["settings"])(
        lambda x: "settings", lambda: t("settings"),
        "default", lambda: "Settings"
    )

    # Cargar configuración de colores
    config = load_gui_config()
    BG_COLOR = config.get("bg_color", "#2b2b2b")
    TEXT_COLOR = config.get("text_color", "#ffffff")
    BTN_BG = config.get("btn_bg", "#3c3f41")
    HIGHLIGHT_COLOR = config.get("highlight_color", "#4e5254")
    PREVIEW_BG = config.get("preview_bg", "#f0f0f0")

    # Set matplotlib backend
    if IN_JUPYTER:
        mpl.use("module://ipykernel.pylab.backend_inline")
    else:
        mpl.use("Agg")

    current_fig = fig
    if plot_function is not None:
        if plot_args is None:
            plot_args = {}
        current_fig = plot_function(**plot_args)

    if preview_mode:
        if current_fig is not None:
            current_fig.patch.set_facecolor(PREVIEW_BG)
            for ax in current_fig.get_axes():
                ax.set_facecolor(PREVIEW_BG)
                ax.title.set_color(TEXT_COLOR)
                ax.xaxis.label.set_color(TEXT_COLOR)
                ax.yaxis.label.set_color(TEXT_COLOR)
                ax.tick_params(colors=TEXT_COLOR)
                for spine in ax.spines.values():
                    spine.set_color(TEXT_COLOR)
        return current_fig

    # Main window setup
    window = tk.Tk()
    window.title(title)
    window.geometry("1000x800")
    window.configure(bg=BG_COLOR)

    # Style configuration
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TFrame", background=BG_COLOR)
    style.configure(
        "Dark.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Consolas", 10)
    )
    style.configure(
        "Dark.TButton", background=BTN_BG, foreground=TEXT_COLOR, borderwidth=1
    )
    style.map("Dark.TButton", background=[("active", HIGHLIGHT_COLOR)])

    # Main container with proper weight distribution
    window.grid_rowconfigure(0, weight=1)
    window.grid_columnconfigure(0, weight=1)

    main_frame = ttk.Frame(window, style="Dark.TFrame")
    main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)

    # Notebook for tabs
    notebook = ttk.Notebook(main_frame)
    notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

    # Content tab
    doc_frame = ttk.Frame(notebook, style="Dark.TFrame")
    notebook.add(doc_frame, text=content_text)

    text_area = ScrolledText(
        doc_frame,
        wrap=tk.WORD,
        font=("Consolas", 10),
        bg=BG_COLOR,
        fg=TEXT_COLOR,
        insertbackground=TEXT_COLOR,
        selectbackground=HIGHLIGHT_COLOR,
    )
    text_area.pack(expand=True, fill="both", padx=5, pady=5)
    text_area.insert(tk.END, content)
    text_area.config(state="disabled")

    # Visualization handling
    current_fig = fig
    canvas = None

    if fig is not None or plot_function is not None:
        # Preview tab
        graph_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(graph_frame, text=preview_text)

        if plot_function is not None:
            if plot_args is None:
                plot_args = {}
            current_fig = plot_function(**plot_args)

        if current_fig is not None:
            current_fig.patch.set_facecolor(PREVIEW_BG)
            for ax in current_fig.get_axes():
                ax.set_facecolor(PREVIEW_BG)
                ax.title.set_color("black")
                ax.xaxis.label.set_color("black")
                ax.yaxis.label.set_color("black")
                ax.tick_params(colors="black")
                for spine in ax.spines.values():
                    spine.set_color("black")

            canvas = FigureCanvasTkAgg(current_fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Button functions
    def copy_to_clipboard():
        window.clipboard_clear()
        window.clipboard_append(content)
        window.update()

    def save_image():
        if current_fig is not None:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("All files", "*.*"),
                ],
            )
            if filepath:
                current_fig.savefig(filepath, bbox_inches="tight", dpi=300)

    def export_data():
        if export_callback:
            format_menu = tk.Menu(window, tearoff=0)
            formats = ["csv", "json", "excel", "xml", "sql", "parquet", "html"]
            
            for fmt in formats:
                format_menu.add_command(
                    label=fmt.upper(), 
                    command=lambda f=fmt: export_callback(f)
                )
            
            export_btn = btn_frame.winfo_children()[2]
            x = export_btn.winfo_rootx()
            y = export_btn.winfo_rooty() + export_btn.winfo_height()
            format_menu.post(x, y)

    def toggle_theme():
        nonlocal BG_COLOR, TEXT_COLOR, BTN_BG, HIGHLIGHT_COLOR, PREVIEW_BG
        
        theme_config = switch(
            BG_COLOR, {
                "#ffffff": {
                    "bg_color": "#2b2b2b",
                    "text_color": "#ffffff", 
                    "btn_bg": "#3c3f41",
                    "highlight_color": "#4e5254",
                    "preview_bg": "#f0f0f0"
                },
                "#2b2b2b": {
                    "bg_color": "#ffffff",
                    "text_color": "#000000",
                    "btn_bg": "#f0f0f0", 
                    "highlight_color": "#e0e0e0",
                    "preview_bg": "#f0f0f0"
                },
                "default": {
                "bg_color": "#2b2b2b",
                "text_color": "#ffffff",
                "btn_bg": "#3c3f41",
                "highlight_color": "#4e5254",
                "preview_bg": "#f0f0f0"
            }
            }
        )
        
        save_gui_config(theme_config)
        
        on_close()
        show_gui_popup(
            title, content, fig, plot_function, plot_args, 
            False, export_callback, table_data
        )

    def open_settings():
        settings_window = tk.Toplevel(window)
        settings_window.title("Configuración de GUI")
        settings_window.geometry("400x300")
        settings_window.configure(bg=BG_COLOR)
        
        ttk.Label(settings_window, text="Configuración de colores", style="Dark.TLabel").pack(pady=10)
        
        def save_custom_colors():
            pass
        
        ttk.Button(settings_window, text="Guardar", command=save_custom_colors, style="Dark.TButton").pack(pady=10)

    def on_close():
        if current_fig is not None:
            plt.close(current_fig)
        window.quit()
        window.destroy()

    # Button container
    btn_frame = ttk.Frame(main_frame, style="Dark.TFrame")
    btn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))

    btn_frame.grid_columnconfigure(0, weight=1)
    btn_frame.grid_columnconfigure(1, weight=1)
    btn_frame.grid_columnconfigure(2, weight=1)
    btn_frame.grid_columnconfigure(3, weight=1)
    btn_frame.grid_columnconfigure(4, weight=1)

    # Action button
    action_btn = ttk.Button(
        btn_frame, text=copy_text, command=copy_to_clipboard, style="Dark.TButton"
    )
    action_btn.grid(row=0, column=0, padx=5, sticky="w")

    # Export button
    if export_callback:
        export_btn = ttk.Button(
            btn_frame, text=export_text, command=export_data, style="Dark.TButton"
        )
        export_btn.grid(row=0, column=1, padx=5)

    # Theme toggle button
    theme_btn_text = switch(BG_COLOR,{
        "#ffffff": dark_theme_text,
        "#2b2b2b": light_theme_text,
        "default": light_theme_text}
    )
    
    theme_btn = ttk.Button(
        btn_frame, text=theme_btn_text, 
        command=toggle_theme, style="Dark.TButton"
    )
    theme_btn.grid(row=0, column=2, padx=5)

    # Settings button
    settings_btn = ttk.Button(
        btn_frame, text=settings_text, command=open_settings, style="Dark.TButton"
    )
    settings_btn.grid(row=0, column=3, padx=5)

    # Close button
    close_btn = ttk.Button(
        btn_frame, text=close_text, command=on_close, style="Dark.TButton"
    )
    close_btn.grid(row=0, column=4, padx=5, sticky="e")

    # Tab change handler
    def on_tab_change(event):
        tab_action = Switch(notebook.index("current"))(
            lambda x: 1, lambda: {"action_text": save_text, "action_command": save_image},
            "default", lambda: {"action_text": copy_text, "action_command": copy_to_clipboard}
        )
        action_btn.config(text=tab_action["action_text"], command=tab_action["action_command"])

    notebook.bind("<<NotebookTabChanged>>", on_tab_change)

    def _jup_func_():
        from IPython.display import display as ipy_display
        import ipywidgets as widgets

        output = widgets.Output(),
        ipy_display(output),

        def run_in_jupyter():
            with output:
                try:
                    window.mainloop()
                except Exception as e:
                    print(f"{gui_error_text}: {str(e)}")

        return window.after(100, run_in_jupyter)

    # Initial button state
    if fig is not None or plot_function is not None:
        if notebook.index("current") == 1:
            action_btn.config(text=save_text, command=save_image)

    # Jupyter Notebook specific handling
    if IN_JUPYTER:
         _jup_func_()
    else:
        window.mainloop()

    if current_fig is not None:
        plt.close(current_fig)

def get_translation_path(lang: str) -> Path:
    return Path(__file__).parent / "lang" / f"{lang}.json"

TRANSLATIONS_PATH = get_translation_path(CONFIG_LANG)
TRANSLATIONS = {}
_translations = {}

def t(key: str, lang: str = None) -> str:
    if not key:
        return t("missing_translation_key").format(key=key)

    lang = lang or CONFIG_LANG

    entry = _translations.get(key, {})
    return entry.get(lang, f"[{key}]")

def load_user_translations(lang_path: str = "lang.json"):
    global _translations

    user_translations = {}
    path = Path(lang_path)

    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_translations = json.load(f)
        except Exception as e:
            show_gui_popup(
                t("warning"), t("load_user_translations_error").format(error=str(e))
            )

    _translations = TRANSLATIONS.copy()
    _translations.update(user_translations)

if TRANSLATIONS_PATH.exists():
    with open(TRANSLATIONS_PATH, encoding="utf-8") as f:
        TRANSLATIONS = json.load(f)
        _translations = TRANSLATIONS.copy()
else:
    show_gui_popup(t("warning"), t("translations_not_found_warning"))

REGISTRY = {}

def register(name=None):
    """Decorator to register a function or class in the global REGISTRY."""
    def wrapper(fn):
        key = name or fn.__name__
        REGISTRY[key] = fn
        return fn
    return wrapper

def fig_to_img(fig):
    """Convierte una figura matplotlib a una imagen para mostrar en otro gráfico"""
    fig.canvas.draw()
    img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    return img

def generate_all_previews(preview_data):
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    import numpy as np

    preview_title = t("function_preview_title")
    preview_error = t("preview_error_message")

    # Filtrar solo las funciones que devuelven gráficos
    graph_previews = {}
    for func_name, data in preview_data.items():
        try:
            result = data["preview_func"]()
            if hasattr(result, "figure"):
                graph_previews[func_name] = data
        except:
            pass

    num_funcs = len(graph_previews)
    if num_funcs == 0:
        return None

    rows = (num_funcs + 1) // 2
    fig_height = rows * 6
    fig_width = 18
    fig = plt.figure(figsize=(fig_width, fig_height), tight_layout=True)
    gs = GridSpec(rows, 2, figure=fig)

    for idx, (func_name, data) in enumerate(graph_previews.items()):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])

        try:
            result = data["preview_func"]()
            if hasattr(result, "figure"):
                result.canvas.draw()
                img = np.frombuffer(result.canvas.tostring_rgb(), dtype=np.uint8)
                img = img.reshape(result.canvas.get_width_height()[::-1] + (3,))
                ax.imshow(img)
                ax.axis("off")
                plt.close(result.figure)
        except Exception as e:
            ax.text(
                0.5,
                0.5,
                preview_error.format(error=str(e)),
                ha="center",
                va="center",
                color="red",
            )
            ax.axis("off")

        ax.set_title(f"{func_name}", fontsize=12)

    return fig

def help(type: str = None):
    from .submodules import (
        hbar, vbar, pie, normalize, get_moda, get_media, get_median, boxplot,
        get_rank, get_var, get_desv, histo, disp, table, conditional, heatmap,
        call, Switch, scatter, lineplot, kdeplot, violinplot, pairplot,
        countplot, lmplot, jointplot, swarmplot, regplot, barplot, stripplot
    )

    # Translation strings usando Switch
    translations_map = {
        "preview_error": "preview_error",
        "error_in_gui": "error_in_gui", 
        "help_error": "help_error",
        "function_preview_title": "function_preview_title",
        "preview_error_message": "preview_error_message",
        "async_preview_not_available": "async_preview_not_available",
        "preview": "preview",
        "example": "example",
        "description": "description",
        "help_available_functions": "help_available_functions",
        "help_usage": "help_usage",
        "title_all": "title_all"
    }
    
    # Traducir todas las cadenas
    translated = {}
    for key, value in translations_map.items():
        translated[key] = Switch(value)(
            lambda x: value, lambda: t(value),
            "default", lambda: value.replace("_", " ").title()
        )

    help_map = {
        "get_moda": {
            translated["description"]: t("get_moda"),
            translated["example"]: "get_moda(np.array([1, 2, 2, 3, 3, 3]), with_repetition=True, decimals=2)",
            translated["preview"]: lambda: show_gui_popup(
                title="Moda",
                content=get_moda(np.array([1, 2, 2, 3, 3, 3]), with_repetition=True, decimals=2),
                preview_mode=True,
            ),
        },
        # ... (resto del help_map se mantiene igual por brevedad)
    }

    functions = sorted(help_map.keys())

    if type is None:
        if IN_JUPYTER:
            display(Markdown(f"**{translated['help_available_functions']}**"))
            for func in functions:
                display(Markdown(f"- `{func}`"))
            display(Markdown(f"\n*{translated['help_usage']}*"))
        else:
            func_list = "\n".join(f"- {func}" for func in functions)
            show_gui_popup(
                "Help", f"{translated['help_available_functions']}\n{func_list}\n\n{translated['help_usage']}"
            )
        return

    if not isinstance(type, str):
        msg = t("error_type")
        if IN_JUPYTER:
            display(Markdown(f"**Error:** {msg}"))
        else:
            show_gui_popup(title=translated["error_in_gui"], content=msg)
        return

    type = type.lower()

    if type == "all":
        full_doc = []
        preview_data = {}

        for func_name in functions:
            entry = help_map.get(func_name, {})
            doc = entry.get(translated["description"], "")
            example = entry.get(translated["example"], "")

            func_doc = f"{func_name.upper()}\n\n{doc}\n\nExample:\n{example}"
            full_doc.append(func_doc)

            if translated["preview"] in entry:
                preview_data[func_name] = {
                    translated["example"]: example,
                    "preview_func": entry[translated["preview"]],
                }

        full_doc_text = "\n\n" + ("=" * 50).join("\n\n") + "\n\n".join(full_doc) + "\n\n" + ("=" * 50)

        if IN_JUPYTER:
            display(Markdown(full_doc_text))
            for func_name, data in preview_data.items():
                display(Markdown(f"**Preview for {func_name}**"))
                try:
                    result = data["preview_func"]()
                    if hasattr(result, "figure"):
                        display(result.figure)
                        plt.close(result.figure)
                    else:
                        display(Markdown(f"```\n{str(result)}\n```"))
                except Exception as e:
                    display(Markdown(f"**Error in preview:**\n```\n{str(e)}\n```"))
        else:
            show_gui_popup(
                translated["title_all"],
                full_doc_text,
                plot_function=lambda: generate_all_previews(preview_data),
            )
        return

    if type in functions:
        doc = t(type)
        entry = help_map.get(type, {})
        example = entry.get(translated["example"], "")
        preview_func = entry.get(translated["preview"])

        if IN_JUPYTER:
            output = f"**{type.upper()}**\n```python\n{doc.strip()}\n```"
            if example:
                output += f"\n\n**{translated['example']}:**\n```python\n{example}\n```"
            display(Markdown(output))

            if preview_func:
                try:
                    print(f"\n**{translated['preview']}:**")
                    preview_func()
                except Exception as e:
                    display(Markdown(f"**{translated['preview_error']}:**\n```\n{str(e)}\n```"))
        else:
            full_text = doc.strip()
            if example:
                full_text += f"\n\n{translated['example']}:\n{example}"

            fig = None
            if preview_func:
                try:
                    result = preview_func()
                    if hasattr(result, "figure"):
                        fig = result.figure
                except Exception as e:
                    messagebox.showerror(f"{translated['preview_error']} {type}", str(e))

            show_gui_popup(type.upper(), full_text, fig=fig)
    else:
        error_msg = translated["help_error"].format(type)
        if IN_JUPYTER:
            display(Markdown(f"**{error_msg}**"))
        else:
            show_gui_popup(translated["error_in_gui"], error_msg)

def format_number(
    value: float, use_decimals: bool = True, decimals: int = 2, percent: bool = False
) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"

    if percent:
        value *= 100

    formatted = Switch(use_decimals)(
        lambda x: True, lambda: f"{value:,.{decimals}f}",
        lambda x: False, lambda: f"{int(round(value)):,}",
        "default", lambda: f"{value:,.{decimals}f}"
    )

    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    if percent:
        formatted += "%"

    return formatted

def set_language(lang: str):
    global CONFIG_LANG
    if lang not in next(iter(TRANSLATIONS.values())).keys():
        raise ValueError(f"Language '{lang}' is not available.")
    CONFIG_LANG = lang

__all__ = [
    # Módulos estándar
    "ast", "asyncio", "csv", "inspect", "json", "math", "os", "re", "struct", "sys", "time","warnings",
    
    # Tipos
    "Any", "Callable", "Dict", "List", "Optional", "Set", "Tuple", "Union",
    
    # Ciencia de datos
    "mpl", "np", "pd", "plt", "sns", "Path","gpd", "ET",
    
    # Scikit-learn y SciPy
    "kurtosis", "norm", "PCA", "skew", "StandardScaler",
    
    # SQLAlchemy
    "Column", "create_engine", "sessionmaker", "func", "MetaData", "sa", "select", "SQLAlchemyError", "Table", "text",
    
    # PDF y otros
    "PdfReader",
    
    # GUI
    "filedialog", "FigureCanvasTkAgg", "messagebox", "ScrolledText", "tk", "ttk",
    
    # Funciones propias
    "config", "fig_to_img", "format_number", "help", "load_user_translations", 
    "register", "REGISTRY", "set_language", "show_gui_popup", "t",
    
    # Constantes
    "BIG_SIZE", "CONFIG_LANG", "NORMAL_SIZE",
    
    # Utilidades
    "is_jupyter_notebook", "IN_JUPYTER"
]
