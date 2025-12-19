import streamlit as st
from PIL import Image, ImageOps, ImageDraw
from fpdf import FPDF
import io
import os
import math

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Tarjezor Pro", 
    layout="centered", 
    page_icon="🖨️"
)

# --- ESTILOS CSS MODERNOS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header-style {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

CM_TO_PT = 28.3465

# ---------------------------
# 1) FUNCIONES GRÁFICAS (CORE)
# ---------------------------

def draw_preview_image(composed_image, page_w_cm, page_h_cm, ml_cm, mr_cm, mt_cm, mb_cm, cols, rows):
    """
    Genera una vista previa rápida con líneas de guía visuales (rojas).
    """
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    
    ml_pt = ml_cm * CM_TO_PT; mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT; mb_pt = mb_cm * CM_TO_PT

    page_w_px = int(round(pw_pt))
    page_h_px = int(round(ph_pt))

    preview = Image.new("RGB", (page_w_px, page_h_px), "white")
    draw = ImageDraw.Draw(preview)

    c_w, c_h = composed_image.size
    
    content_w_pt = pw_pt - (ml_pt + mr_pt)
    content_h_pt = ph_pt - (mt_pt + mb_pt)
    
    scale = min(content_w_pt / c_w, content_h_pt / c_h)
    
    final_w = c_w * scale
    final_h = c_h * scale

    x_pos = ml_pt + (content_w_pt - final_w) / 2
    y_pos = mt_pt + (content_h_pt - final_h) / 2

    x_pos_px = int(round(x_pos))
    y_pos_px = int(round(y_pos))
    final_w_px = int(round(final_w))
    final_h_px = int(round(final_h))

    # Usamos LANCZOS para buena calidad en pantalla
    scaled = composed_image.resize((final_w_px, final_h_px), Image.LANCZOS)
    # Convertimos a RGB para evitar conflictos de transparencia en visualización
    if scaled.mode == 'RGBA':
        scaled = scaled.convert('RGB')
        
    preview.paste(scaled, (x_pos_px, y_pos_px))

    guide_color = (220, 53, 69)
    lw = 2
    
    xr = x_pos_px + final_w_px
    yb = y_pos_px + final_h_px

    # Marco
    draw.rectangle([x_pos_px, y_pos_px, xr, yb], outline=guide_color, width=lw)
    
    # Líneas
    draw.line([(x_pos_px, 0), (x_pos_px, page_h_px)], fill=guide_color, width=1)
    draw.line([(xr, 0), (xr, page_h_px)], fill=guide_color, width=1)
    draw.line([(0, y_pos_px), (page_w_px, y_pos_px)], fill=guide_color, width=1)
    draw.line([(0, yb), (page_w_px, yb)], fill=guide_color, width=1)

    for col in range(1, cols):
        x_col = x_pos_px + int(round(col * final_w_px / cols))
        draw.line([(x_col, 0), (x_col, y_pos_px)], fill=guide_color, width=1)
        draw.line([(x_col, yb), (x_col, page_h_px)], fill=guide_color, width=1)

    for row in range(1, rows):
        y_row = y_pos_px + int(round(row * final_h_px / rows))
        draw.line([(0, y_row), (x_pos_px, y_row)], fill=guide_color, width=1)
        draw.line([(xr, y_row), (page_w_px, y_row)], fill=guide_color, width=1)

    return preview


