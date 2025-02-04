import streamlit as st
from PIL import Image, ImageOps, ImageDraw
from fpdf import FPDF
import io
import os

CM_TO_PT = 28.3465

# ---------------------------
# 1) FUNCIONES DE CORTE
# ---------------------------
def draw_preview_image(
    composed_image,
    page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows
):
    """
    Crea una imagen PIL en blanco (tamaño = hoja en pt),
    pega 'composed_image' escalada y centrada,
    y dibuja líneas “como antes”:
      - columnas en margen sup/inf
      - filas en margen izq/der
    """
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

    # Escalado
    c_w, c_h = composed_image.size
    content_w_pt = pw_pt - (ml_pt + mr_pt)
    content_h_pt = ph_pt - (mt_pt + mb_pt)
    scale = min(content_w_pt / c_w, content_h_pt / c_h)
    final_w = c_w * scale
    final_h = c_h * scale

    x_pos = ml_pt + (content_w_pt - final_w) / 2
    y_pos = mt_pt + (content_h_pt - final_h) / 2

    # Convertir a px para dibujar
    x_pos_px = int(round(x_pos))
    y_pos_px = int(round(y_pos))
    final_w_px = int(round(final_w))
    final_h_px = int(round(final_h))

    # Pegamos la imagen escalada
    scaled = composed_image.resize((final_w_px, final_h_px), Image.LANCZOS)
    preview.paste(scaled, (x_pos_px, y_pos_px))

    color = (255, 0, 0)
    lw = 2
    x_right = x_pos_px + final_w_px
    y_bottom = y_pos_px + final_h_px

    # Marco externo
    # Izq
    draw.line([(x_pos_px, 0), (x_pos_px, y_pos_px)], fill=color, width=lw)
    draw.line([(x_pos_px, y_bottom), (x_pos_px, page_h_px)], fill=color, width=lw)
    # Der
    draw.line([(x_right, 0), (x_right, y_pos_px)], fill=color, width=lw)
    draw.line([(x_right, y_bottom), (x_right, page_h_px)], fill=color, width=lw)
    # Sup
    draw.line([(0, y_pos_px), (x_pos_px, y_pos_px)], fill=color, width=lw)
    draw.line([(x_right, y_pos_px), (page_w_px, y_pos_px)], fill=color, width=lw)
    # Inf
    draw.line([(0, y_bottom), (x_pos_px, y_bottom)], fill=color, width=lw)
    draw.line([(x_right, y_bottom), (page_w_px, y_bottom)], fill=color, width=lw)

    # Columnas => sup/inf
    for col in range(1, cols):
        x_col = x_pos_px + int(round(col * final_w_px / cols))
        draw.line([(x_col, 0), (x_col, y_pos_px)], fill=color, width=lw)
        draw.line([(x_col, y_bottom), (x_col, page_h_px)], fill=color, width=lw)

    # Filas => izq/der
    for row in range(1, rows):
        y_row = y_pos_px + int(round(row * final_h_px / rows))
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
    Genera un PDF con la misma lógica:
      - columnas en sup/inf
      - filas en izq/der
    """
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    temp_path = "temp_comp.jpg"
    composed_image.convert("RGB").save(temp_path, "JPEG", quality=100)

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

    pdf_str = pdf.output(dest='S')
    pdf_bytes = pdf_str.encode('latin-1')

    try:
        os.remove(temp_path)
    except:
        pass
    return pdf_bytes

# ---------------------------
# 2) LÓGICA DE AUTO ROTACIÓN
# ---------------------------
def auto_rotate_for_format(img, chosen_format):
    """
    - Para A3 / Súper A3 => rotar si w>h (vertical)
    - Para A4 => rotar si h>w (horizontal)
    """
    w, h = img.size
    if chosen_format.startswith("Súper A3") or chosen_format.startswith("A3"):
        # vertical
        if w > h:
            return img.rotate(90, expand=True)
        else:
            return img
    else:
        # A4 => horizontal
        if h > w:
            return img.rotate(90, expand=True)
        else:
            return img

# ---------------------------
# 3) COMPOSICIÓN DE LA PLANTILLA
# ---------------------------
def adjust_image(image, size):
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, cols, rows):
    template = Image.open(template_path).convert("RGBA")
    t_w, t_h = template.size
    card_w = t_w / cols
    card_h = t_h / rows
    composed = template.copy()
    for rr in range(rows):
        for cc in range(cols):
            x = int(cc * card_w)
            y = int(rr * card_h)
            piece = adjust_image(user_image, (int(card_w), int(card_h)))
            composed.paste(piece, (x, y))
    return composed

# ---------------------------
# 4) CONFIG DE FORMATOS
# ---------------------------
def get_config(option):
    # Retorna: (width_cm, height_cm, marg_left, marg_right, marg_top, marg_bottom, cols, rows)
    if option == "Súper A3 (9×3=27)":
        return (47.5, 32.5, 1.0, 1.0, 2.57, 2.57, 9, 3)
    elif option == "A3 (8×3=24)":
        return (42.0, 29.7, 1.0, 1.0, 1.0, 1.0, 8, 3)
    else:  # "A4 (3×4=12)"
        return (29.7, 21.0, 1.0, 1.0, 1.0, 1.0, 3, 4)

# ---------------------------
# 5) STREAMLIT MAIN
# ---------------------------
def main():
    st.title("Tarjezor")

    st.write("Subí tu imagen y generá las tarjetas en distintos formatos (Súper A3, A3, A4) con líneas de corte.")

    uploaded_file = st.file_uploader("Subí tu archivo", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        try:
            user_img = Image.open(uploaded_file).convert("RGBA")
            template_path = "tarjetas.png"

            # Selectbox para vista previa
            preview_option = st.selectbox(
                "Elegí la vista previa:",
                ["Súper A3 (9×3=27)", "A3 (8×3=24)", "A4 (3×4=12)"]
            )

            # 1) Rotamos automáticamente según el preview
            rotated_img = auto_rotate_for_format(user_img, preview_option)
            # 2) Componemos la plantilla
            (pw_cm, ph_cm, ml_cm, mr_cm, mt_cm, mb_cm, colz, rowz) = get_config(preview_option)
            composed_prev = compose_template(template_path, rotated_img, colz, rowz)

            # Vista previa
            preview_img = draw_preview_image(
                composed_prev,
                page_w_cm=pw_cm,
                page_h_cm=ph_cm,
                ml_cm=ml_cm,
                mr_cm=mr_cm,
                mt_cm=mt_cm,
                mb_cm=mb_cm,
                cols=colz,
                rows=rowz
            )
            st.image(preview_img, caption=f"Vista previa: {preview_option}")

            st.write("---")
            st.write("**Descargar en cada formato (rotación automática según su lógica):**")

            # Botón Súper A3
            if st.button("Descargar Súper A3 (9×3=27)"):
                # Re-rotamos
                rot_sa3 = auto_rotate_for_format(user_img, "Súper A3 (9×3=27)")
                comp_sa3 = compose_template(template_path, rot_sa3, 9, 3)
                pdf_sa3 = create_pdf(
                    comp_sa3,
                    47.5, 32.5,
                    1.0, 1.0,
                    2.57, 2.57,
                    9, 3
                )
                st.download_button(
                    "Bajar PDF Súper A3",
                    data=pdf_sa3,
                    file_name="tarjetas_superA3_9x3.pdf",
                    mime="application/pdf"
                )

            # Botón A3
            if st.button("Descargar A3 (8×3=24)"):
                rot_a3 = auto_rotate_for_format(user_img, "A3 (8×3=24)")
                comp_a3 = compose_template(template_path, rot_a3, 8, 3)
                pdf_a3 = create_pdf(
                    comp_a3,
                    42.0, 29.7,
                    1.0, 1.0,
                    1.0, 1.0,
                    8, 3
                )
                st.download_button(
                    "Bajar PDF A3",
                    data=pdf_a3,
                    file_name="tarjetas_A3_8x3.pdf",
                    mime="application/pdf"
                )

            # Botón A4
            if st.button("Descargar A4 (3×4=12)"):
                rot_a4 = auto_rotate_for_format(user_img, "A4 (3×4=12)")
                comp_a4 = compose_template(template_path, rot_a4, 3, 4)
                pdf_a4 = create_pdf(
                    comp_a4,
                    29.7, 21.0,
                    1.0, 1.0,
                    1.0, 1.0,
                    3, 4
                )
                st.download_button(
                    "Bajar PDF A4",
                    data=pdf_a4,
                    file_name="tarjetas_A4_3x4.pdf",
                    mime="application/pdf"
                )

        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Ponela junto al código.")
        except Exception as err:
            st.error(f"Ocurrió un error: {err}")

if __name__ == "__main__":
    main()
