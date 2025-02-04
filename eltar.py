import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

# Conversión cm → pt, para FPDF
CM_TO_PT = 28.3465

def adjust_image(image, size):
    """
    Ajusta la imagen (manteniendo relación de aspecto) 
    exactamente a size (width, height) con ImageOps.fit.
    """
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, cols, rows, rotate=False):
    """
    Carga `template_path` (tarjetas.png), 
    la corta en (cols x rows) y pega user_image en cada “casillero”.

    Retorna la imagen compuesta final en RGBA.
    """
    template = Image.open(template_path).convert("RGBA")

    # Si marcaste girar 90°...
    if rotate:
        user_image = user_image.rotate(90, expand=True)

    # Medidas de la plantilla
    t_width, t_height = template.size

    # Tamaño de cada tarjeta dentro de la plantilla
    card_width = t_width / cols
    card_height = t_height / rows

    # Copiamos la plantilla
    composed = template.copy()

    # Rellenamos cada casillero
    for r in range(rows):
        for c in range(cols):
            x = int(c * card_width)
            y = int(r * card_height)
            adjusted_img = adjust_image(user_image, (int(card_width), int(card_height)))
            composed.paste(adjusted_img, (x, y))

    return composed

def create_pdf_with_lines(
    composed_image,
    page_width_cm,
    page_height_cm,
    margin_left_cm,
    margin_right_cm,
    margin_top_cm,
    margin_bottom_cm,
    cols,
    rows
):
    """
    Crea un PDF con tamaño (page_width_cm x page_height_cm) [en cm],
    con márgenes, centrando la `composed_image`.

    Dibuja:
      - marco externo,
      - extiende líneas de las columnas y filas (cols/rows) hacia los bordes,
      - sin cruzar la imagen, solo en los márgenes.

    Retorna los bytes del PDF.
    """
    pw_pt = page_width_cm * CM_TO_PT
    ph_pt = page_height_cm * CM_TO_PT
    ml_pt = margin_left_cm * CM_TO_PT
    mr_pt = margin_right_cm * CM_TO_PT
    mt_pt = margin_top_cm * CM_TO_PT
    mb_pt = margin_bottom_cm * CM_TO_PT

    # Área disponible dentro de los márgenes
    content_w = pw_pt - (ml_pt + mr_pt)
    content_h = ph_pt - (mt_pt + mb_pt)

    # Guardamos la imagen compuesta temporal
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    # Tamaño de la imagen en píxeles
    c_width, c_height = composed_image.size

    # Escalamos para que quepa en la zona útil
    scale_x = content_w / c_width
    scale_y = content_h / c_height
    scale = min(scale_x, scale_y)

    final_w = c_width * scale
    final_h = c_height * scale

    # Coordenadas para centrar
    x_pos = ml_pt + (content_w - final_w) / 2
    y_pos = mt_pt + (content_h - final_h) / 2

    # Creamos el PDF
    pdf = FPDF(unit="pt", format=[pw_pt, ph_pt])
    pdf.add_page()
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Ajustes de dibujo
    pdf.set_draw_color(255, 0, 0)  # rojo
    pdf.set_line_width(0.5)

    # 1) Marco externo
    # Izquierda
    pdf.line(x_pos, 0, x_pos, y_pos)
    pdf.line(x_pos, y_pos + final_h, x_pos, ph_pt)
    # Derecha
    pdf.line(x_pos + final_w, 0, x_pos + final_w, y_pos)
    pdf.line(x_pos + final_w, y_pos + final_h, x_pos + final_w, ph_pt)
    # Superior
    pdf.line(0, y_pos, x_pos, y_pos)
    pdf.line(x_pos + final_w, y_pos, pw_pt, y_pos)
    # Inferior
    pdf.line(0, y_pos + final_h, x_pos, y_pos + final_h)
    pdf.line(x_pos + final_w, y_pos + final_h, pw_pt, y_pos + final_h)

    # 2) Extensión de líneas de cada columna (cols - 1 internas)
    for col in range(1, cols):
        x_line = x_pos + (col * final_w / cols)
        # Arriba
        pdf.line(x_line, 0, x_line, y_pos)
        # Abajo
        pdf.line(x_line, y_pos + final_h, x_line, ph_pt)

    # 3) Extensión de líneas de cada fila (rows - 1 internas)
    for row in range(1, rows):
        y_line = y_pos + (row * final_h / rows)
        # Izquierda
        pdf.line(0, y_line, x_pos, y_line)
        # Derecha
        pdf.line(x_pos + final_w, y_line, pw_pt, y_line)

    # Exportamos PDF
    pdf_str = pdf.output(dest='S')
    pdf_bytes = pdf_str.encode('latin-1')

    # Borramos temp
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