def create_pdf(composed_image, page_w_cm, page_h_cm, ml_cm, mr_cm, mt_cm, mb_cm, cols, rows, target_dpi=300):
    """
    Genera el PDF compatible con FPDF antiguo (1.7.2).
    """
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT; mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT; mb_pt = mb_cm * CM_TO_PT

    c_w, c_h = composed_image.size
    
    cw_area_pt = pw_pt - (ml_pt + mr_pt)
    ch_area_pt = ph_pt - (mt_pt + mb_pt)

    scale = min(cw_area_pt / c_w, ch_area_pt / c_h)
    
    final_w_pt = c_w * scale
    final_h_pt = c_h * scale

    x_pos = ml_pt + (cw_area_pt - final_w_pt) / 2
    y_pos = mt_pt + (ch_area_pt - final_h_pt) / 2

    # --- PREPARACIÓN DE IMAGEN (FIX para FPDF 1.7.2) ---
    # 1. Calcular resolución real en pixeles
    target_px_w = int(round((final_w_pt / 72.0) * target_dpi))
    target_px_h = int(round((final_h_pt / 72.0) * target_dpi))
    
    hires = composed_image.resize((target_px_w, target_px_h), Image.LANCZOS)
    
    # 2. IMPORTANTE: Convertir a RGB (Quitar canal Alfa/Transparencia)
    # FPDF viejo falla con RGBA o pone fondos negros.
    if hires.mode == 'RGBA':
        background = Image.new("RGB", hires.size, (255, 255, 255))
        background.paste(hires, mask=hires.split()[3]) # 3 is alpha channel
        hires = background
    elif hires.mode != 'RGB':
        hires = hires.convert('RGB')

    temp_path = f"temp_{int(page_w_cm)}x{int(page_h_cm)}.jpg"
    # Usamos JPEG calidad máxima para evitar problemas de compatibilidad en FPDF viejo
    hires.save(temp_path, "JPEG", quality=100, optimize=True)

    # --- GENERACIÓN PDF ---
    pdf = FPDF(unit="pt", format=[pw_pt, ph_pt])
    pdf.set_auto_page_break(False)
    pdf.add_page()
    
    # Insertar imagen
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w_pt, h=final_h_pt)

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)

    xr = x_pos + final_w_pt
    yb = y_pos + final_h_pt

    # Líneas de corte
    pdf.line(x_pos, 0, x_pos, y_pos)
    pdf.line(x_pos, yb, x_pos, ph_pt)
    pdf.line(xr, 0, xr, y_pos)
    pdf.line(xr, yb, xr, ph_pt)
    
    pdf.line(0, y_pos, x_pos, y_pos)
    pdf.line(xr, y_pos, pw_pt, y_pos)
    pdf.line(0, yb, x_pos, yb)
    pdf.line(xr, yb, pw_pt, yb)

    for col in range(1, cols):
        x_col = x_pos + (col * final_w_pt / cols)
        pdf.line(x_col, 0, x_col, y_pos)
        pdf.line(x_col, yb, x_col, ph_pt)

    for row in range(1, rows):
        y_row = y_pos + (row * final_h_pt / rows)
        pdf.line(0, y_row, x_pos, y_row)
        pdf.line(xr, y_row, pw_pt, y_row)

    pdf_str = pdf.output(dest='S')
    # En FPDF 1.7.2 output devuelve string en py3 (bytes mal codificados a veces),
    # o latin-1 string. Lo convertimos a bytes seguramente.
    if isinstance(pdf_str, str):
        pdf_bytes = pdf_str.encode('latin-1')
    else:
        pdf_bytes = pdf_str

    try:
        os.remove(temp_path)
    except:
        pass
        
    return pdf_bytes


def auto_rotate_for_format(img, chosen_format):
    w, h = img.size
    if "A3" in chosen_format:
        if w > h: 
            return img.rotate(90, expand=True)
    elif "A4" in chosen_format:
        if h > w: 
            return img.rotate(90, expand=True)
    return img


def compose_template_hd(user_image, cols, rows, content_w_pt, content_h_pt, target_dpi=300, scaling_mode="fit"):
    """
    Compone la grilla. CORRECCIÓN DE DESFASE.
    scaling_mode: 'fit' (recortar), 'stretch' (estirar), 'pad' (encajar)
    """
    max_w_px = int(round((content_w_pt / 72.0) * target_dpi))
    max_h_px = int(round((content_h_pt / 72.0) * target_dpi))

    # División entera para evitar decimales flotantes
    card_w = max_w_px // cols
    card_h = max_h_px // rows
    
    exact_total_w = card_w * cols
    exact_total_h = card_h * rows

    # Usamos RGBA para componer
    composed = Image.new("RGBA", (exact_total_w, exact_total_h), (255, 255, 255, 0))

    # --- LÓGICA DE ESCALADO ---
    if scaling_mode == "stretch":
        # Estirar: Ignora proporción, llena todo el cuadro (puede deformar)
        card_img = user_image.resize((card_w, card_h), resample=Image.LANCZOS)
    elif scaling_mode == "pad":
        # Encajar: Mantiene proporción, agrega bordes blancos si sobra espacio
        card_img = ImageOps.pad(user_image, (card_w, card_h), method=Image.LANCZOS, color=(255, 255, 255, 0), centering=(0.5, 0.5))
    else:
        # Fit (Default): Hace zoom para llenar todo, recorta lo que sobra
        card_img = ImageOps.fit(user_image, (card_w, card_h), method=Image.LANCZOS)

    for rr in range(rows):
        for cc in range(cols):
            x = cc * card_w
            y = rr * card_h
            composed.paste(card_img, (x, y))
            
    return composed

# Configuración de formatos
def get_config(option):
    if "Súper A3" in option:
        return (47.5, 32.5, 1.0, 1.0, 2.57, 2.57, 9, 3)
    elif "A3" in option:
        return (42.0, 29.7, 1.0, 1.0, 1.0, 1.0, 8, 3)
    else:  # A4
        return (29.7, 21.0, 1.0, 1.0, 1.0, 1.0, 3, 4)

