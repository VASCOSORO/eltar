import streamlit as st
from PIL import Image, ImageOps, ImageDraw
from fpdf import FPDF
import io
import os
import math

# Configuración de página de Streamlit (debe ser lo primero)
st.set_page_config(page_title="Tarjezor Pro", layout="centered", page_icon="🖨️")

CM_TO_PT = 28.3465

# ---------------------------
# 1) FUNCIONES DE CORTE / PREVIEW
# ---------------------------
def draw_preview_image(
    composed_image,
    page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows
):
    """
    Crea una imagen PIL para mostrar en pantalla con las líneas de corte.
    """
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    # Convertir puntos a pixeles base para preview (72 DPI base visual)
    page_w_px = int(round(pw_pt))
    page_h_px = int(round(ph_pt))

    preview = Image.new("RGB", (page_w_px, page_h_px), "white")
    draw = ImageDraw.Draw(preview)

    # Escalado del compuesto dentro del área útil
    c_w, c_h = composed_image.size
    
    # Área útil
    content_w_pt = pw_pt - (ml_pt + mr_pt)
    content_h_pt = ph_pt - (mt_pt + mb_pt)
    
    # Calcular escala para que entre en la hoja preview
    scale = min(content_w_pt / c_w, content_h_pt / c_h)
    
    final_w = c_w * scale
    final_h = c_h * scale

    x_pos = ml_pt + (content_w_pt - final_w) / 2
    y_pos = mt_pt + (content_h_pt - final_h) / 2

    # Convertir a px para dibujar
    x_pos_px = int(round(x_pos))
    y_pos_px = int(round(y_pos))
    final_w_px = int(round(final_w))
    final_h_px = int(round(final_h))

    # Pegar imagen escalada (LANCZOS para calidad en reducción)
    scaled = composed_image.resize((final_w_px, final_h_px), Image.Resampling.LANCZOS)
    preview.paste(scaled, (x_pos_px, y_pos_px))

    color = (200, 0, 0) # Rojo oscuro para guías
    lw = 2
    x_right = x_pos_px + final_w_px
    y_bottom = y_pos_px + final_h_px

    # --- DIBUJO DE GUIAS ---
    # Marco externo
    draw.line([(x_pos_px, 0), (x_pos_px, y_pos_px)], fill=color, width=lw) # TL vert
    draw.line([(x_pos_px, y_bottom), (x_pos_px, page_h_px)], fill=color, width=lw) # BL vert
    
    draw.line([(x_right, 0), (x_right, y_pos_px)], fill=color, width=lw) # TR vert
    draw.line([(x_right, y_bottom), (x_right, page_h_px)], fill=color, width=lw) # BR vert
    
    draw.line([(0, y_pos_px), (x_pos_px, y_pos_px)], fill=color, width=lw) # TL horiz
    draw.line([(x_right, y_pos_px), (page_w_px, y_pos_px)], fill=color, width=lw) # TR horiz
    
    draw.line([(0, y_bottom), (x_pos_px, y_bottom)], fill=color, width=lw) # BL horiz
    draw.line([(x_right, y_bottom), (page_w_px, y_bottom)], fill=color, width=lw) # BR horiz

    # Columnas (Guías superiores e inferiores)
    for col in range(1, cols):
        # Calculamos la posición exacta basada en el ancho visual
        x_col = x_pos_px + int(round(col * final_w_px / cols))
        draw.line([(x_col, 0), (x_col, y_pos_px)], fill=color, width=lw)
        draw.line([(x_col, y_bottom), (x_col, page_h_px)], fill=color, width=lw)

    # Filas (Guías laterales)
    for row in range(1, rows):
        y_row = y_pos_px + int(round(row * final_h_px / rows))
        draw.line([(0, y_row), (x_pos_px, y_row)], fill=color, width=lw)
        draw.line([(x_right, y_row), (page_w_px, y_row)], fill=color, width=lw)

    return preview


