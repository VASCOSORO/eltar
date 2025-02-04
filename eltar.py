import streamlit as st
from PIL import Image, ImageOps, ImageDraw
from fpdf import FPDF
import io
import os

CM_TO_PT = 28.3465

def adjust_image(image, size):
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def auto_rotate_for_format(img, chosen_format):
    """
    Aplica una rotación automática según el formato elegido.
    - Para "Súper A3" y "A3", rota si w>h (buscamos vertical).
    - Para "A4", rota si h>w (buscamos horizontal, por ej.)
    Ajustalo según tu preferencia.
    """
    w, h = img.size

    if chosen_format.startswith("Súper A3") or chosen_format.startswith("A3"):
        # Queremos vertical => rotar si la imagen está apaisada (w>h)
        if w > h:
            return img.rotate(90, expand=True)
        else:
            return img
    else:
        # "A4"
        # Supongamos que queremos horizontal => rotar si es más alta que ancha
        if h > w:
            return img.rotate(90, expand=True)
        else:
            return img

def compose_template(template_path, user_image, cols, rows):
    template = Image.open(template_path).convert("RGBA")
    t_w, t_h = template.size
    card_w = t_w / cols
    card_h = t_h / rows

    composed = template.copy()
    for r in range(rows):
        for c in range(cols):
            x = int(c * card_w)
            y = int(r * card_h)
            adjusted = adjust_image(user_image, (int(card_w), int(card_h)))
            composed.paste(adjusted, (x, y))
    return composed

def draw_preview_image(
    composed_image, page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows
):
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    page_w_px = int(round(pw_pt))
    page_h_px = int(round(ph_pt))

    preview = Image.new("RGB", (page_w_px, page_h_px), "white")
    draw = ImageDraw.Draw(preview)

    c_w, c_h = composed_image.size
    content_w_pt = pw_pt - (ml_pt + mr_pt)
    content_h_pt = ph_pt - (mt_pt + mb_pt)
    scale = min(content_w_pt / c_w, content_h_pt / c_h)
    final_w = c_w * scale
    final_h = c_h * scale

    x_pos = ml_pt + (content_w_pt - final_w) / 2
    y_pos = mt_pt + (content_h_pt - final_h) / 2

    x_pos_px = int(round(x_pos))
    y_pos_px = int(round(y_pos))
    final_w_px = int(round(final_w))
    final_h_px = int(round(final_h))

    scaled = composed_image.resize((final_w_px, final_h_px), Image.LANCZOS)
    preview.paste(scaled, (x_pos_px, y_pos_px))

    color = (255, 0, 0)
    lw = 2
    x_right = x_pos_px + final_w_px
    y_bottom = y_pos_px + final_h_px

    # Marco externo
    draw.line([(x_pos_px, 0), (x_pos_px, y_pos_px)], fill=color, width=lw)
    draw.line([(x_pos_px, y_bottom), (x_pos_px, page_h_px)], fill=color, width=lw)
    draw.line([(x_right, 0), (x_right, y_pos_px)], fill=color, width=lw)
    draw.line([(x_right, y_bottom), (x_right, page_h_px)], fill=color, width=lw)
    draw.line([(0, y_pos_px), (x_pos_px, y_pos_px)], fill=color, width=lw)
    draw.line([(x_right, y_pos_px), (page_w_px, y_pos_px)], fill=color, width=lw)
    draw.line([(0, y_bottom), (x_pos_px, y_bottom)], fill=color, width=lw)
    draw.line([(x_right, y_bottom), (page_w_px, y_bottom)], fill=color, width=lw)

    # Columnas => sup/inf
    for col in range(1, cols):
        x_col = x_pos_px + int(round(col * final_w_px / cols))
        draw.line([(x_col, 0), (x_col, y_pos_px)], fill=color, width=lw)
        draw.line([(x_col, y_bottom), (x_col, page_h_px)], fill=color, width=lw)

    # Filas => izq/der
    for row in range(1, rows):
        y_row = y_pos_px + int(round(row * final_w_px / rows))
        draw.line([(0, y_row), (x_pos_px, y_row)], fill=color, width=lw)
        draw.line([(x_right, y_row), (page_w_px, y_row)], fill=color, width=lw)

    return preview

