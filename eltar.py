import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

# ---------------------------------------------------------
# FUNCIONES PRINCIPALES
# ---------------------------------------------------------

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

def create_pdf(
    composed_image,
    page_width_cm,
    page_height_cm,
    margin_left_right_cm,
    margin_top_bottom_cm
):
    """
    Genera un PDF con el tamaño en cm indicado (horizontal o vertical),
    con márgenes a izquierda/derecha y arriba/abajo.
    Centra la grilla 9x3 sin dibujar líneas encima,
    pero extiende las líneas de corte hacia los márgenes.
    
    Retorna los bytes del PDF listo para descargar.
    """
    # Conversión de cm a puntos
    CM_TO_PT = 28.3465
    
    # Medidas de la página en pt
    page_width_pt = page_width_cm * CM_TO_PT
    page_height_pt = page_height_cm * CM_TO_PT
    
    # Márgenes en pt
    margin_lr_pt = margin_left_right_cm * CM_TO_PT
    margin_tb_pt = margin_top_bottom_cm * CM_TO_PT

    # Zona útil
    content_width_pt = page_width_pt - 2 * margin_lr_pt
    content_height_pt = page_height_pt - 2 * margin_tb_pt

    # Guardamos la imagen compuesta temporalmente
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    # Dimensiones de la imagen en píxeles
    c_width, c_height = composed_image.size

    # Escalamos para que quepa en la zona útil
    scale_x = content_width_pt / c_width
    scale_y = content_height_pt / c_height
    scale = min(scale_x, scale_y)

    final_w = c_width * scale
    final_h = c_height * scale

    # Coordenadas para centrar
    x_pos = margin_lr_pt + (content_width_pt - final_w) / 2
    y_pos = margin_tb_pt + (content_height_pt - final_h) / 2

    # Creamos el PDF
    pdf = FPDF(unit="pt", format=[page_width_pt, page_height_pt])
    pdf.add_page()
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Ajustamos estilos para las líneas
    pdf.set_draw_color(255, 0, 0)  # Rojo
    pdf.set_line_width(0.5)

    # 1) Líneas del marco externo
    pdf.line(x_pos, 0, x_pos, y_pos)  # Izquierda marg sup
    pdf.line(x_pos, y_pos + final_h, x_pos, page_height_pt)  # Izquierda marg inf
    pdf.line(x_pos + final_w, 0, x_pos + final_w, y_pos)  # Derecha marg sup
    pdf.line(x_pos + final_w, y_pos + final_h, x_pos + final_w, page_height_pt)  # Der marg inf
    pdf.line(0, y_pos, x_pos, y_pos)  # Superior marg izq
    pdf.line(x_pos + final_w, y_pos, page_width_pt, y_pos)  # Sup marg der
    pdf.line(0, y_pos + final_h, x_pos, y_pos + final_h)  # Inf marg izq
    pdf.line(x_pos + final_w, y_pos + final_h, page_width_pt, y_pos + final_h)  # Inf marg der

    # 2) Extensión de líneas de cada columna hacia márgenes (8 líneas verticales)
    cols, rows = 9, 3
    for col in range(1, cols):
        x_line = x_pos + (col * final_w / cols)
        pdf.line(x_line, 0, x_line, y_pos)  # arriba
        pdf.line(x_line, y_pos + final_h, x_line, page_height_pt)  # abajo

    # 3) Extensión de líneas de cada fila hacia márgenes (2 líneas horizontales)
    for row in range(1, rows):
        y_line = y_pos + (row * final_h / rows)
        pdf.line(0, y_line, x_pos, y_line)  # izq
        pdf.line(x_pos + final_w, y_line, page_width_pt, y_line)  # der

    # Generamos PDF en memoria
    pdf_str = pdf.output(dest='S')
    pdf_bytes = pdf_str.encode('latin-1')

    # Borramos el archivo temporal
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

# ---------------------------------------------------------
# MAIN STREAMLIT APP
# ---------------------------------------------------------
def main():
    st.title("Grilla 9×3 con Líneas de Corte (Súper A3, A3 y A4)")
    st.write(
        "Esta aplicación te permite generar:\n"
        "- **Súper A3** (47,5×32,5 cm)\n"
        "- **A3** (42×29,7 cm, horizontal)\n"
        "- **A4** (29,7×21 cm, horizontal)\n\n"
        "Se dibujan las líneas externas y se extienden las divisiones de la grilla 9x3 hacia los bordes."
    )

    rotate_image = st.checkbox("Girar imagen 90° a la izquierda", value=False)
    uploaded_file = st.file_uploader("Subí tu imagen (para la grilla 9×3)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")
            template_path = "tarjetas.png"

            composed_img = compose_template(template_path, user_image, rotate=rotate_image)
            st.image(composed_img, caption="Vista previa de la plantilla + imagen (9×3)", use_column_width=True)

            # Botón 1: Súper A3
            if st.button("Generar PDF Súper A3 (47,5×32,5 cm)"):
                try:
                    pdf_bytes_superA3 = create_pdf(
                        composed_img,
                        page_width_cm=47.5,
                        page_height_cm=32.5,
                        margin_left_right_cm=1.0,
                        margin_top_bottom_cm=2.57
                    )
                    st.download_button(
                        "Descargar PDF Súper A3",
                        data=pdf_bytes_superA3,
                        file_name="tarjetas_superA3.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generando PDF Súper A3: {e}")

            # Botón 2: A3
            if st.button("Generar PDF A3 (42×29,7 cm)"):
                try:
                    pdf_bytes_A3 = create_pdf(
                        composed_img,
                        page_width_cm=42.0,  # A3 horizontal
                        page_height_cm=29.7,
                        margin_left_right_cm=1.0,
                        margin_top_bottom_cm=1.5  # Podés ajustar
                    )
                    st.download_button(
                        "Descargar PDF A3",
                        data=pdf_bytes_A3,
                        file_name="tarjetas_A3.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generando PDF A3: {e}")

            # Botón 3: A4
            if st.button("Generar PDF A4 (29,7×21 cm)"):
                try:
                    pdf_bytes_A4 = create_pdf(
                        composed_img,
                        page_width_cm=29.7,  # A4 horizontal
                        page_height_cm=21.0,
                        margin_left_right_cm=1.0,
                        margin_top_bottom_cm=1.0  # Ajustá si lo necesitás
                    )
                    st.download_button(
                        "Descargar PDF A4",
                        data=pdf_bytes_A4,
                        file_name="tarjetas_A4.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generando PDF A4: {e}")

        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Verificá que esté en el directorio.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()
