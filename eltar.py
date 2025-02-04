import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

def adjust_image(image, size):
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def create_pdf(template, image, grid_positions):
    pdf_width, pdf_height = template.size
    card_width, card_height = grid_positions[0][2], grid_positions[0][3]
    
    pdf = FPDF(unit="pt", format=[pdf_width, pdf_height])
    pdf.add_page()
    
    temp_template_path = "temp_template.jpg"
    template.convert("RGB").save(temp_template_path, format="JPEG", quality=100)
    pdf.image(temp_template_path, x=0, y=0, w=pdf_width, h=pdf_height)
    
    image = adjust_image(image, (int(card_width), int(card_height)))
    temp_img_path = "temp_card.jpg"
    image.convert("RGB").save(temp_img_path, format="JPEG", quality=100)
    
    for x, y, w, h in grid_positions:
        pdf.image(temp_img_path, x=x, y=y, w=w, h=h)
    
    pdf_output = io.BytesIO()
    pdf.output(pdf_output, dest='S')
    pdf_output.seek(0)
    
    os.remove(temp_template_path)
    os.remove(temp_img_path)
    
    return pdf_output

def main():
    st.title("Generador de PDF de Tarjetas")
    st.write("Subí la imagen que se reemplazará en la plantilla.")
    
    template_path = "tarjetas.png"
    uploaded_file = st.file_uploader("Subí la imagen de la tarjeta", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        try:
            template = Image.open(template_path).convert("RGBA")
            image = Image.open(uploaded_file).convert("RGBA")
        except FileNotFoundError:
            st.error("No se encontró la plantilla 'tarjetas.png'. Asegurate de que esté en el repositorio.")
            return
        
        grid_positions = []
        cols, rows = 9, 3
        template_width, template_height = template.size
        card_width = template_width / cols
        card_height = template_height / rows
        
        for row in range(rows):
            for col in range(cols):
                x = col * card_width
                y = row * card_height
                grid_positions.append((x, y, card_width, card_height))
        
        preview = template.copy()
        for x, y, w, h in grid_positions:
            preview.paste(adjust_image(image, (int(w), int(h))), (int(x), int(y)))
        
        st.image(preview, caption="Vista previa de la plantilla con la imagen reemplazada", use_column_width=True)
        
        pdf_output = create_pdf(template, image, grid_positions)
        
        st.success("PDF generado con éxito!")
        st.download_button("Descargar PDF", data=pdf_output.getvalue(), file_name="tarjetas_output.pdf", mime="application/pdf")
        
if __name__ == "__main__":
    main()
