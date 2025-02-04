import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

# ---------------------------------
# PARÁMETROS DE PÁGINA Y MÁRGENES
# ---------------------------------
PAGE_WIDTH_CM = 47.5  # Hoja horizontal
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
    """Ajusta la imagen (manteniendo relación de aspecto) al size deseado."""
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, rotate=False):
    """
    Carga la plantilla, pega la imagen en la grilla 9x3 y devuelve
    la imagen compuesta final (RGBA).
    """
    template = Image.open(template_path).convert("RGBA")
    if rotate:
        user_image = user_image.rotate(90, expand=True)

    # Grilla 9x3
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
    Genera el PDF (47,5x32,5 cm) con:
      - Márgenes: 1 cm izq/der, 2,57 cm sup/inf
      - Grilla 9x3 centrada sin líneas encima
      - Extiende los límites de cada columna/fila hacia los márgenes
      - Mantiene líneas en los bordes de la imagen
    Retorna los bytes del PDF listo.
    """
    # Guardamos la imagen compuesta temporalmente
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    # Dimensiones de la imagen en píxeles
    c_width, c_height = composed_image.size

    # Escalamos para que quepa en la zona útil
    scale_x = CONTENT_WIDTH_PT / c_width
    scale_y = CONTENT_HEIGHT_PT / c_height
    scale = min(scale_x, scale_y)

    final_w = c_width * scale
    final_h = c_height * scale

    # Coordenadas para centrar
    x_pos = MARGIN_LR_PT + (CONTENT_WIDTH_PT - final_w) / 2
    y_pos = MARGIN_TB_PT + (CONTENT_HEIGHT_PT - final_h) / 2

    pdf = FPDF(unit="pt", format=[PAGE_WIDTH_PT, PAGE_HEIGHT_PT])
    pdf.add_page()
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Ajustamos estilos para las líneas
    pdf.set_draw_color(255, 0, 0)  # Rojo
    pdf.set_line_width(0.5)

    # -----------------------------
    # 1) Líneas del marco externo
    # -----------------------------
    # Izquierda
    pdf.line(x_pos, 0, x_pos, y_pos)
    pdf.line(x_pos, y_pos + final_h, x_pos, PAGE_HEIGHT_PT)
    # Derecha
    pdf.line(x_pos + final_w, 0, x_pos + final_w, y_pos)
    pdf.line(x_pos + final_w, y_pos + final_h, x_pos + final_w, PAGE_HEIGHT_PT)
    # Superior
    pdf.line(0, y_pos, x_pos, y_pos)
    pdf.line(x_pos + final_w, y_pos, PAGE_WIDTH_PT, y_pos)
    # Inferior
    pdf.line(0, y_pos + final_h, x_pos, y_pos + final_h)
    pdf.line(x_pos + final_w, y_pos + final_h, PAGE_WIDTH_PT, y_pos + final_h)

    # -----------------------------
    # 2) Extensión de líneas de cada columna hacia márgenes
    #    (8 líneas verticales para las 9 columnas)
    # -----------------------------
    cols, rows = 9, 3
    for col in range(1, cols):  # col=1..8
        # x dentro de la imagen
        x_line = x_pos + (col * final_w / cols)
        # Extiende hacia arriba
        pdf.line(x_line, 0, x_line, y_pos)
        # Extiende hacia abajo
        pdf.line(x_line, y_pos + final_h, x_line, PAGE_HEIGHT_PT)

    # -----------------------------
    # 3) Extensión de líneas de cada fila hacia márgenes
    #    (2 líneas horizontales para las 3 filas)
    # -----------------------------
    for row in range(1, rows):  # row=1..2
        # y dentro de la imagen
        y_line = y_pos + (row * final_h / rows)
        # Extiende a la izquierda
        pdf.line(0, y_line, x_pos, y_line)
        # Extiende a la derecha
        pdf.line(x_pos + final_w, y_line, PAGE_WIDTH_PT, y_line)

    # Generamos PDF en memoria
    pdf_str = pdf.output(dest='S')
    pdf_bytes = pdf_str.encode('latin-1')

    # Borramos el archivo temporal
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

def main():
    st.title("Grilla 9×3 con Líneas de Corte Extendidas a los Márgenes")
    st.write(
        "Hoja horizontal 47,5×32,5 cm, con márgenes 1 cm izq/der y 2,57 cm sup/inf.\n"
        "Se dibujan líneas externas y se extienden las divisiones de la grilla hacia los bordes sin tapar las tarjetas."
    )

    rotate_image = st.checkbox("Girar imagen 90° a la izquierda", value=False)
    uploaded_file = st.file_uploader("Subí tu imagen (para la grilla 9×3)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")
            template_path = "tarjetas.png"

            composed_img = compose_template(template_path, user_image, rotate=rotate_image)
            st.image(composed_img, caption="Vista previa de la plantilla + imagen.", use_column_width=True)

            pdf_bytes = create_pdf(composed_img)
            st.success("¡PDF generado con líneas extendidas en los márgenes!")
            st.download_button(
                "Descargar PDF",
                data=pdf_bytes,
                file_name="tarjetas_output.pdf",
                mime="application/pdf"
            )
        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Verificá que esté en el directorio.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()
