
import os
import json
import streamlit as st

_translations = {}

def load_translations(path="translations.json"):
    global _translations
    # Cargar traducciones base
    base_translations = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                base_translations = json.load(f)
    except Exception as e:
        print(f"Error cargando traducciones base: {e}")

    # Buscar traducciones en módulos
    # root_path es el directorio padre de 'utils'
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    modules_path = os.path.join(root_path, "modules")
    
    if os.path.exists(modules_path):
        for root, dirs, files in os.walk(modules_path):
            if "translations.json" in files:
                file_path = os.path.join(root, "translations.json")
                # Evitar cargar el archivo base si está dentro de modules por error
                if os.path.abspath(file_path) == os.path.abspath(path):
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        module_translations = json.load(f)
                        for lang, keys in module_translations.items():
                            if lang not in base_translations:
                                base_translations[lang] = {}
                            base_translations[lang].update(keys)
                except Exception as e:
                    print(f"Error cargando traducciones de {file_path}: {e}")

    _translations = base_translations

def t(key, **kwargs):
    lang = st.session_state.get("lang", "es")
    translation = _translations.get(lang, {}).get(key, key)
    return translation.format(**kwargs)

def inject_custom_css():
    st.markdown(f"""
        <style>
            .e16n7gab3::before {{ 
                content: "{t('uploader_drag')}" !important;
            }}
            .stFileUploader .e1q4kxr42::after {{ 
                content: "{t('uploader_browse')}" !important;
            }}
        </style>
    """, unsafe_allow_html=True)
