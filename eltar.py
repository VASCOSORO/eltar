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
    # Conversión a puntos y luego a píxeles base para pantalla (72 DPI aprox)
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    
    # Márgenes en pt
    ml_pt = ml_cm * CM_TO_PT; mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT; mb_pt = mb_cm * CM_TO_PT

    page_w_px = int(round(pw_pt))
    page_h_px = int(round(ph_pt))

    preview = Image.new("RGB", (page_w_px, page_h_px), "white")
    draw = ImageDraw.Draw(preview)

    # Dimensiones de la imagen compuesta
    c_w, c_h = composed_image.size
    
    # Espacio útil dentro de los márgenes
    content_w_pt = pw_pt - (ml_pt + mr_pt)
    content_h_pt = ph_pt - (mt_pt + mb_pt)
    
    # Calcular escala para ajustar ("fit") la composición en el área útil
    scale = min(content_w_pt / c_w, content_h_pt / c_h)
    
    final_w = c_w * scale
    final_h = c_h * scale

    # Posición centrada
    x_pos = ml_pt + (content_w_pt - final_w) / 2
    y_pos = mt_pt + (content_h_pt - final_h) / 2

    x_pos_px = int(round(x_pos))
    y_pos_px = int(round(y_pos))
    final_w_px = int(round(final_w))
    final_h_px = int(round(final_h))

    # Redimensionar para la preview (usando LANCZOS para que se vea bien aunque sea chica)
    scaled = composed_image.resize((final_w_px, final_h_px), Image.Resampling.LANCZOS)
    preview.paste(scaled, (x_pos_px, y_pos_px))

    # Dibujar guías
    guide_color = (220, 53, 69) # Rojo moderno
    lw = 2
    
    xr = x_pos_px + final_w_px
    yb = y_pos_px + final_h_px

    # Marco exterior
    draw.rectangle([x_pos_px, y_pos_px, xr, yb], outline=guide_color, width=lw)
    
    # Líneas de corte extendidas (estilo imprenta)
    # Verticales
    draw.line([(x_pos_px, 0), (x_pos_px, page_h_px)], fill=guide_color, width=1)
    draw.line([(xr, 0), (xr, page_h_px)], fill=guide_color, width=1)
    
    # Horizontales
    draw.line([(0, y_pos_px), (page_w_px, y_pos_px)], fill=guide_color, width=1)
    draw.line([(0, yb), (page_w_px, yb)], fill=guide_color, width=1)

    # Columnas internas
    for col in range(1, cols):
        x_col = x_pos_px + int(round(col * final_w_px / cols))
        draw.line([(x_col, 0), (x_col, y_pos_px)], fill=guide_color, width=1)
        draw.line([(x_col, yb), (x_col, page_h_px)], fill=guide_color, width=1)

    # Filas internas
    for row in range(1, rows):
        y_row = y_pos_px + int(round(row * final_h_px / rows))
        draw.line([(0, y_row), (x_pos_px, y_row)], fill=guide_color, width=1)
        draw.line([(xr, y_row), (page_w_px, y_row)], fill=guide_color, width=1)

    return preview