def create_pdf(
    composed_image,
    page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows,
    target_dpi=300
):
    """
    Genera un PDF de alta calidad.
    """
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    # Dimensiones reales del "canvas" de la imagen compuesta
    c_w, c_h = composed_image.size
    
    # Dimensiones útiles en el PDF
    cw_area_pt = pw_pt - (ml_pt + mr_pt)
    ch_area_pt = ph_pt - (mt_pt + mb_pt)

    # Factor de escala para pasar de Píxeles (imagen) a Puntos (PDF)
    # manteniendo la relación de aspecto y asegurando que quepa
    scale = min(cw_area_pt / c_w, ch_area_pt / c_h)
    
    final_w_pt = c_w * scale
    final_h_pt = c_h * scale

    # Centrado
    x_pos = ml_pt + (cw_area_pt - final_w_pt) / 2
    y_pos = mt_pt + (ch_area_pt - final_h_pt) / 2

    # --- PREPARAR IMAGEN PARA PDF ---
    # Calcular píxeles objetivo para impresión nítida
    # 1 pt = 1/72 pulgada. DPI = pixels per inch.
    # Pixels necesarios = (pts / 72) * DPI
    target_px_w = int(round((final_w_pt / 72.0) * target_dpi))
    target_px_h = int(round((final_h_pt / 72.0) * target_dpi))
    
    # Redimensionar la imagen compuesta a la resolución final de impresión
    hires = composed_image.resize((target_px_w, target_px_h), Image.Resampling.LANCZOS)

    # Guardar temporalmente
    temp_path = f"temp_comp_{int(page_w_cm)}_{int(page_h_cm)}.png"
    hires.save(temp_path, "PNG", compress_level=0)

    # --- GENERAR PDF ---
    pdf = FPDF(unit="pt", format=[pw_pt, ph_pt])
    pdf.set_auto_page_break(False)
    pdf.add_page()
    
    # Insertar imagen (FPDF escala automáticamente a las dimensiones w/h dadas en puntos)
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w_pt, h=final_h_pt)

    # Dibujar líneas de corte
    pdf.set_draw_color(0, 0, 0) # Negro puro para impresión
    pdf.set_line_width(0.5)

    xr = x_pos + final_w_pt
    yb = y_pos + final_h_pt

    # Marco (Marcas de esquina)
    len_mark = 10 # Largo de la marca de corte hacia afuera

    # Verticales externas
    pdf.line(x_pos, 0, x_pos, y_pos) # TL Arr
    pdf.line(x_pos, yb, x_pos, ph_pt) # BL Abj
    pdf.line(xr, 0, xr, y_pos) # TR Arr
    pdf.line(xr, yb, xr, ph_pt) # BR Abj
    
    # Horizontales externas
    pdf.line(0, y_pos, x_pos, y_pos) # TL Izq
    pdf.line(xr, y_pos, pw_pt, y_pos) # TR Der
    pdf.line(0, yb, x_pos, yb) # BL Izq
    pdf.line(xr, yb, pw_pt, yb) # BR Der

    # Divisiones internas (Columnas)
    for col in range(1, cols):
        # IMPORTANTE: Usar la misma lógica de fracción que la imagen
        # La imagen se construyó con enteros, pero en PDF usamos floats.
        # Al alinear final_w con la imagen exacta, la división matemática es segura.
        x_col = x_pos + (col * final_w_pt / cols)
        pdf.line(x_col, 0, x_col, y_pos)
        pdf.line(x_col, yb, x_col, ph_pt)

    # Divisiones internas (Filas)
    for row in range(1, rows):
        y_row = y_pos + (row * final_h_pt / rows)
        pdf.line(0, y_row, x_pos, y_row)
        pdf.line(xr, y_row, pw_pt, y_row)

    pdf_str = pdf.output(dest='S')
    pdf_bytes = pdf_str.encode('latin-1')

    # Limpieza
    try:
        os.remove(temp_path)
    except:
        pass
        
    return pdf_bytes

# ---------------------------
# 2) LÓGICA DE AUTO ROTACIÓN
# ---------------------------
def auto_rotate_for_format(img, chosen_format):
    """
    Rota la imagen original para aprovechar mejor el espacio de la tarjeta individual.
    Asumimos que si la tarjeta es vertical, queremos la imagen vertical, etc.
    """
    w, h = img.size
    
    # Determinar orientación de la "tarjeta" (celda), no solo de la hoja.
    # Hoja Súper A3/A3 es apaisada generalmente, pero las tarjetas pueden variar.
    # Aquí mantenemos la lógica simple del usuario: 
    # Hoja grande (A3) suele usarse verticalmente en impresoras o el diseño entra vertical.
    
    if "A4" in chosen_format:
        # A4 (horizontal en diseño general) => 3x4
        # Si la imagen es más alta que ancha, rotar para que entre acostada?
        # Depende del diseño. Dejamos la lógica original pero forzamos exapnd.
        if h > w:
            return img.rotate(90, expand=True)
    else:
        # Súper A3 / A3
        if w > h:
            return img.rotate(90, expand=True)
            
    return img

