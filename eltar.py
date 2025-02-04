import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

# -----------------------------
# PARÁMETROS DE PÁGINA Y MÁRGENES
# -----------------------------
PAGE_WIDTH_CM = 47.5    # Hoja horizontal
PAGE_HEIGHT_CM = 32.5
MARGIN_LEFT_RIGHT_CM = 1.0
MARGIN_TOP_BOTTOM_CM = 2.57

CM_TO_PT = 28.3465
PAGE_WIDTH_PT = PAGE_WIDTH_CM * CM_TO_PT
PAGE_HEIGHT_PT = PAGE_HEIGHT_CM * CM_TO_PT
MARGIN_LR_PT = MARGIN_LEFT_RIGHT_CM * CM_TO_PT
MARGIN_TB_PT = MARGIN_TOP_BOTTOM_CM * CM_TO_PT

# Zona útil (donde centramos la imagen)
CONTENT_WIDTH_PT = PAGE_WIDTH_PT - 2 * MARGIN_LR_PT
CONTENT_HEIGHT_PT = PAGE_HEIGHT_PT - 2 * MARGIN_TB_PT

def adjust_image(image, size):
    """ Ajusta la imagen (manteniendo relación de aspecto) al size deseado. """
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, rotate=False):
    """
    Carga la plantilla y la pega en grilla 9x3 con la imagen subida.
    Devuelve la imagen compuesta final (RGBA).
    """
    template = Image.open(template_path).convert("RGBA")
    if rotate:
        user_image = user_image.rotate(90, expand=True)

    cols, rows = 9, 3
    t_width, t_height = template.size
    card_width = t_width / cols
    card_height = t_height / rows

    composed = template.copy()
    for r in range(rows):
        for c in range(cols):
            x = c * card_width
            y = r * card_height
            adjusted_img = adjust_image(user_image, (int(card_width), int(card_height)))
            composed.paste(adjusted_img, (int(x), int(y)))

    return composed

