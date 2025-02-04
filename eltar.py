import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

# Constantes de página y márgenes en cm
PAGE_WIDTH_CM = 32.5
PAGE_HEIGHT_CM = 47.5
MARGIN_LEFT_RIGHT_CM = 1.0
MARGIN_TOP_BOTTOM_CM = 2.57

# Conversión de cm a puntos (FPDF trabaja en puntos)
CM_TO_PT = 28.3465
PAGE_WIDTH_PT = PAGE_WIDTH_CM * CM_TO_PT
PAGE_HEIGHT_PT = PAGE_HEIGHT_CM * CM_TO_PT
MARGIN_LR_PT = MARGIN_LEFT_RIGHT_CM * CM_TO_PT
MARGIN_TB_PT = MARGIN_TOP_BOTTOM_CM * CM_TO_PT

# Área interna disponible (en puntos)
CONTENT_WIDTH_PT = PAGE_WIDTH_PT - (2 * MARGIN_LR_PT)
CONTENT_HEIGHT_PT = PAGE_HEIGHT_PT - (2 * MARGIN_TB_PT)

def adjust_image(image, size):
    """
    Ajusta la imagen a un tamaño específico utilizando ImageOps.fit,
    manteniendo la relación de aspecto.
    """
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, rotate=False):
    """
    Carga la plantilla y la imagen del usuario,
    aplica una grilla 9x3 y devuelve la imagen compuesta.
    """
    # Cargamos la plantilla
    template = Image.open(template_path).convert("RGBA")

    # Rotamos si se solicitó
    if rotate:
        user_image = user_image.rotate(90, expand=True)

    # Definimos la grilla 9x3
    cols, rows = 9, 3
    template_width, template_height = template.size
    card_width = template_width / cols
    card_height = template_height / rows

    # Creamos una copia de la plantilla para pegar
    composed = template.copy()

    # Recorremos la grilla y pegamos la imagen ajustada
    for row in range(rows):
        for col in range(cols):
            x = col * card_width
            y = row * card_height
            adjusted_img = adjust_image(user_image, (int(card_width), int(card_height)))
            composed.paste(adjusted_img, (int(x), int(y)))

    return composed

def create_pdf(composed_image):
    """
    Crea un PDF de 32,5 x 47,5 cm con márgenes solicitados,
    centrando la imagen compuesta en ese espacio.
    Retorna los bytes del PDF listo para descargar.
    """
    # Guardamos la imagen compuesta temporalmente para usarla en FPDF
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    # Obtenemos dimensiones de la imagen compuesta
    c_width, c_height = composed_image.size

    # Calculamos factor de escala para que la imagen complete
    # el área interior (CONTENT_WIDTH_PT x CONTENT_HEIGHT_PT) sin deformar.
    # Recordá que FPDF espera medidas en puntos, PIL está en píxeles.
    # Asumimos que 1 píxel = 1 punto para escalar relativo; o ajustamos a lo ancho/alto.
    # Opcionalmente podés afinar con DPI, pero acá hacemos un ajuste simple.
    scale_x = CONTENT_WIDTH_PT / c_width
    scale_y = CONTENT_HEIGHT_PT / c_height
    scale = min(scale_x, scale_y)

    final_w = c_width * scale
    final_h = c_height * scale

    # Posicionamos la imagen centrada en el área interna
    # Calculamos la coordenada X e Y de inicio
    x_pos = MARGIN_LR_PT + (CONTENT_WIDTH_PT - final_w) / 2
    y_pos = MARGIN_TB_PT + (CONTENT_HEIGHT_PT - final_h) / 2

    # Creamos PDF con el tamaño total en puntos
    pdf = FPDF(unit="pt", format=[PAGE_WIDTH_PT, PAGE_HEIGHT_PT])
    pdf.add_page()

    # Insertamos la imagen compuesta
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Generamos el PDF en memoria
    pdf_str = pdf.output(dest='S')        # PDF en string
    pdf_bytes = pdf_str.encode('latin-1') # Convertimos a bytes

    # Borramos archivo temporal
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

def main():
    st.title("Generador de PDF de Tarjetas (9x3)")
    st.write("Plantilla centrada con márgenes de 1 cm a los costados y 2,57 cm arriba/abajo.")

    # Checkbox para girar la imagen
    rotate_image = st.checkbox("Girar la imagen 90° a la izquierda", value=False)

    # Subida de archivo
    uploaded_file = st.file_uploader("Subí tu imagen", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")
            
            # Armamos la imagen compuesta en memoria
            template_path = "tarjetas.png"
            composed_img = compose_template(template_path, user_image, rotate=rotate_image)

            # Mostramos preview
            st.image(composed_img, caption="Vista previa de la plantilla con tu imagen repetida (9x3)", use_column_width=True)

            # Creamos y descargamos el PDF final
            pdf_bytes = create_pdf(composed_img)
            st.success("¡PDF generado con éxito!")
            st.download_button(
                "Descargar PDF",
                data=pdf_bytes,
                file_name="tarjetas_output.pdf",
                mime="application/pdf"
            )

        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Verificá que esté en el mismo directorio.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()