def create_pdf(composed_image, page_w_cm, page_h_cm, ml_cm, mr_cm, mt_cm, mb_cm, cols, rows, target_dpi=300):
    """
    Genera el PDF final de alta calidad.
    """
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT; mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT; mb_pt = mb_cm * CM_TO_PT

    # Dimensiones de la imagen compuesta (Pixels reales)
    c_w, c_h = composed_image.size
    
    # Área útil en el PDF (Puntos)
    cw_area_pt = pw_pt - (ml_pt + mr_pt)
    ch_area_pt = ph_pt - (mt_pt + mb_pt)

    # Escala para convertir Pixels a Puntos ajustándose al área útil
    scale = min(cw_area_pt / c_w, ch_area_pt / c_h)
    
    final_w_pt = c_w * scale
    final_h_pt = c_h * scale

    # Centrado
    x_pos = ml_pt + (cw_area_pt - final_w_pt) / 2
    y_pos = mt_pt + (ch_area_pt - final_h_pt) / 2

    # --- PREPARACIÓN DE IMAGEN ---
    # Convertimos la imagen compuesta a la resolución final requerida (300 DPI)
    # Cálculo: (Puntos en PDF / 72) * DPI Deseado = Pixels necesarios
    target_px_w = int(round((final_w_pt / 72.0) * target_dpi))
    target_px_h = int(round((final_h_pt / 72.0) * target_dpi))
    
    hires = composed_image.resize((target_px_w, target_px_h), Image.Resampling.LANCZOS)
    
    # Guardar temporal
    temp_path = f"temp_{int(page_w_cm)}x{int(page_h_cm)}.png"
    hires.save(temp_path, "PNG", compress_level=0)

    # --- GENERACIÓN PDF ---
    pdf = FPDF(unit="pt", format=[pw_pt, ph_pt])
    pdf.set_auto_page_break(False)
    pdf.add_page()
    
    # Insertar imagen (FPDF usa dimensiones en puntos)
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w_pt, h=final_h_pt)

    # Líneas de corte (Negro de registro, fino)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)

    xr = x_pos + final_w_pt
    yb = y_pos + final_h_pt

    # Guías externas (Esquinas)
    pdf.line(x_pos, 0, x_pos, y_pos)
    pdf.line(x_pos, yb, x_pos, ph_pt)
    pdf.line(xr, 0, xr, y_pos)
    pdf.line(xr, yb, xr, ph_pt)
    
    pdf.line(0, y_pos, x_pos, y_pos)
    pdf.line(xr, y_pos, pw_pt, y_pos)
    pdf.line(0, yb, x_pos, yb)
    pdf.line(xr, yb, pw_pt, yb)

    # Guías internas (Columnas)
    for col in range(1, cols):
        # Usamos float para precisión en PDF
        x_col = x_pos + (col * final_w_pt / cols)
        pdf.line(x_col, 0, x_col, y_pos)
        pdf.line(x_col, yb, x_col, ph_pt)

    # Guías internas (Filas)
    for row in range(1, rows):
        y_row = y_pos + (row * final_h_pt / rows)
        pdf.line(0, y_row, x_pos, y_row)
        pdf.line(xr, y_row, pw_pt, y_row)

    pdf_bytes = pdf.output(dest='S').encode('latin-1')

    # Limpiar
    try:
        os.remove(temp_path)
    except:
        pass
        
    return pdf_bytes


def auto_rotate_for_format(img, chosen_format):
    """
    Rota la imagen inteligentemente basándose en si la celda destino es vertical u horizontal.
    Esto previene que imágenes horizontales queden comprimidas en celdas verticales.
    """
    w, h = img.size
    
    # Súper A3 y A3 suelen tener celdas verticales (ej: 9x3)
    if "A3" in chosen_format:
        if w > h: # Imagen es horizontal, pero la celda es vertical
            return img.rotate(90, expand=True)
            
    # A4 (3x4) suele tener celdas horizontales (ej: 9x5cm acostadas)
    elif "A4" in chosen_format:
        if h > w: # Imagen es vertical, pero la celda es horizontal
            return img.rotate(90, expand=True)
            
    return img


