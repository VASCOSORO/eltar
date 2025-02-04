import streamlit as st
from PIL import Image, ImageOps, ImageDraw
from fpdf import FPDF
import io
import os

CM_TO_PT = 28.3465

def adjust_image(image, size):
    """Ajusta 'image' a 'size' (width, height) manteniendo relación de aspecto."""
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, cols, rows, rotate=False):
    """
    Crea una imagen RGBA componiendo 'template_path' (tarjetas.png)
    en (cols x rows) y pega 'user_image' en cada casillero.
    """
    template = Image.open(template_path).convert("RGBA")
    if rotate:
        user_image = user_image.rotate(90, expand=True)

    t_width, t_height = template.size
    card_w = t_width / cols
    card_h = t_height / rows

    composed = template.copy()
    for r in range(rows):
        for c in range(cols):
            x = int(c * card_w)
            y = int(r * card_h)
            adjusted_img = adjust_image(user_image, (int(card_w), int(card_h)))
            composed.paste(adjusted_img, (x, y))

    return composed

def draw_preview_image(composed_image, page_w_cm, page_h_cm, ml_cm, mr_cm, mt_cm, mb_cm, cols, rows):
    """
    Genera una **imagen PIL** (1 punto=1 píxel) con las mismas dimensiones (en puntos)
    que tendría el PDF, dibujando los márgenes y líneas de corte.

    Retorna la imagen PIL con:
      - La 'composed_image' centrada y reescalada
      - Líneas rojas en los bordes y extendidas por las divisiones
    """
    # Convertimos cm → pt
    page_w_pt = page_w_cm * CM_TO_PT
    page_h_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    # Creamos una "hoja" en blanco (RGB) del tamaño total en puntos (redondeamos)
    page_width_px = int(round(page_w_pt))
    page_height_px = int(round(page_h_pt))
    preview = Image.new("RGB", (page_width_px, page_height_px), color="white")

    draw = ImageDraw.Draw(preview)
    c_width, c_height = composed_image.size

    # Calculamos escala para que quepa en content area
    content_w_pt = page_w_pt - (ml_pt + mr_pt)
    content_h_pt = page_h_pt - (mt_pt + mb_cm)
    scale_x = content_w_pt / c_width
    scale_y = content_h_pt / c_height
    scale = min(scale_x, scale_y)

    final_w = c_width * scale
    final_h = c_height * scale

    # Posición (x,y) para centrar
    x_pos = ml_pt + (content_w_pt - final_w) / 2
    y_pos = mt_pt + (content_h_pt - final_h) / 2

    # Redondeamos para indices de píxeles
    x_pos_px = int(round(x_pos))
    y_pos_px = int(round(y_pos))
    final_w_px = int(round(final_w))
    final_h_px = int(round(final_h))

    # Reescalamos la imagen compuesta
    scaled = composed_image.resize((final_w_px, final_h_px), Image.LANCZOS)

    # Pegamos en la "hoja"
    preview.paste(scaled, (x_pos_px, y_pos_px))

    # Dibujamos líneas rojas
    color = (255, 0, 0)
    line_width = 1

    # 1) Marco externo
    # Izq
    draw.line([(x_pos_px, 0), (x_pos_px, y_pos_px)], fill=color, width=line_width)
    draw.line([(x_pos_px, y_pos_px + final_h_px), (x_pos_px, page_height_px)], fill=color, width=line_width)
    # Der
    x_right = x_pos_px + final_w_px
    draw.line([(x_right, 0), (x_right, y_pos_px)], fill=color, width=line_width)
    draw.line([(x_right, y_pos_px + final_h_px), (x_right, page_height_px)], fill=color, width=line_width)
    # Sup
    draw.line([(0, y_pos_px), (x_pos_px, y_pos_px)], fill=color, width=line_width)
    draw.line([(x_right, y_pos_px), (page_width_px, y_pos_px)], fill=color, width=line_width)
    # Inf
    y_bottom = y_pos_px + final_h_px
    draw.line([(0, y_bottom), (x_pos_px, y_bottom)], fill=color, width=line_width)
    draw.line([(x_right, y_bottom), (page_width_px, y_bottom)], fill=color, width=line_width)

    # 2) Extensión vertical (cols)
    for c in range(1, cols):
        x_col = x_pos_px + int(round(c * final_w_px / cols))
        draw.line([(x_col, 0), (x_col, y_pos_px)], fill=color, width=line_width)
        draw.line([(x_col, y_bottom), (x_col, page_height_px)], fill=color, width=line_width)

    # 3) Extensión horizontal (rows)
    for r in range(1, rows):
        y_row = y_pos_px + int(round(r * final_h_px / rows))
        draw.line([(0, y_row), (x_pos_px, y_row)], fill=color, width=line_width)
        draw.line([(x_right, y_row), (page_width_px, y_row)], fill=color, width=line_width)

    return preview

