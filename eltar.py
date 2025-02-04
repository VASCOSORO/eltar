import streamlit as st
from PIL import Image, ImageOps, ImageDraw
from fpdf import FPDF
import io
import os

CM_TO_PT = 28.3465  # Conversión de cm a puntos

def adjust_image(image, size):
    """Ajusta 'image' para que encaje exactamente en 'size' (width, height), manteniendo proporción."""
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, cols, rows, rotate=False):
    """
    Carga 'tarjetas.png', la divide en (cols x rows) y pega 'user_image' en cada hueco.
    Devuelve la imagen compuesta (modo RGBA).
    """
    template = Image.open(template_path).convert("RGBA")
    if rotate:
        user_image = user_image.rotate(90, expand=True)

    t_w, t_h = template.size
    card_w = t_w / cols
    card_h = t_h / rows

    composed = template.copy()
    for r in range(rows):
        for c in range(cols):
            x = int(c * card_w)
            y = int(r * card_h)
            adjusted_img = adjust_image(user_image, (int(card_w), int(card_h)))
            composed.paste(adjusted_img, (x, y))

    return composed

def draw_preview_image(
    composed_image,
    page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows
):
    """
    Genera una imagen PIL (vista previa) con la hoja en blanco
    y la 'composed_image' centrada y escalada para que quepa.
    Dibuja las mismas líneas de corte y márgenes en rojo.
    """
    # Convertimos cm → pt
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    # Creamos la "hoja" en blanco
    page_w_px = int(round(pw_pt))
    page_h_px = int(round(ph_pt))
    preview = Image.new("RGB", (page_w_px, page_h_px), color="white")
    draw = ImageDraw.Draw(preview)

    # Medidas de la imagen compuesta
    c_w, c_h = composed_image.size

    # Área útil (en pt)
    content_w_pt = pw_pt - (ml_pt + mr_pt)
    content_h_pt = ph_pt - (mt_pt + mb_pt)

    # Escalamos para que quepa
    scale = min(content_w_pt / c_w, content_h_pt / c_h)
    final_w = c_w * scale
    final_h = c_h * scale

    x_pos = ml_pt + (content_w_pt - final_w) / 2
    y_pos = mt_pt + (content_h_pt - final_h) / 2

    # Redondeamos a píxeles
    x_pos_px = int(round(x_pos))
    y_pos_px = int(round(y_pos))
    final_w_px = int(round(final_w))
    final_h_px = int(round(final_h))

    # Reescalamos la compuesta
    scaled = composed_image.resize((final_w_px, final_h_px), Image.LANCZOS)
    # Pegamos en la hoja en blanco
    preview.paste(scaled, (x_pos_px, y_pos_px))

    # Dibujamos líneas en rojo
    color = (255, 0, 0)
    lw = 1

    x_right = x_pos_px + final_w_px
    y_bottom = y_pos_px + final_h_px

    # 1) Marco externo
    # Izquierda
    draw.line([(x_pos_px, 0), (x_pos_px, y_pos_px)], fill=color, width=lw)
    draw.line([(x_pos_px, y_bottom), (x_pos_px, page_h_px)], fill=color, width=lw)
    # Derecha
    draw.line([(x_right, 0), (x_right, y_pos_px)], fill=color, width=lw)
    draw.line([(x_right, y_bottom), (x_right, page_h_px)], fill=color, width=lw)
    # Superior
    draw.line([(0, y_pos_px), (x_pos_px, y_pos_px)], fill=color, width=lw)
    draw.line([(x_right, y_pos_px), (page_w_px, y_pos_px)], fill=color, width=lw)
    # Inferior
    draw.line([(0, y_bottom), (x_pos_px, y_bottom)], fill=color, width=lw)
    draw.line([(x_right, y_bottom), (page_w_px, y_bottom)], fill=color, width=lw)

    # 2) Columnas internas
    for col in range(1, cols):
        x_col = x_pos_px + int(round(col * final_w_px / cols))
        draw.line([(x_col, 0), (x_col, y_pos_px)], fill=color, width=lw)
        draw.line([(x_col, y_bottom), (x_col, page_h_px)], fill=color, width=lw)

    # 3) Filas internas
    for row in range(1, rows):
        y_row = y_pos_px + int(round(row * final_w_px / rows))
        draw.line([(0, y_row), (x_pos_px, y_row)], fill=color, width=lw)
        draw.line([(x_right, y_row), (page_w_px, y_row)], fill=color, width=lw)

    return preview

