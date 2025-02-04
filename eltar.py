import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

# Conversión de cm a puntos (FPDF usa puntos)
CM_TO_PT = 28.3465

def adjust_image(image, size):
    """
    Ajusta la imagen del usuario a un tamaño específico (ancho, alto),
    manteniendo la relación de aspecto (ImageOps.fit).
    """
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(user_image, cols, rows, rotate=False):
    """
    Carga 'tarjetas.png' (la plantilla base) y pega en ella, en una grilla de (cols x rows),
    la imagen que sube el usuario, sin alterar el tamaño total de la plantilla.
    
    Retorna la imagen compuesta final (modo RGBA).
    """
    # Cargamos la plantilla base
    template = Image.open("tarjetas.png").convert("RGBA")

    if rotate:
        # Rotamos la imagen del usuario si se marcó el checkbox
        user_image = user_image.rotate(90, expand=True)

    # Medidas de la plantilla
    t_width, t_height = template.size

    # Dividimos en 'cols' columnas y 'rows' filas
    card_width = t_width / cols
    card_height = t_height / rows

    # Copiamos la plantilla para no pisarla
    composed = template.copy()

    # Pegamos la imagen en cada "casillero"
    for r in range(rows):
        for c in range(cols):
            x = int(c * card_width)
            y = int(r * card_height)
            # Ajustamos la imagen del usuario al tamaño de cada tarjeta
            adjusted_img = adjust_image(user_image, (int(card_width), int(card_height)))
            composed.paste(adjusted_img, (x, y))

    return composed  # Imagen final RGBA

def create_pdf_no_scale(
    composed_image,
    page_width_cm,
    page_height_cm,
    margin_left_cm,
    margin_right_cm,
    margin_top_cm,
    margin_bottom_cm,
    extend_lines=True
):
    """
    Crea un PDF de tamaño 'page_width_cm' x 'page_height_cm' (en cm), 
    con los márgenes indicados, y *SIN* reescalar la imagen compuesta (1 píxel ~ 1 punto).

    - Si no entra la imagen con esos márgenes, lanza error (no la achica).
    - Dibuja líneas rojas:
        1) un marco externo alrededor de la imagen,
        2) extiende las divisiones de la plantilla hasta los bordes (si extend_lines=True).
    Retorna los bytes del PDF listo para descargar.
    """
    # -- Convertimos medidas de página y márgenes a puntos --
    pw_pt = page_width_cm * CM_TO_PT
    ph_pt = page_height_cm * CM_TO_PT
    ml_pt = margin_left_cm * CM_TO_PT
    mr_pt = margin_right_cm * CM_TO_PT
    mt_pt = margin_top_cm * CM_TO_PT
    mb_pt = margin_bottom_cm * CM_TO_PT

    # Área disponible dentro de los márgenes
    content_w = pw_pt - (ml_pt + mr_pt)
    content_h = ph_pt - (mt_pt + mb_pt)

    # Guardamos la imagen compuesta como JPG temporal
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    # Ancho y alto de la imagen compuesta en píxeles
    c_width, c_height = composed_image.size

    # Suponemos 1 píxel ≈ 1 punto (sin reescalar).
    final_w = c_width
    final_h = c_height

    # Verificamos si entra con los márgenes dados
    if final_w > content_w or final_h > content_h:
        raise ValueError(
            f"La imagen de {final_w}×{final_h} pt no entra "
            f"en la hoja {pw_pt}×{ph_pt} pt con márgenes. "
            "Ajustá márgenes o probá otra configuración."
        )

    # Centramos la imagen en la zona útil
    x_pos = (pw_pt - final_w) / 2
    y_pos = (ph_pt - final_h) / 2

    # Creamos el PDF con FPDF
    pdf = FPDF(unit="pt", format=[pw_pt, ph_pt])
    pdf.add_page()

    # Insertamos la imagen
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Borramos el archivo temporal
    try:
        os.remove(temp_path)
    except OSError:
        pass

    # Dibujamos líneas de corte en rojo
    pdf.set_draw_color(255, 0, 0)
    pdf.set_line_width(0.5)

    # (1) Marco externo alrededor de la imagen
    #      Arriba, abajo, izquierda, derecha
    pdf.line(x_pos, y_pos, x_pos + final_w, y_pos)                       # Arriba
    pdf.line(x_pos, y_pos + final_h, x_pos + final_w, y_pos + final_h)   # Abajo
    pdf.line(x_pos, y_pos, x_pos, y_pos + final_h)                       # Izq
    pdf.line(x_pos + final_w, y_pos, x_pos + final_w, y_pos + final_h)   # Der

    # (2) Extender líneas de la plantilla (grilla) hasta los bordes
    if extend_lines:
        # La plantilla original era 9×3, 3×3, etc. 
        # Deducimos la grilla según la proporción:
        ratio = c_width / c_height
        # Con 9x3 => ratio = 3.0
        # Con 3x3 => ratio = 1.0
        # Ajustamos un poco con tolerancias:
        if abs(ratio - 3.0) < 0.2:   # ~9x3
            cols, rows = 9, 3
        elif abs(ratio - 1.0) < 0.2: # ~3x3
            cols, rows = 3, 3
        else:
            # Por defecto asumimos 9×3
            cols, rows = 9, 3

        # Líneas verticales internas (entre columnas)
        for col in range(1, cols):
            x_col = x_pos + (col * (final_w / cols))
            # Extiende hacia arriba
            pdf.line(x_col, 0, x_col, y_pos)
            # Extiende hacia abajo
            pdf.line(x_col, y_pos + final_h, x_col, ph_pt)

        # Líneas horizontales internas (entre filas)
        for row in range(1, rows):
            y_row = y_pos + (row * (final_h / rows))
            # Extiende a la izquierda
            pdf.line(0, y_row, x_pos, y_row)
            # Extiende a la derecha
            pdf.line(x_pos + final_w, y_row, pw_pt, y_row)

    # Exportamos a bytes en memoria
    pdf_str = pdf.output(dest='S')
    pdf_bytes = pdf_str.encode('latin-1')

    return pdf_bytes