def create_pdf(
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
    Genera el PDF final (con FPDF), dibujando exactamente las mismas líneas
    de corte en los márgenes. Retorna los bytes del PDF.
    """
    # Convertimos cm a pt
    pw_pt = page_width_cm * CM_TO_PT
    ph_pt = page_height_cm * CM_TO_PT
    ml_pt = margin_left_cm * CM_TO_PT
    mr_pt = margin_right_cm * CM_TO_PT
    mt_pt = margin_top_cm * CM_TO_PT
    mb_pt = margin_bottom_cm * CM_TO_PT

    # Guardamos la imagen compuesta
    temp_img = "temp_comp.jpg"
    composed_image.convert("RGB").save(temp_img, format="JPEG", quality=100)

    # Dimension en pix
    c_w, c_h = composed_image.size
    cw_pt = pw_pt - (ml_pt + mr_pt)
    ch_pt = ph_pt - (mt_pt + mb_pt)

    scale = min(cw_pt / c_w, ch_pt / c_h)
    final_w = c_w * scale
    final_h = c_h * scale

    x_pos = ml_pt + (cw_pt - final_w) / 2
    y_pos = mt_pt + (ch_pt - final_h) / 2

    pdf = FPDF(unit="pt", format=[pw_pt, ph_pt])
    pdf.add_page()
    pdf.image(temp_img, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Dibujamos líneas rojas (igual que en draw_preview_image, pero con FPDF)
    pdf.set_draw_color(255, 0, 0)
    pdf.set_line_width(0.5)

    # Marco externo
    # Izq
    pdf.line(x_pos, 0, x_pos, y_pos)
    pdf.line(x_pos, y_pos + final_h, x_pos, ph_pt)
    # Der
    xr = x_pos + final_w
    pdf.line(xr, 0, xr, y_pos)
    pdf.line(xr, y_pos + final_h, xr, ph_pt)
    # Sup
    pdf.line(0, y_pos, x_pos, y_pos)
    pdf.line(xr, y_pos, pw_pt, y_pos)
    # Inf
    yb = y_pos + final_h
    pdf.line(0, yb, x_pos, yb)
    pdf.line(xr, yb, pw_pt, yb)

    # Extensión col
    for c in range(1, cols):
        x_col = x_pos + (c * final_w / cols)
        pdf.line(x_col, 0, x_col, y_pos)
        pdf.line(x_col, yb, x_col, ph_pt)

    # Extensión row
    for r in range(1, rows):
        y_row = y_pos + (r * final_h / rows)
        pdf.line(0, y_row, x_pos, y_row)
        pdf.line(xr, y_row, pw_pt, y_row)

    pdf_str = pdf.output(dest="S")
    pdf_bytes = pdf_str.encode("latin-1")

    try:
        os.remove(temp_img)
    except:
        pass

    return pdf_bytes

def main():
    st.title("Vista Previa con Márgenes + Líneas y Descarga en PDF")
    st.markdown(
        "Subí la imagen a repetir en la plantilla, elegí una vista previa (Súper A3, A3 o A4), y luego "
        "descargá cualquiera de los PDFs (Súper A3, A3, A4). Se dibujan líneas de corte y márgenes."
    )

    rotate_image = st.checkbox("Girar imagen 90° a la izquierda", value=False)
    uploaded_file = st.file_uploader("Subí tu imagen (se repetirá en la grilla)", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")

            # Definimos la plantilla
            template_path = "tarjetas.png"

            # Armamos 3 versiones de la imagen compuesta, con distintas grillas:
            # 1) Súper A3 -> 9×3
            # 2) A3 -> 4×3
            # 3) A4 -> 3×4
            composed_superA3 = compose_template(template_path, user_image, cols=9, rows=3, rotate=rotate_image)
            composed_A3 = compose_template(template_path, user_image, cols=4, rows=3, rotate=rotate_image)
            composed_A4 = compose_template(template_path, user_image, cols=3, rows=4, rotate=rotate_image)

            # Seleccionamos una vista previa
            preview_option = st.selectbox(
                "¿Qué tamaño querés visualizar?",
                ["Súper A3 (9×3)", "A3 (4×3)", "A4 (3×4)"]
            )

            # Según la opción, dibujamos la vista previa
            if preview_option == "Súper A3 (9×3)":
                # Hoja 47.5×32.5, márgenes 1 & 2.57, grilla 9×3
                preview_img = draw_preview_image(
                    composed_superA3,
                    page_w_cm=47.5,
                    page_h_cm=32.5,
                    ml_cm=1.0,
                    mr_cm=1.0,
                    mt_cm=2.57,
                    mb_cm=2.57,
                    cols=9,
                    rows=3
                )
                st.image(preview_img, caption="Vista previa: Súper A3 (9×3)", use_column_width=True)

            elif preview_option == "A3 (4×3)":
                # A3 horizontal: 42×29.7, márgenes 1, grilla 4×3
                preview_img = draw_preview_image(
                    composed_A3,
                    page_w_cm=42.0,
                    page_h_cm=29.7,
                    ml_cm=1.0,
                    mr_cm=1.0,
                    mt_cm=1.0,
                    mb_cm=1.0,
                    cols=4,
                    rows=3
                )
                st.image(preview_img, caption="Vista previa: A3 (4×3)", use_column_width=True)

            else:  # "A4 (3×4)"
                preview_img = draw_preview_image(
                    composed_A4,
                    page_w_cm=29.7,
                    page_h_cm=21.0,
                    ml_cm=1.0,
                    mr_cm=1.0,
                    mt_cm=1.0,
                    mb_cm=1.0,
                    cols=3,
                    rows=4
                )
                st.image(preview_img, caption="Vista previa: A4 (3×4)", use_column_width=True)

            # ----------------------------------------------------------------
            # BOTONES PARA DESCARGAR EN CADA FORMATO
            # ----------------------------------------------------------------
            st.write("**Descargá tu PDF en alguno de los 3 formatos:**")

            # Súper A3
            if st.button("Descargar PDF Súper A3 (9×3)"):
                pdf_bytes = create_pdf(
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
                    data=pdf_bytes,
                    file_name="tarjetas_superA3.pdf",
                    mime="application/pdf"
                )

            # A3
            if st.button("Descargar PDF A3 (4×3)"):
                pdf_bytes = create_pdf(
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
                    data=pdf_bytes,
                    file_name="tarjetas_A3.pdf",
                    mime="application/pdf"
                )

            # A4
            if st.button("Descargar PDF A4 (3×4)"):
                pdf_bytes = create_pdf(
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
                    data=pdf_bytes,
                    file_name="tarjetas_A4.pdf",
                    mime="application/pdf"
                )

        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Ponela en el directorio.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()