def create_pdf(
    composed_image,
    page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows
):
    """
    Genera el PDF final con FPDF, dibujando las mismas líneas rojas en el margen.
    """
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    # Guardamos la imagen compuesta temporal
    temp_path = "temp_comp.jpg"
    composed_image.convert("RGB").save(temp_path, "JPEG", quality=100)

    c_w, c_h = composed_image.size
    cw_pt = pw_pt - (ml_pt + mr_pt)
    ch_pt = ph_pt - (mt_pt + mb_cm)
    scale = min(cw_pt / c_w, ch_pt / c_h)

    final_w = c_w * scale
    final_h = c_h * scale
    x_pos = ml_pt + (cw_pt - final_w) / 2
    y_pos = mt_pt + (ch_pt - final_h) / 2

    pdf = FPDF(unit="pt", format=[pw_pt, ph_pt])
    pdf.add_page()
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    # Líneas rojas
    pdf.set_draw_color(255, 0, 0)
    pdf.set_line_width(0.5)

    xr = x_pos + final_w
    yb = y_pos + final_h

    # Marco externo
    # Izq
    pdf.line(x_pos, 0, x_pos, y_pos)
    pdf.line(x_pos, yb, x_pos, ph_pt)
    # Der
    pdf.line(xr, 0, xr, y_pos)
    pdf.line(xr, yb, xr, ph_pt)
    # Sup
    pdf.line(0, y_pos, x_pos, y_pos)
    pdf.line(xr, y_pos, pw_pt, y_pos)
    # Inf
    pdf.line(0, yb, x_pos, yb)
    pdf.line(xr, yb, pw_pt, yb)

    # Cols internas
    for col in range(1, cols):
        x_col = x_pos + (col * final_w / cols)
        pdf.line(x_col, 0, x_col, y_pos)
        pdf.line(x_col, yb, x_col, ph_pt)

    # Filas internas
    for row in range(1, rows):
        y_row = y_pos + (row * final_h / rows)
        pdf.line(0, y_row, x_pos, y_row)
        pdf.line(xr, y_row, pw_pt, y_row)

    pdf_str = pdf.output(dest="S")
    pdf_bytes = pdf_str.encode("latin-1")

    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

def main():
    st.title("Diferentes formatos y cantidades de tarjetas")
    st.markdown(
        "- **Súper A3 (47,5×32,5 cm)** → 9×3 = 27 tarjetas\n"
        "- **A3 (42×29,7 cm)** → 8×3 = 24 tarjetas\n"
        "- **A4 (29,7×21 cm)** → 3×4 = 12 tarjetas\n\n"
        "Cada uno con sus propios márgenes y líneas de corte."
    )

    rotate_image = st.checkbox("Girar imagen 90° a la izquierda", value=False)
    uploaded_file = st.file_uploader("Subí tu imagen", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        try:
            user_image = Image.open(uploaded_file).convert("RGBA")
            template_path = "tarjetas.png"

            # 1) Súper A3 -> 9×3 = 27
            composed_superA3 = compose_template(template_path, user_image, cols=9, rows=3, rotate=rotate_image)
            # 2) A3 -> 8×3 = 24
            composed_A3 = compose_template(template_path, user_image, cols=8, rows=3, rotate=rotate_image)
            # 3) A4 -> 3×4 = 12
            composed_A4 = compose_template(template_path, user_image, cols=3, rows=4, rotate=rotate_image)

            # Vista previa (select)
            preview_choice = st.selectbox(
                "¿Qué formato querés ver en la vista previa?",
                ["Súper A3 (9×3=27)", "A3 (8×3=24)", "A4 (3×4=12)"]
            )

            if preview_choice == "Súper A3 (9×3=27)":
                # 47,5×32,5 cm, márgenes 1 / 2,57
                pre = draw_preview_image(
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
                st.image(pre, "Vista previa: Súper A3 (27)")

            elif preview_choice == "A3 (8×3=24)":
                # 42×29,7 cm, márgenes 1 cm
                pre = draw_preview_image(
                    composed_A3,
                    page_w_cm=42.0,
                    page_h_cm=29.7,
                    ml_cm=1.0,
                    mr_cm=1.0,
                    mt_cm=1.0,
                    mb_cm=1.0,
                    cols=8,
                    rows=3
                )
                st.image(pre, "Vista previa: A3 (24)")

            else:  # "A4 (3×4=12)"
                # 29,7×21 cm, márgenes 1 cm
                pre = draw_preview_image(
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
                st.image(pre, "Vista previa: A4 (12)")

            st.write("---")
            st.write("**Descargá el PDF en cualquier tamaño:**")

            # Botón Súper A3
            if st.button("Descargar PDF Súper A3 (27 tarjetas)"):
                pdf_superA3 = create_pdf(
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
                st.download_button(
                    "Descargar Súper A3 PDF",
                    data=pdf_superA3,
                    file_name="tarjetas_superA3_9x3.pdf",
                    mime="application/pdf"
                )

            # Botón A3
            if st.button("Descargar PDF A3 (24 tarjetas)"):
                pdf_a3 = create_pdf(
                    composed_A3,
                    page_w_cm=42.0,
                    page_h_cm=29.7,
                    ml_cm=1.0,
                    mr_cm=1.0,
                    mt_cm=1.0,
                    mb_cm=1.0,
                    cols=8,
                    rows=3
                )
                st.download_button(
                    "Descargar A3 PDF",
                    data=pdf_a3,
                    file_name="tarjetas_A3_8x3.pdf",
                    mime="application/pdf"
                )

            # Botón A4
            if st.button("Descargar PDF A4 (12 tarjetas)"):
                pdf_a4 = create_pdf(
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
                st.download_button(
                    "Descargar A4 PDF",
                    data=pdf_a4,
                    file_name="tarjetas_A4_3x4.pdf",
                    mime="application/pdf"
                )

        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Verificá que esté en el directorio.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()
 
