import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

# Conversión de cm a pt (FPDF usa puntos)
CM_TO_PT = 28.3465

def adjust_image(image, size):
    """
    Ajusta la imagen a un tamaño específico (tupla width, height) 
    manteniendo la relación de aspecto via ImageOps.fit.
    """
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(user_image, cols, rows, rotate=False):
    """
    Genera la imagen compuesta en RGBA, de tamaño exacto para la grilla (cols x rows),
    usando "tarjetas.png" como plantilla base.
    No reescala la plantilla resultante: cada tarjeta queda del tamaño original.
    """
    # Cargamos plantilla base
    template = Image.open("tarjetas.png").convert("RGBA")

    # Si se marcó rotación
    if rotate:
        user_image = user_image.rotate(90, expand=True)

    # Ancho y alto de la plantilla
    t_width, t_height = template.size
    # Asumimos que la plantilla ya está pensada para cols x rows
    card_width = t_width / cols
    card_height = t_height / rows

    # Creamos copia para pegar las imágenes
    composed = template.copy()
    for r in range(rows):
        for c in range(cols):
            x = int(c * card_width)
            y = int(r * card_height)
            # Ajustamos la imagen subida al tamaño exacto de cada "hueco"
            adjusted_img = adjust_image(user_image, (int(card_width), int(card_height)))
            composed.paste(adjusted_img, (x, y))

    return composed  # RGBA

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
    Crea un PDF sin reescalar la imagen compuesta (1:1) y la ubica centrada si sobra espacio.
    Dibuja líneas de corte:
      - Un “marco” alrededor de la imagen.
      - Extiende las divisiones de la grilla hacia los márgenes (si extend_lines=True).
    Retorna los bytes del PDF.
    """
    # Convertimos medidas de la página y márgenes a puntos
    pw_pt = page_width_cm * CM_TO_PT
    ph_pt = page_height_cm * CM_TO_PT
    ml_pt = margin_left_cm * CM_TO_PT
    mr_pt = margin_right_cm * CM_TO_PT
    mt_pt = margin_top_cm * CM_TO_PT
    mb_pt = margin_bottom_cm * CM_TO_PT

    # Área disponible
    content_w = pw_pt - (ml_pt + mr_pt)
    content_h = ph_pt - (mt_pt + mb_pt)

    # Guardamos la imagen compuesta en disco temporal, para que FPDF pueda usarla
    temp_path = "temp_composed.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

    # Tamaño de la imagen en píxeles
    c_width, c_height = composed_image.size

    # == PASO 1: Verificar que 1:1 (en puntos) quepa en la página con márgenes ==
    # Suponemos 1 píxel ~ 1 punto (no lo escalamos). 
    # Si no entra, se avisa (o podrías recortar márgenes si deseás).
    final_w = c_width
    final_h = c_height

    if final_w > content_w or final_h > content_h:
        # Si no entra, avisamos. Podrías forzar “sin margen” o similar.
        raise ValueError("La imagen (tarjetas) no entra en la página con esos márgenes sin escalar.")

    # == PASO 2: Calcular x,y para centrarla dentro del área content ==
    x_pos = (pw_pt - final_w) / 2
    y_pos = (ph_pt - final_h) / 2

    # Creamos el PDF
    pdf = FPDF(unit="pt", format=[pw_pt, ph_pt])
    pdf.add_page()
    # Insertamos la imagen al 100%
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Dibujamos líneas de corte en rojo
    pdf.set_draw_color(255, 0, 0)
    pdf.set_line_width(0.5)

    # 1) Marco externo alrededor de la imagen
    #    (arriba, abajo, izquierda, derecha)
    pdf.line(x_pos, y_pos, x_pos + final_w, y_pos)  # Arriba
    pdf.line(x_pos, y_pos + final_h, x_pos + final_w, y_pos + final_h)  # Abajo
    pdf.line(x_pos, y_pos, x_pos, y_pos + final_h)  # Izq
    pdf.line(x_pos + final_w, y_pos, x_pos + final_w, y_pos + final_h)  # Der

    # 2) Extender líneas de división de la grilla hacia márgenes (si la plantilla es 9x3 o la que sea)
    if extend_lines:
        # Sacamos cuántas columnas/filas tenía la imagen (p.ej. 9x3).
        # Lo sabemos si la "plantilla" se dividía en cols, rows, 
        # pero aquí podemos deducirlo en píxeles:
        #   - ancho total = c_width
        #   - col_width = c_width / cols
        #   => cols = c_width / col_width
        # Sin “metadatos” directos, suponemos 9x3 para “Super A3” y “A3”,
        # o 3x3 para “A4”, etc. Podés guardarlo como un arg o manejarlo según convenga.
        # Acá haremos un truco: detectamos la proporción.
        # Para simplificar, asume que la plantilla es 9x3 siempre, salvo si no da la proporción.
        # O definimos manualmente según tamaño de la imagen.
        # - ancho vs alto ~ 3 veces => decimos 3x3
        # - ancho vs alto ~ 9x3 => decimos 9x3
        # etc. ¡Depende de tu template real!
        ratio = c_width / c_height
        # Aproximamos
        if abs(ratio - 3) < 0.2:
            cols, rows = 3, 3
        else:
            # Por defecto 9 x 3
            cols, rows = 9, 3

        # Líneas verticales internas
        for col in range(1, cols):
            x_col = x_pos + (col * (final_w / cols))
            # Extiende desde el borde superior de la página hasta la imagen,
            # y desde el borde inferior de la imagen hasta el final de la página
            pdf.line(x_col, 0, x_col, y_pos)
            pdf.line(x_col, y_pos + final_h, x_col, ph_pt)

        # Líneas horizontales internas
        for row in range(1, rows):
            y_row = y_pos + (row * (final_h / rows))
            pdf.line(0, y_row, x_pos, y_row)
            pdf.line(x_pos + final_w, y_row, pw_pt, y_row)

    # Exportamos a bytes en memoria
    pdf_str = pdf.output(dest='S')
    pdf_bytes = pdf_str.encode('latin-1')

    # Borramos archivo temporal
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

def main():
    st.title("Generador de PDFs con el MISMO tamaño de tarjeta")

    st.write(
        "Este script crea tres PDFs:\n\n"
        "- **Súper A3** (47.5×32.5 cm) con grilla de 9×3, márgenes amplios.\n"
        "- **A3** (42×29.7 cm, horizontal) con la misma grilla 9×3, márgenes reducidos.\n"
        "- **A4** (29.7×21 cm, horizontal) con grilla 3×3 para que quepan las mismas tarjetas sin reescalar.\n"
        "\n"
        "Si no entra la imagen con esos márgenes, se mostrará error. Podés ajustar según necesites."
    )

    # Checkbox para girar la imagen
    rotate_image = st.checkbox("Girar la imagen 90° a la izquierda", value=False)

    # Subida de la imagen para las tarjetas
    uploaded_file = st.file_uploader("Subí tu imagen para colocar en las tarjetas", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")

            # 1) Generamos la imagen compuesta para Súper A3 (9×3)
            #    => Hoja 47.5×32.5 (ya usado en ejemplos anteriores)
            super_a3_cols, super_a3_rows = 9, 3
            composed_super_a3 = compose_template(user_image, super_a3_cols, super_a3_rows, rotate=rotate_image)

            # 2) Generamos la imagen compuesta para A3 (igual 9×3), pero hoja 42×29.7
            a3_cols, a3_rows = 9, 3
            composed_a3 = compose_template(user_image, a3_cols, a3_rows, rotate=rotate_image)

            # 3) Generamos la imagen compuesta para A4 (3×3), para que entre sin reducir tamaño de tarjeta
            a4_cols, a4_rows = 3, 3
            composed_a4 = compose_template(user_image, a4_cols, a4_rows, rotate=rotate_image)

            st.write("### Vista previa rápida de la plantilla (Súper A3) 9×3")
            st.image(composed_super_a3, caption="Plantilla 9×3 (Súper A3)", use_column_width=True)

            # Botones de descarga: Súper A3, A3 y A4
            # -- SÚPER A3 --
            if st.button("Descargar PDF Súper A3 (9×3)"):
                try:
                    pdf_bytes_super_a3 = create_pdf_no_scale(
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
                        data=pdf_bytes_super_a3,
                        file_name="tarjetas_superA3.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error al generar PDF Súper A3: {e}")

            # -- A3 --
            if st.button("Descargar PDF A3 (9×3)"):
                try:
                    pdf_bytes_a3 = create_pdf_no_scale(
                        composed_a3,
                        page_width_cm=42,  # A3 horizontal
                        page_height_cm=29.7,
                        margin_left_cm=0.5,  # márgenes más chicos
                        margin_right_cm=0.5,
                        margin_top_cm=1.0,
                        margin_bottom_cm=1.0,
                        extend_lines=True
                    )
                    st.download_button(
                        label="Descargar A3 PDF",
                        data=pdf_bytes_a3,
                        file_name="tarjetas_A3.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error al generar PDF A3: {e}")

            # -- A4 --
            if st.button("Descargar PDF A4 (3×3)"):
                try:
                    pdf_bytes_a4 = create_pdf_no_scale(
                        composed_a4,
                        page_width_cm=29.7,  # A4 horizontal
                        page_height_cm=21.0,
                        margin_left_cm=1.0,
                        margin_right_cm=1.0,
                        margin_top_cm=1.0,
                        margin_bottom_cm=1.0,
                        extend_lines=True
                    )
                    st.download_button(
                        label="Descargar A4 PDF",
                        data=pdf_bytes_a4,
                        file_name="tarjetas_A4.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error al generar PDF A4: {e}")

        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Ponela en el mismo directorio.")
        except Exception as err:
            st.error(f"Ocurrió un error general: {err}")