def create_pdf(
    composed_image, page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows
):
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    temp_path = "temp_comp.jpg"
    composed_image.convert("RGB").save(temp_path, format="JPEG", quality=100)

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
    pdf.image(temp_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

    pdf.set_draw_color(255, 0, 0)
    pdf.set_line_width(0.5)

    xr = x_pos + final_w
    yb = y_pos + final_h

    # Marco
    pdf.line(x_pos, 0, x_pos, y_pos)
    pdf.line(x_pos, yb, x_pos, ph_pt)
    pdf.line(xr, 0, xr, y_pos)
    pdf.line(xr, yb, xr, ph_pt)
    pdf.line(0, y_pos, x_pos, y_pos)
    pdf.line(xr, y_pos, pw_pt, y_pos)
    pdf.line(0, yb, x_pos, yb)
    pdf.line(xr, yb, pw_pt, yb)

    # Cols => sup/inf
    for col in range(1, cols):
        x_col = x_pos + (col * final_w / cols)
        pdf.line(x_col, 0, x_col, y_pos)
        pdf.line(x_col, yb, x_col, ph_pt)

    # Filas => izq/der
    for row in range(1, rows):
        y_row = y_pos + (row * final_h / rows)
        pdf.line(0, y_row, x_pos, y_row)
        pdf.line(xr, y_row, pw_pt, y_row)

    pdf_str = pdf.output(dest="S")
    pdf_bytes = pdf_str.encode("latin-1")

    try:
        os.remove(temp_path)
    except:
        pass
    return pdf_bytes

def get_config(option):
    """
    Devuelve (page_w_cm, page_h_cm, ml_cm, mr_cm, mt_cm, mb_cm, cols, rows)
    según el formato.
    """
    if option == "Súper A3 (9×3=27)":
        return (47.5, 32.5, 1.0, 1.0, 2.57, 2.57, 9, 3)
    elif option == "A3 (8×3=24)":
        return (42.0, 29.7, 1.0, 1.0, 1.0, 1.0, 8, 3)
    else:  # A4 (3×4=12)
        return (29.7, 21.0, 1.0, 1.0, 1.0, 1.0, 3, 4)

def main():
    st.title("Auto-rotación Distinta para A4 vs. A3/Súper A3")
    st.markdown(
        "Según el formato elegido, rotamos la imagen de forma distinta:\n"
        "- **Súper A3 / A3**: Queremos tarjetas verticales → rotamos si w>h.\n"
        "- **A4**: Queremos tarjetas horizontales → rotamos si h>w.\n"
        "Ajustá la lógica a tu preferencia."
    )

    uploaded_file = st.file_uploader("Subí tu imagen", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        try:
            user_img = Image.open(uploaded_file).convert("RGBA")

            template_path = "tarjetas.png"

            # Elegir qué formato querés PREvisualizar (después se generan los 3 PDFs si querés)
            preview_option = st.selectbox(
                "Vista previa de:",
                ["Súper A3 (9×3=27)", "A3 (8×3=24)", "A4 (3×4=12)"]
            )

            # 1) Ajustamos la imagen "automáticamente" según la lógica elegida
            user_img_rotated = auto_rotate_for_format(user_img, preview_option)

            # 2) Componemos la plantilla para esa vista previa
            (pw_cm, ph_cm, ml_cm, mr_cm, mt_cm, mb_cm, colz, rowz) = get_config(preview_option)
            composed_preview = compose_template(template_path, user_img_rotated, colz, rowz)

            # Dibujamos vista previa
            pre_img = draw_preview_image(
                composed_preview,
                page_w_cm=pw_cm,
                page_h_cm=ph_cm,
                ml_cm=ml_cm, mr_cm=mr_cm,
                mt_cm=mt_cm, mb_cm=mb_cm,
                cols=colz, rows=rowz
            )
            st.image(pre_img, caption=f"Vista previa: {preview_option}")

            # ---------------------------
            # Descarga en 3 formatos
            # ---------------------------
            st.write("---")
            st.write("**Descarga en cualquiera de los 3 formatos** (rotando según su propia lógica).")

            # Súper A3
            if st.button("Descargar en Súper A3"):
                # Volvemos a rotar en base a la lógica: w>h => gira
                user_img_sa3 = auto_rotate_for_format(user_img, "Súper A3 (9×3=27)")
                # Componemos
                c_sa3 = compose_template(template_path, user_img_sa3, 9, 3)
                # PDF
                pdf_sa3 = create_pdf(
                    c_sa3,
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
                    data=pdf_sa3,
                    file_name="tarjetas_superA3_9x3.pdf",
                    mime="application/pdf"
                )

            # A3
            if st.button("Descargar en A3"):
                # Volvemos a rotar con la lógica de A3
                user_img_a3 = auto_rotate_for_format(user_img, "A3 (8×3=24)")
                c_a3 = compose_template(template_path, user_img_a3, 8, 3)
                pdf_a3 = create_pdf(
                    c_a3,
                    42.0,
                    29.7,
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                    8,
                    3
                )
                st.download_button(
                    "Descargar A3 PDF",
                    data=pdf_a3,
                    file_name="tarjetas_A3_8x3.pdf",
                    mime="application/pdf"
                )

            # A4
            if st.button("Descargar en A4"):
                # Lógica de A4 => h>w => gira
                user_img_a4 = auto_rotate_for_format(user_img, "A4 (3×4=12)")
                c_a4 = compose_template(template_path, user_img_a4, 3, 4)
                pdf_a4 = create_pdf(
                    c_a4,
                    29.7,
                    21.0,
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                    3,
                    4
                )
                st.download_button(
                    "Descargar A4 PDF",
                    data=pdf_a4,
                    file_name="tarjetas_A4_3x4.pdf",
                    mime="application/pdf"
                )

        except FileNotFoundError:
            st.error("No se encontró 'tarjetas.png'. Verificá que esté en la carpeta.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()