def compose_template_hd(user_image, cols, rows, content_w_pt, content_h_pt, target_dpi=300):
    """
    Compone la grilla. 
    CORRECCIÓN DE DESFASE: Calcula el tamaño de celda exacto en píxeles enteros
    y construye el lienzo en base a eso, evitando errores de redondeo.
    """
    # 1. Calcular tamaño máximo disponible en píxeles
    max_w_px = int(round((content_w_pt / 72.0) * target_dpi))
    max_h_px = int(round((content_h_pt / 72.0) * target_dpi))

    # 2. Calcular tamaño EXACTO de una tarjeta (división entera)
    card_w = max_w_px // cols
    card_h = max_h_px // rows
    
    # 3. Recalcular el tamaño del lienzo TOTAL basado en las tarjetas exactas.
    # Esto elimina la "fuga" de píxeles que causaba el desfase.
    exact_total_w = card_w * cols
    exact_total_h = card_h * rows

    composed = Image.new("RGBA", (exact_total_w, exact_total_h), (255, 255, 255, 0))

    # Pre-escalar una vez para eficiencia
    # ImageOps.fit recorta el centro para llenar sin deformar
    card_img = ImageOps.fit(user_image, (card_w, card_h), method=Image.Resampling.LANCZOS)

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
        
        # Validación de calidad
        if user_img.width < 1000 or user_img.height < 1000:
            st.toast("⚠️ Tu imagen tiene baja resolución. Podría salir pixelada.", icon="⚠️")
        else:
            st.toast("✅ Imagen de buena calidad detectada.", icon="✨")

        st.divider()

        # Layout de configuración
        c_config, c_preview = st.columns([1, 2], gap="large")

        with c_config:
            st.write("### ⚙️ Configuración")
            preview_option = st.radio(
                "Seleccioná el formato:",
                ["Súper A3 (9×3=27)", "A3 (8×3=24)", "A4 (3×4=12)"],
                captions=["47.5 x 32.5 cm", "42.0 x 29.7 cm", "29.7 x 21.0 cm"]
            )
            
            st.info(f"📐 Tu imagen: {user_img.width} x {user_img.height} px")

        # Generar Preview (Baja res para velocidad)
        (pw_cm, ph_cm, ml_cm, mr_cm, mt_cm, mb_cm, colz, rowz) = get_config(preview_option)
        
        pw_pt = pw_cm * CM_TO_PT; ph_pt = ph_cm * CM_TO_PT
        ml_pt = ml_cm * CM_TO_PT; mr_pt = mr_cm * CM_TO_PT
        mt_pt = mt_cm * CM_TO_PT; mb_pt = mb_cm * CM_TO_PT
        content_w_pt = pw_pt - (ml_pt + mr_pt)
        content_h_pt = ph_pt - (mt_pt + mb_pt)

        rotated_img_prev = auto_rotate_for_format(user_img, preview_option)
        
        # Generamos preview rápido a 72 DPI
        composed_prev = compose_template_hd(rotated_img_prev, colz, rowz, content_w_pt, content_h_pt, target_dpi=72)
        preview_viz = draw_preview_image(composed_prev, pw_cm, ph_cm, ml_cm, mr_cm, mt_cm, mb_cm, colz, rowz)

        with c_preview:
            st.image(preview_viz, caption="Vista Previa (Guías en Rojo)", use_column_width=True)

        st.divider()
        st.write("### ⬇️ Descargar Archivos de Producción (300 DPI)")

        cols_dl = st.columns(3)

        # Generador dinámico de botones
        format_map = {
            "Súper A3": ("Súper A3 (9×3=27)", "superA3"),
            "A3": ("A3 (8×3=24)", "A3"),
            "A4": ("A4 (3×4=12)", "A4")
        }

        for i, (label, (conf_key, file_suffix)) in enumerate(format_map.items()):
            with cols_dl[i]:
                if st.button(f"Generar {label}"):
                    with st.spinner(f"Renderizando {label} en Alta Definición..."):
                        try:
                            # 1. Configuración
                            cfg = get_config(conf_key)
                            (pw, ph, ml, mr, mt, mb, c, r) = cfg
                            
                            # 2. Preparar dimensiones
                            pw_p = pw * CM_TO_PT; ph_p = ph * CM_TO_PT
                            cw_p = pw_p - (ml + mr) * CM_TO_PT
                            ch_p = ph_p - (mt + mb) * CM_TO_PT
                            
                            # 3. Procesar Imagen
                            rot = auto_rotate_for_format(user_img, conf_key)
                            
                            # 4. Componer en HD (300 DPI)
                            comp = compose_template_hd(rot, c, r, cw_p, ch_p, target_dpi=300)
                            
                            # 5. Generar PDF
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