def create_pdf(composed_image):
    """
    Genera el PDF 47,5x32,5 cm, con la imagen centrada y:
      - Líneas en las esquinas (arriba/abajo/izquierda/derecha).
      - 2 líneas adicionales en izq/der.
      - 8 líneas adicionales en sup/inf.
      Sin cruzar la imagen, solo en márgenes.
    Retorna los bytes del PDF.
    """
    # Guardamos la imagen compuesta temporalmente
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    c_width, c_height = composed_image.size  # píxeles

    # Escalamos para que quepa en la zona útil
    scale_x = CONTENT_WIDTH_PT / c_width
    scale_y = CONTENT_HEIGHT_PT / c_height
    scale = min(scale_x, scale_y)
    final_w = c_width * scale
    final_h = c_height * scale

    # Posición para centrar
    x_pos = MARGIN_LR_PT + (CONTENT_WIDTH_PT - final_w) / 2
    y_pos = MARGIN_TB_PT + (CONTENT_HEIGHT_PT - final_h) / 2

    pdf = FPDF(unit="pt", format=[PAGE_WIDTH_PT, PAGE_HEIGHT_PT])
    pdf.add_page()
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Ajustes de dibujo
    pdf.set_draw_color(255, 0, 0)  # Rojo
    pdf.set_line_width(0.5)

    # ============== LÍNEAS ESQUINA (ALREDEDOR DEL RECTÁNGULO DE LA IMAGEN) ==============
    # Izquierda
    pdf.line(x_pos, 0, x_pos, y_pos)                                # Margen superior
    pdf.line(x_pos, y_pos + final_h, x_pos, PAGE_HEIGHT_PT)         # Margen inferior
    # Derecha
    pdf.line(x_pos + final_w, 0, x_pos + final_w, y_pos)
    pdf.line(x_pos + final_w, y_pos + final_h, x_pos + final_w, PAGE_HEIGHT_PT)
    # Superior
    pdf.line(0, y_pos, x_pos, y_pos)
    pdf.line(x_pos + final_w, y_pos, PAGE_WIDTH_PT, y_pos)
    # Inferior
    pdf.line(0, y_pos + final_h, x_pos, y_pos + final_h)
    pdf.line(x_pos + final_w, y_pos + final_h, PAGE_WIDTH_PT, y_pos + final_h)

    # ==================== LÍNEAS EXTRA EN LOS MÁRGENES ====================
    # Querés 2 líneas en izq/der y 8 líneas en sup/inf

    # 1) MARGEN IZQUIERDA (x: 0 -> x_pos)
    #    Trazamos 2 líneas paralelas al eje horizontal, a modo de subdivisiones
    left_margin_width = x_pos
    # Dividimos en (n+1) segmentos → n=2 => 3 segmentos
    n_left = 2
    for i in range(1, n_left + 1):
        # x_line es la línea vertical en la porción  i/(n+1)
        x_line = (i/(n_left+1)) * left_margin_width
        # Arriba
        pdf.line(x_line, 0, x_line, y_pos)
        # Abajo
        pdf.line(x_line, y_pos + final_h, x_line, PAGE_HEIGHT_PT)

    # 2) MARGEN DERECHA (x: x_pos+final_w -> PAGE_WIDTH_PT)
    right_margin_width = PAGE_WIDTH_PT - (x_pos + final_w)
    n_right = 2
    for i in range(1, n_right + 1):
        x_line = x_pos + final_w + (i/(n_right+1)) * right_margin_width
        # Arriba
        pdf.line(x_line, 0, x_line, y_pos)
        # Abajo
        pdf.line(x_line, y_pos + final_h, x_line, PAGE_HEIGHT_PT)

    # 3) MARGEN SUPERIOR (y: 0 -> y_pos)
    top_margin_height = y_pos
    n_top = 8
    for i in range(1, n_top + 1):
        y_line = (i/(n_top+1)) * top_margin_height
        # Izquierda
        pdf.line(0, y_line, x_pos, y_line)
        # Derecha
        pdf.line(x_pos + final_w, y_line, PAGE_WIDTH_PT, y_line)

    # 4) MARGEN INFERIOR (y: y_pos+final_h -> PAGE_HEIGHT_PT)
    bottom_margin_height = PAGE_HEIGHT_PT - (y_pos + final_h)
    n_bottom = 8
    for i in range(1, n_bottom + 1):
        y_line = y_pos + final_h + (i/(n_bottom+1)) * bottom_margin_height
        # Izquierda
        pdf.line(0, y_line, x_pos, y_line)
        # Derecha
        pdf.line(x_pos + final_w, y_line, PAGE_WIDTH_PT, y_line)

    # Exportamos a bytes
    pdf_str = pdf.output(dest='S')
    pdf_bytes = pdf_str.encode('latin-1')

    # Eliminamos archivo temporal
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

def main():
    st.title("PDF Horizontal (47,5×32,5) con Líneas Extra en los Márgenes")
    st.write(
        "- Hoja horizontal (47,5 cm × 32,5 cm)\n"
        "- Márgenes: 1 cm izq/der, 2,57 cm sup/inf\n"
        "- Grilla 9×3 centrada\n"
        "- Líneas exteriores y líneas de subdivisión extra (2 en izq/der, 8 en sup/inf)."
    )

    rotate_image = st.checkbox("Girar imagen 90° a la izquierda", value=False)
    uploaded_file = st.file_uploader("Subí tu imagen (para la grilla 9x3)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")
            template_path = "tarjetas.png"

            # Componemos la plantilla 9x3
            composed_img = compose_template(template_path, user_image, rotate=rotate_image)
            st.image(composed_img, caption="Vista previa: plantilla + imagen", use_column_width=True)

            pdf_bytes = create_pdf(composed_img)
            st.success("¡PDF generado con líneas extra de corte en los márgenes!")
            st.download_button(
                "Descargar PDF",
                data=pdf_bytes,
                file_name="tarjetas_output.pdf",
                mime="application/pdf"
            )
        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Verificá que esté en la carpeta.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()