# ---------------------------
# 3) COMPOSICIÓN HD (CORREGIDA)
# ---------------------------
def adjust_image(image, size):
    # ImageOps.fit recorta el centro para llenar el espacio (sin deformar)
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)

def compose_template_hd(user_image, cols, rows, content_w_pt, content_h_pt, target_dpi=300):
    """
    Compone la grilla.
    CORRECCIÓN CRÍTICA: Ajusta el tamaño del canvas al múltiplo exacto de las tarjetas
    para evitar el 'drift' (desfase) de las líneas de corte.
    """
    # 1. Calcular el tamaño total disponible en píxeles a la resolución deseada
    max_w_px = int(round((content_w_pt / 72.0) * target_dpi))
    max_h_px = int(round((content_h_pt / 72.0) * target_dpi))

    # 2. Calcular el tamaño exacto de CADA tarjeta (entero)
    card_w = max_w_px // cols
    card_h = max_h_px // rows
    
    # 3. Recalcular el tamaño del canvas para que sea EXACTO (sin resto)
    # Esto elimina la franja blanca que causaba el desfase
    exact_total_w = card_w * cols
    exact_total_h = card_h * rows

    # canvas RGBA
    composed = Image.new("RGBA", (exact_total_w, exact_total_h), (255, 255, 255, 0))

    # Optimización: Redimensionar imagen una sola vez si es posible, 
    # pero ImageOps.fit lo maneja bien por tarjeta.
    
    for rr in range(rows):
        for cc in range(cols):
            x = cc * card_w
            y = rr * card_h
            # Ajustar imagen a la celda
            piece = adjust_image(user_image, (card_w, card_h))
            composed.paste(piece, (x, y))
            
    return composed

# ---------------------------
# 4) CONFIG DE FORMATOS
# ---------------------------
def get_config(option):
    # Retorna: (width_cm, height_cm, marg_left, marg_right, marg_top, marg_bottom, cols, rows)
    if "Súper A3" in option:
        return (47.5, 32.5, 1.0, 1.0, 2.57, 2.57, 9, 3)
    elif "A3" in option:
        # A3 estándar 42x29.7
        return (42.0, 29.7, 1.0, 1.0, 1.0, 1.0, 8, 3)
    else:  # "A4"
        return (29.7, 21.0, 1.0, 1.0, 1.0, 1.0, 3, 4)

