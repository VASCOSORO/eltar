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

# Zona útil (donde centramos la imagen de la plantilla)
CONTENT_WIDTH_PT = PAGE_WIDTH_PT - 2 * MARGIN_LR_PT
CONTENT_HEIGHT_PT = PAGE_HEIGHT_PT - 2 * MARGIN_TB_PT

def adjust_image(image, size):
    """ Ajusta la imagen (manteniendo relación de aspecto) al size deseado. """
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, rotate=False):
    """
    Carga la plantilla, pega la imagen en una grilla 9x3 y devuelve
    la imagen compuesta final (en modo RGBA).
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
    Crea un PDF (47,5 x 32,5 cm horizontales) con:
      - Márgenes: 1 cm izq/der, 2,57 cm sup/inf
      - Imagen compuesta centrada
      - Líneas de corte para cada tarjeta
      - Regla desde el centro (0) hacia los bordes
    Devuelve los bytes del PDF listo para descarga.
    """

    # Guardamos la imagen compuesta temporalmente
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    c_width, c_height = composed_image.size  # En píxeles

    # Factor de escala para que quepa sin deformar dentro de la zona útil
    scale_x = CONTENT_WIDTH_PT / c_width
    scale_y = CONTENT_HEIGHT_PT / c_height
    scale = min(scale_x, scale_y)  # Elegimos el factor menor para no recortar

    final_w = c_width * scale
    final_h = c_height * scale

    # Coordenadas para centrar la imagen compuesta
    x_pos = MARGIN_LR_PT + (CONTENT_WIDTH_PT - final_w) / 2
    y_pos = MARGIN_TB_PT + (CONTENT_HEIGHT_PT - final_h) / 2

    # Creamos PDF con FPDF (en puntos)
    pdf = FPDF(unit="pt", format=[PAGE_WIDTH_PT, PAGE_HEIGHT_PT])
    pdf.add_page()

    # Insertamos la imagen compuesta en la página
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # -----------------------------
    # 1) DIBUJAR LÍNEAS DE CORTE (grilla 9x3)
    # -----------------------------
    pdf.set_draw_color(255, 0, 0)     # Rojo, por ejemplo
    pdf.set_line_width(0.5)          # Grosor de línea

    # Tamaño original de la plantilla
    t_width, t_height = composed_image.size
    cols, rows = 9, 3
    card_w_px = t_width / cols
    card_h_px = t_height / rows

    # Dimensiones en PDF tras escalar
    card_w_pt = card_w_px * scale
    card_h_pt = card_h_px * scale

    # Trazamos líneas verticales
    for c in range(1, cols):
        x_line = x_pos + c * card_w_pt
        pdf.line(x_line, y_pos, x_line, y_pos + final_h)
    
    # Trazamos líneas horizontales
    for r in range(1, rows):
        y_line = y_pos + r * card_h_pt
        pdf.line(x_pos, y_line, x_pos + final_w, y_line)

    # -----------------------------
    # 2) REGLAS DESDE EL CENTRO
    # -----------------------------
    pdf.set_draw_color(0, 0, 255)  # Azul
    pdf.set_line_width(0.2)
    pdf.set_font("Courier", size=8)

    center_x = PAGE_WIDTH_PT / 2
    center_y = PAGE_HEIGHT_PT / 2

    # Línea horizontal principal (centro)
    pdf.line(0, center_y, PAGE_WIDTH_PT, center_y)
    # Línea vertical principal (centro)
    pdf.line(center_x, 0, center_x, PAGE_HEIGHT_PT)

    # Trazamos pequeñas marcas cada 1 cm (aprox)
    max_x_cm = PAGE_WIDTH_CM / 2    # Hacia la derecha e izquierda del centro
    max_y_cm = PAGE_HEIGHT_CM / 2   # Hacia arriba y abajo del centro

    # Horizontal
    for i in range(int(max_x_cm) + 1):
        # Positivo (derecha)
        x_mark_pos = center_x + i * CM_TO_PT
        # Negativo (izquierda)
        x_mark_neg = center_x - i * CM_TO_PT

        # Marcas (pequeñas líneas)
        tick_size = 5  # tamaño de la marca
        pdf.line(x_mark_pos, center_y - tick_size, x_mark_pos, center_y + tick_size)
        pdf.line(x_mark_neg, center_y - tick_size, x_mark_neg, center_y + tick_size)

        # Texto debajo de la línea horizontal
        pdf.text(x_mark_pos + 2, center_y + 15, f"{i}")
        if i != 0:
            pdf.text(x_mark_neg + 2, center_y + 15, f"{-i}")

    # Vertical
    for j in range(int(max_y_cm) + 1):
        y_mark_pos = center_y + j * CM_TO_PT
        y_mark_neg = center_y - j * CM_TO_PT

        # Marcas
        tick_size = 5
        pdf.line(center_x - tick_size, y_mark_pos, center_x + tick_size, y_mark_pos)
        pdf.line(center_x - tick_size, y_mark_neg, center_x + tick_size, y_mark_neg)

        # Texto a la derecha de la línea vertical
        # (desplazamos un poco en x para no pisar la línea)
        pdf.text(center_x + 8, y_mark_pos, f"{-j}")  # abajo es negativo
        if j != 0:
            pdf.text(center_x + 8, y_mark_neg, f"{j}")  # arriba es positivo

    # -----------------------------
    # EXPORTAR PDF
    # -----------------------------
    pdf_str = pdf.output(dest='S')         # PDF como string
    pdf_bytes = pdf_str.encode('latin-1')  # Convertimos a bytes

    # Borramos el archivo temporal
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

def main():
    st.title("Generador de PDF con Reglas y Líneas de Corte")
    st.write("Hoja horizontal 47,5 cm x 32,5 cm, con márgenes y regla desde el centro.")

    rotate_image = st.checkbox("Girar la imagen 90° a la izquierda", value=False)
    uploaded_file = st.file_uploader("Subí tu imagen para la grilla (9x3)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")

            template_path = "tarjetas.png"
            composed_img = compose_template(template_path, user_image, rotate=rotate_image)

            st.image(composed_img, caption="Vista previa de la plantilla + imagen (9x3).", use_column_width=True)

            pdf_bytes = create_pdf(composed_img)
            st.success("¡PDF generado con líneas de corte y regla desde el centro!")
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