def main():
    st.title("Generador de PDFs con el MISMO tamaño de tarjetas")
    st.markdown(
        "- Usa la **misma plantilla** (`tarjetas.png`) y **no la reescala**.\n"
        "- Crea 3 PDFs:\n"
        "  1) **Súper A3** (47,5 × 32,5 cm), grilla 9×3\n"
        "  2) **A3** (42 × 29,7 cm), grilla 9×3\n"
        "  3) **A4** (29,7 × 21 cm), grilla 3×3\n"
        "Si no entra la imagen en los márgenes indicados, lanza un error."
    )

    # Opcional: rotar la imagen 90° a la izquierda
    rotate_image = st.checkbox("Girar la imagen 90° a la izquierda", value=False)

    # Subida de la imagen que irá en la plantilla
    uploaded_file = st.file_uploader("Subí tu imagen", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            # Cargamos la imagen del usuario
            user_image = Image.open(uploaded_file).convert("RGBA")

            # 1) Componemos para Súper A3 (9×3) => la plantilla se asume 9×3
            composed_super_a3 = compose_template(user_image, cols=9, rows=3, rotate=rotate_image)
            # 2) Componemos para A3 (9×3)
            composed_a3 = compose_template(user_image, cols=9, rows=3, rotate=rotate_image)
            # 3) Componemos para A4 (3×3) - Ejemplo
            composed_a4 = compose_template(user_image, cols=3, rows=3, rotate=rotate_image)

            st.info("Se generaron 3 imágenes compuestas: Súper A3 (9×3), A3 (9×3) y A4 (3×3).")

            # Previsualizamos solo una (la Súper A3) para no saturar la pantalla
            st.image(composed_super_a3, caption="Vista previa (Súper A3, 9×3)", use_column_width=True)

            # Generamos bytes PDF Súper A3
            if st.button("Generar y Descargar PDF Súper A3"):
                try:
                    pdf_super_a3 = create_pdf_no_scale(
                        composed_super_a3,
                        page_width_cm=47.5,
                        page_height_cm=32.5,
                        margin_left_cm=1.0,
                        margin_right_cm=1.0,
                        margin_top_cm=2.57,
                        margin_bottom_cm=2.57,
                        extend_lines=True
                    )
                    st.download_button(
                        label="Descargar Súper A3 PDF",
                        data=pdf_super_a3,
                        file_name="tarjetas_superA3.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generando Súper A3: {e}")

            # Generamos bytes PDF A3
            if st.button("Generar y Descargar PDF A3"):
                try:
                    pdf_a3 = create_pdf_no_scale(
                        composed_a3,
                        page_width_cm=42.0,  # A3 horizontal
                        page_height_cm=29.7,
                        margin_left_cm=0.7,   # márgenes reducidos, ajustalo si querés
                        margin_right_cm=0.7,
                        margin_top_cm=1.0,
                        margin_bottom_cm=1.0,
                        extend_lines=True
                    )
                    st.download_button(
                        label="Descargar A3 PDF",
                        data=pdf_a3,
                        file_name="tarjetas_A3.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generando A3: {e}")

            # Generamos bytes PDF A4 (3×3)
            if st.button("Generar y Descargar PDF A4"):
                try:
                    pdf_a4 = create_pdf_no_scale(
                        composed_a4,
                        page_width_cm=29.7,   # A4 horizontal
                        page_height_cm=21.0,
                        margin_left_cm=1.0,
                        margin_right_cm=1.0,
                        margin_top_cm=1.0,
                        margin_bottom_cm=1.0,
                        extend_lines=True
                    )
                    st.download_button(
                        label="Descargar A4 PDF",
                        data=pdf_a4,
                        file_name="tarjetas_A4.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generando A4: {e}")

        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Asegurate de que esté junto al código.")
        except Exception as err:
            st.error(f"Ocurrió un error: {err}")
