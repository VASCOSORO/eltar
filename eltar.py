import streamlit as st
from PIL import Image, ImageOps, ImageDraw
from fpdf import FPDF
import io
import os

CM_TO_PT = 28.3465

def adjust_image(image, size):
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def compose_template(template_path, user_image, cols, rows, rotate=False):
    template = Image.open(template_path).convert("RGBA")
    if rotate:
        user_image = user_image.rotate(90, expand=True)
    t_w, t_h = template.size
    c_w = t_w / cols
    c_h = t_h / rows
    composed = template.copy()
    for r in range(rows):
        for c in range(cols):
            x = int(c * c_w)
            y = int(r * c_h)
            adjusted = adjust_image(user_image, (int(c_w), int(c_h)))
            composed.paste(adjusted, (x, y))
    return composed

def draw_preview_image(
    composed_image,
    page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows
):
    """
    Genera una PIL Image en blanco (tamaño = hoja en puntos),
    centra 'composed_image' y dibuja las marcas de corte:
    - Marco externo
    - Extensión de columnas en márgenes sup/inf
    - Extensión de filas en márgenes izq/der
    """
    # --- Conversión y “hoja” en blanco ---
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

    # --- Escalar y centrar la imagen compuesta ---
    c_w, c_h = composed_image.size
    content_w_pt = pw_pt - (ml_pt + mr_pt)
    content_h_pt = ph_pt - (mt_pt + mb_cm)
    scale = min(content_w_pt / c_w, content_h_pt / c_h)
    final_w = c_w * scale
    final_h = c_h * scale
    x_pos = ml_pt + (content_w_pt - final_w) / 2
    y_pos = mt_pt + (content_h_pt - final_h) / 2

    # Convertir a píxeles para la vista previa
    x_pos_px = int(round(x_pos))
    y_pos_px = int(round(y_pos))
    final_w_px = int(round(final_w))
    final_h_px = int(round(final_h))

    # Pegamos la imagen escalada
    scaled = composed_image.resize((final_w_px, final_h_px), Image.LANCZOS)
    preview.paste(scaled, (x_pos_px, y_pos_px))

    # --- Dibujar líneas rojas ---
    color = (255, 0, 0)
    lw = 2
    x_right = x_pos_px + final_w_px
    y_bottom = y_pos_px + final_h_px

    # 1) Marco externo
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

    # 2) Columnas internas → solo en margen sup/inf
    for col in range(1, cols):
        x_col = x_pos_px + int(round(col * final_w_px / cols))
        # Margen superior
        draw.line([(x_col, 0), (x_col, y_pos_px)], fill=color, width=lw)
        # Margen inferior
        draw.line([(x_col, y_bottom), (x_col, page_h_px)], fill=color, width=lw)

    # 3) Filas internas → solo en margen izq/der
    for row in range(1, rows):
        y_row = y_pos_px + int(round(row * final_h_px / rows))
        # Margen izquierdo
        draw.line([(0, y_row), (x_pos_px, y_row)], fill=color, width=lw)
        # Margen derecho
        draw.line([(x_right, y_row), (page_w_px, y_row)], fill=color, width=lw)

    return preview

def create_pdf(
    composed_image,
    page_w_cm, page_h_cm,
    ml_cm, mr_cm, mt_cm, mb_cm,
    cols, rows
):
    """
    Crea el PDF con el mismo sistema de líneas:
    - Columnas solo en margen sup/inf
    - Filas solo en margen izq/der
    """
    pw_pt = page_w_cm * CM_TO_PT
    ph_pt = page_h_cm * CM_TO_PT
    ml_pt = ml_cm * CM_TO_PT
    mr_pt = mr_cm * CM_TO_PT
    mt_pt = mt_cm * CM_TO_PT
    mb_pt = mb_cm * CM_TO_PT

    # Guardamos la imagen en disco
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

    # Columnas (solo margen sup/inf)
    for col in range(1, cols):
        x_col = x_pos + (col * final_w / cols)
        # Arriba
        pdf.line(x_col, 0, x_col, y_pos)
        # Abajo
        pdf.line(x_col, yb, x_col, ph_pt)

    # Filas (solo margen izq/der)
    for row in range(1, rows):
        y_row = y_pos + (row * final_h / rows)
        # Izq
        pdf.line(0, y_row, x_pos, y_row)
        # Der
        pdf.line(xr, y_row, pw_pt, y_row)

    pdf_str = pdf.output(dest="S")
    pdf_bytes = pdf_str.encode("latin-1")

    try:
        os.remove(temp_path)
    except OSError:
        pass

    return pdf_bytes

def main():
    st.title("Marcas laterales restauradas: como antes")
    rotate = st.checkbox("Rotar imagen 90° a la izquierda", False)
    upfile = st.file_uploader("Subí tu imagen", ["png", "jpg", "jpeg"])

    if upfile:
        try:
            user_img = Image.open(upfile).convert("RGBA")
            template_path = "tarjetas.png"

            # Ejemplo A3 => 8x3
            composed = compose_template(template_path, user_img, cols=8, rows=3, rotate=rotate)
            # Vista previa
            preview_img = draw_preview_image(
                composed, 
                page_w_cm=42.0, page_h_cm=29.7,
                ml_cm=1.0, mr_cm=1.0, mt_cm=1.0, mb_cm=1.0,
                cols=8, rows=3
            )
            st.image(preview_img, "Vista previa con líneas “como antes”")

            if st.button("Descargar PDF"):
                pdf_data = create_pdf(
                    composed,
                    page_w_cm=42.0, page_h_cm=29.7,
                    ml_cm=1.0, mr_cm=1.0, mt_cm=1.0, mb_cm=1.0,
                    cols=8, rows=3
                )
                st.download_button(
                    "Descargar PDF A3",
                    data=pdf_data,
                    file_name="tarjetas_A3_restablecido.pdf",
                    mime="application/pdf"
                )

        except FileNotFoundError:
            st.error("No se encontró 'tarjetas.png'. Revisá que esté en la carpeta.")
        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
