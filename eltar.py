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
      - Líneas de corte SOLO en los márgenes (no sobre la imagen)
    Retorna los bytes del PDF listo para descargar.
    """
    # Guardamos la imagen compuesta temporalmente
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    # Tamaño de la imagen en píxeles
    c_width, c_height = composed_image.size

    # Factor de escala para que quepa dentro de la zona útil (respetando proporciones)
    scale_x = CONTENT_WIDTH_PT / c_width
    scale_y = CONTENT_HEIGHT_PT / c_height
    scale = min(scale_x, scale_y)

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
    # DIBUJAR "LÍNEAS DE CORTE" EN LOS MÁRGENES (NO SOBRE LA IMAGEN)
    # -----------------------------
    pdf.set_draw_color(255, 0, 0)     # Rojo
    pdf.set_line_width(0.5)

    # Líneas verticales a la izquierda y derecha, 
    # extendidas solo en la zona de margen superior e inferior.
    # 1) Línea izq: a x = x_pos
    pdf.line(
        x_pos,           # x inicio
        0,               # y inicio (tope de la hoja)
        x_pos,           # x fin
        y_pos            # y fin (donde empieza la imagen)
    )
    pdf.line(
        x_pos,                    # x inicio
        y_pos + final_h,         # donde termina la imagen
        x_pos,                    # x fin
        PAGE_HEIGHT_PT           # hasta el borde inferior
    )
    # 2) Línea der: a x = x_pos + final_w
    pdf.line(
        x_pos + final_w,
        0,
        x_pos + final_w,
        y_pos
    )
    pdf.line(
        x_pos + final_w,
        y_pos + final_h,
        x_pos + final_w,
        PAGE_HEIGHT_PT
    )

    # Líneas horizontales arriba y abajo, en la zona de margen izq/der
    # 3) Línea sup: y = y_pos
    pdf.line(
        0,       # x inicio
        y_pos,   # y
        x_pos,   # x fin (donde empieza la imagen)
        y_pos
    )
    pdf.line(
        x_pos + final_w,
        y_pos,
        PAGE_WIDTH_PT,
        y_pos
    )
    # 4) Línea inf: y = y_pos + final_h
    pdf.line(
        0,
        y_pos + final_h,
        x_pos,
        y_pos + final_h
    )
    pdf.line(
        x_pos + final_w,
        y_pos + final_h,
        PAGE_WIDTH_PT,
        y_pos + final_h
    )

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
    st.title("Generador de PDF Horizontal con Líneas de Corte en Márgenes")
    st.write(
        "Hoja 47,5 cm x 32,5 cm, con 1 cm de margen izq/der y 2,57 cm sup/inf. "
        "Se dibujan líneas de corte en los costados sin cruzar la imagen."
    )

    rotate_image = st.checkbox("Girar la imagen 90° a la izquierda", value=False)
    uploaded_file = st.file_uploader("Subí tu imagen (para la grilla 9x3)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")
            template_path = "tarjetas.png"

            # Componemos la plantilla 9x3
            composed_img = compose_template(template_path, user_image, rotate=rotate_image)
            st.image(composed_img, caption="Vista previa: plantilla + imagen (9x3)", use_column_width=True)

            # Creamos y descargamos el PDF con líneas de corte en los márgenes
            pdf_bytes = create_pdf(composed_img)
            st.success("¡PDF generado con éxito!")
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