def main():
    st.title("PDF con diferentes formatos y cantidades de tarjetas")
    st.markdown(
        "- **Súper A3** (47.5 × 32.5 cm), **9×3 = 27 tarjetas**\n"
        "- **A3** (42 × 29.7 cm, horizontal), **4×3 = 12 tarjetas**\n"
        "- **A4** (29.7 × 21 cm, horizontal), **3×4 = 12 tarjetas**\n\n"
        "Se dibujan las líneas de corte y se extienden al margen sin cruzar las imágenes."
    )

    rotate_image = st.checkbox("Girar imagen 90° a la izquierda", value=False)
    uploaded_file = st.file_uploader("Subí tu imagen (se repetirá en la grilla)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")

            # Plantilla base
            template_path = "tarjetas.png"

            # -----------------
            # COMPONEMOS 3 VERSIONES
            # -----------------
            # 1) Súper A3 -> 9x3 (27 tarjetas)
            composed_superA3 = compose_template(
                template_path,
                user_image,
                cols=9,
                rows=3,
                rotate=rotate_image
            )
            # 2) A3 -> 4x3 (12 tarjetas)
            composed_A3 = compose_template(
                template_path,
                user_image,
                cols=4,
                rows=3,
                rotate=rotate_image
            )
            # 3) A4 -> 3x4 (12 tarjetas)
            composed_A4 = compose_template(
                template_path,
                user_image,
                cols=3,
                rows=4,
                rotate=rotate_image
            )

            st.success("¡Listo! Se generaron las imágenes compuestas para Súper A3, A3 y A4.")

            # Previsualizamos una (p.ej. A4) para no saturar
            st.image(composed_A4, caption="Vista previa (A4, 3x4 = 12 tarjetas)", use_column_width=True)

            # ------------
            # BOTONES PDF
            # ------------
            # Botón Súper A3
            if st.button("Descargar PDF Súper A3 (9×3)"):
                pdf_bytes_superA3 = create_pdf_with_lines(
                    composed_image=composed_superA3,
                    page_width_cm=47.5,
                    page_height_cm=32.5,
                    margin_left_cm=1.0,
                    margin_right_cm=1.0,
                    margin_top_cm=2.57,
                    margin_bottom_cm=2.57,
                    cols=9,
                    rows=3
                )
                st.download_button(
                    "Descargar Súper A3 PDF",
                    data=pdf_bytes_superA3,
                    file_name="tarjetas_superA3.pdf",
                    mime="application/pdf"
                )

            # Botón A3
            if st.button("Descargar PDF A3 (4×3)"):
                # Elegimos márgenes (p. ej. 1 cm)
                pdf_bytes_A3 = create_pdf_with_lines(
                    composed_image=composed_A3,
                    page_width_cm=42.0,
                    page_height_cm=29.7,
                    margin_left_cm=1.0,
                    margin_right_cm=1.0,
                    margin_top_cm=1.0,
                    margin_bottom_cm=1.0,
                    cols=4,
                    rows=3
                )
                st.download_button(
                    "Descargar A3 PDF",
                    data=pdf_bytes_A3,
                    file_name="tarjetas_A3.pdf",
                    mime="application/pdf"
                )

            # Botón A4
            if st.button("Descargar PDF A4 (3×4)"):
                pdf_bytes_A4 = create_pdf_with_lines(
                    composed_image=composed_A4,
                    page_width_cm=29.7,
                    page_height_cm=21.0,
                    margin_left_cm=1.0,
                    margin_right_cm=1.0,
                    margin_top_cm=1.0,
                    margin_bottom_cm=1.0,
                    cols=3,
                    rows=4
                )
                st.download_button(
                    "Descargar A4 PDF",
                    data=pdf_bytes_A4,
                    file_name="tarjetas_A4.pdf",
                    mime="application/pdf"
                )

        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Asegurate de que esté en el directorio.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()