# ---------------------------
# 5) STREAMLIT MAIN
# ---------------------------
def main():
    # Estilos CSS para modernizar botones
    st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #007bff;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #0056b3;
    }
    .main-header {
        font-size: 2.5rem;
        color: #333;
        text-align: center;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-header">🖨️ Tarjezor Pro</div>', unsafe_allow_html=True)
    st.write("Generador profesional de planchas de tarjetas con guías de corte precisas.")

    uploaded_file = st.file_uploader("📂 Subí tu diseño (PNG o JPG)", type=["png", "jpg", "jpeg"])
    
    if uploaded_file:
        try:
            user_img = Image.open(uploaded_file).convert("RGBA")
            
            # Chequeo rápido de resolución
            if user_img.width < 500 or user_img.height < 500:
                st.warning("⚠️ Tu imagen tiene baja resolución. Para impresión profesional, recomendamos imágenes de al menos 1000px.")
            else:
                st.toast("✅ Imagen cargada correctamente", icon="🖼️")

            st.divider()

            # Opciones
            col_opts, col_preview = st.columns([1, 2])
            
            with col_opts:
                st.subheader("⚙️ Configuración")
                preview_option = st.selectbox(
                    "Formato de papel:",
                    ["Súper A3 (9×3=27)", "A3 (8×3=24)", "A4 (3×4=12)"]
                )
                
                st.info(f"Dimensiones detectadas: {user_img.width}x{user_img.height} px")

            # --- PREVIEW (Baja Resolución para velocidad) ---
            (pw_cm, ph_cm, ml_cm, mr_cm, mt_cm, mb_cm, colz, rowz) = get_config(preview_option)
            
            # Calculamos dimensiones útiles
            pw_pt = pw_cm * CM_TO_PT; ph_pt = ph_cm * CM_TO_PT
            ml_pt = ml_cm * CM_TO_PT; mr_pt = mr_cm * CM_TO_PT
            mt_pt = mt_cm * CM_TO_PT; mb_pt = mb_cm * CM_TO_PT
            content_w_pt = pw_pt - (ml_pt + mr_pt)
            content_h_pt = ph_pt - (mt_pt + mb_pt)

            with st.spinner("Generando vista previa..."):
                rotated_img_prev = auto_rotate_for_format(user_img, preview_option)
                # DPI bajo para preview rápida
                composed_prev = compose_template_hd(rotated_img_prev, colz, rowz, content_w_pt, content_h_pt, target_dpi=72)
                
                preview_viz = draw_preview_image(
                    composed_prev, pw_cm, ph_cm, ml_cm, mr_cm, mt_cm, mb_cm, colz, rowz
                )

            with col_preview:
                st.image(preview_viz, caption=f"Vista previa de impresión: {preview_option}", use_container_width=True)

            st.divider()
            st.subheader("⬇️ Descargar Archivos de Impresión")
            st.write("Los archivos se generan a **300 DPI (Alta Calidad)**.")

            # Columnas para botones de descarga
            c1, c2, c3 = st.columns(3)

            # Botón 1: Súper A3
            with c1:
                if st.button("Generar Súper A3"):
                    with st.spinner("Procesando Súper A3 HD..."):
                        p_conf = get_config("Súper A3 (9×3=27)")
                        # Desempaquetar
                        (pw, ph, ml, mr, mt, mb, c, r) = p_conf
                        
                        # Recalcular pt necesarios
                        pw_p = pw*CM_TO_PT; ph_p = ph*CM_TO_PT
                        cw_p = pw_p - (ml+mr)*CM_TO_PT
                        ch_p = ph_p - (mt+mb)*CM_TO_PT
                        
                        rot = auto_rotate_for_format(user_img, "Súper A3")
                        # 300 DPI CRÍTICO PARA CALIDAD
                        comp = compose_template_hd(rot, c, r, cw_p, ch_p, target_dpi=300)
                        pdf_bytes = create_pdf(comp, pw, ph, ml, mr, mt, mb, c, r, target_dpi=300)
                        
                        st.download_button(
                            "💾 Guardar PDF Súper A3",
                            data=pdf_bytes,
                            file_name="tarjetas_superA3_300dpi.pdf",
                            mime="application/pdf"
                        )
                        st.success("¡Listo!")

            # Botón 2: A3
            with c2:
                if st.button("Generar A3"):
                    with st.spinner("Procesando A3 HD..."):
                        p_conf = get_config("A3 (8×3=24)")
                        (pw, ph, ml, mr, mt, mb, c, r) = p_conf
                        
                        pw_p = pw*CM_TO_PT; ph_p = ph*CM_TO_PT
                        cw_p = pw_p - (ml+mr)*CM_TO_PT
                        ch_p = ph_p - (mt+mb)*CM_TO_PT
                        
                        rot = auto_rotate_for_format(user_img, "A3")
                        comp = compose_template_hd(rot, c, r, cw_p, ch_p, target_dpi=300)
                        pdf_bytes = create_pdf(comp, pw, ph, ml, mr, mt, mb, c, r, target_dpi=300)
                        
                        st.download_button(
                            "💾 Guardar PDF A3",
                            data=pdf_bytes,
                            file_name="tarjetas_A3_300dpi.pdf",
                            mime="application/pdf"
                        )
                        st.success("¡Listo!")

            # Botón 3: A4
            with c3:
                if st.button("Generar A4"):
                    with st.spinner("Procesando A4 HD..."):
                        p_conf = get_config("A4 (3×4=12)")
                        (pw, ph, ml, mr, mt, mb, c, r) = p_conf
                        
                        pw_p = pw*CM_TO_PT; ph_p = ph*CM_TO_PT
                        cw_p = pw_p - (ml+mr)*CM_TO_PT
                        ch_p = ph_p - (mt+mb)*CM_TO_PT
                        
                        rot = auto_rotate_for_format(user_img, "A4")
                        comp = compose_template_hd(rot, c, r, cw_p, ch_p, target_dpi=300)
                        pdf_bytes = create_pdf(comp, pw, ph, ml, mr, mt, mb, c, r, target_dpi=300)
                        
                        st.download_button(
                            "💾 Guardar PDF A4",
                            data=pdf_bytes,
                            file_name="tarjetas_A4_300dpi.pdf",
                            mime="application/pdf"
                        )
                        st.success("¡Listo!")

        except Exception as err:
            st.error(f"❌ Ocurrió un error inesperado: {err}")
            st.exception(err)

if __name__ == "__main__":
    main()