# ---------------------------
# MAIN APP
# ---------------------------
def main():
    st.markdown('<div class="header-style">🖨️ Tarjezor Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Generador de planchas de alta resolución</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Arrastrá tu diseño aquí (JPG o PNG)", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        user_img = Image.open(uploaded_file).convert("RGBA")
        
        if user_img.width < 1000 or user_img.height < 1000:
            st.toast("⚠️ Tu imagen tiene baja resolución. Podría salir pixelada.", icon="⚠️")
        else:
            st.toast("✅ Imagen de buena calidad detectada.", icon="✨")

        st.divider()

        c_config, c_preview = st.columns([1, 2], gap="large")

        with c_config:
            st.write("### ⚙️ Configuración")
            preview_option = st.radio(
                "Seleccioná el formato:",
                ["Súper A3 (9×3=27)", "A3 (8×3=24)", "A4 (3×4=12)"]
            )
            
            # --- NUEVO SELECTOR DE AJUSTE ---
            st.write("### 🖼️ Ajuste de Imagen")
            fit_mode = st.selectbox(
                "¿Cómo querés que entre la imagen?",
                options=["pad", "stretch", "fit"],
                format_func=lambda x: {
                    "pad": "Encajar (Sin cortes, bordes blancos)",
                    "stretch": "Estirar (Llenar todo, puede deformar)",
                    "fit": "Recortar (Llenar todo, zoom auto)"
                }[x]
            )

            st.info(f"📐 Tu imagen: {user_img.width} x {user_img.height} px")

        (pw_cm, ph_cm, ml_cm, mr_cm, mt_cm, mb_cm, colz, rowz) = get_config(preview_option)
        
        pw_pt = pw_cm * CM_TO_PT; ph_pt = ph_cm * CM_TO_PT
        ml_pt = ml_cm * CM_TO_PT; mr_pt = mr_cm * CM_TO_PT
        mt_pt = mt_cm * CM_TO_PT; mb_pt = mb_cm * CM_TO_PT
        content_w_pt = pw_pt - (ml_pt + mr_pt)
        content_h_pt = ph_pt - (mt_pt + mb_pt)

        rotated_img_prev = auto_rotate_for_format(user_img, preview_option)
        
        # Preview rápida (72 DPI) - Pasamos el modo de ajuste
        composed_prev = compose_template_hd(rotated_img_prev, colz, rowz, content_w_pt, content_h_pt, target_dpi=72, scaling_mode=fit_mode)
        preview_viz = draw_preview_image(composed_prev, pw_cm, ph_cm, ml_cm, mr_cm, mt_cm, mb_cm, colz, rowz)

        with c_preview:
            st.image(preview_viz, caption="Vista Previa (Guías en Rojo)", use_column_width=True)

        st.divider()
        st.write("### ⬇️ Descargar Archivos de Producción (300 DPI)")

        cols_dl = st.columns(3)

        format_map = {
            "Súper A3": ("Súper A3 (9×3=27)", "superA3"),
            "A3": ("A3 (8×3=24)", "A3"),
            "A4": ("A4 (3×4=12)", "A4")
        }

        for i, (label, (conf_key, file_suffix)) in enumerate(format_map.items()):
            with cols_dl[i]:
                if st.button(f"Generar {label}"):
                    with st.spinner(f"Procesando {label}..."):
                        try:
                            cfg = get_config(conf_key)
                            (pw, ph, ml, mr, mt, mb, c, r) = cfg
                            
                            pw_p = pw * CM_TO_PT; ph_p = ph * CM_TO_PT
                            cw_p = pw_p - (ml + mr) * CM_TO_PT
                            ch_p = ph_p - (mt + mb) * CM_TO_PT
                            
                            rot = auto_rotate_for_format(user_img, conf_key)
                            
                            # Generamos la composición en memoria a 300 DPI - Pasamos el modo de ajuste
                            comp = compose_template_hd(rot, c, r, cw_p, ch_p, target_dpi=300, scaling_mode=fit_mode)
                            
                            # Creamos el PDF compatible con FPDF 1.7.2
                            pdf_bytes = create_pdf(comp, pw, ph, ml, mr, mt, mb, c, r, target_dpi=300)
                            
                            st.download_button(
                                label=f"💾 Bajar PDF {label}",
                                data=pdf_bytes,
                                file_name=f"tarjetas_{file_suffix}_300dpi.pdf",
                                mime="application/pdf"
                            )
                            st.toast(f"¡{label} generado con éxito!", icon="🚀")
                            
                        except Exception as e:
                            st.error(f"Error al generar: {str(e)}")

if __name__ == "__main__":
    main()
