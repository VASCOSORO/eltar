import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io

def adjust_image(image):
    # Ajustar la imagen para que encaje en la plantilla
    target_size = (500, 900)  # 5 cm x 9 cm en 100 dpi
    image = ImageOps.fit(image, target_size, method=Image.LANCZOS)
    return image

def create_pdf(template, image, output_filename="tarjetas_output.pdf"):
    pdf_width, pdf_height = template.size  # Tomar el tamaño de la plantilla
    card_width, card_height = (500, 900)  # Tamaño de cada tarjeta
    
    # Crear PDF
    pdf = FPDF(unit="pt", format=[pdf_width, pdf_height])
    pdf.add_page()
    
    # Guardar plantilla en un archivo temporal
    temp_template_path = "temp_template.jpg"
    template.convert("RGB").save(temp_template_path, format="JPEG", quality=100)
    pdf.image(temp_template_path, x=0, y=0, w=pdf_width, h=pdf_height)
    
    # Ajustar la imagen a la disposición de las tarjetas
    image = adjust_image(image)
    temp_img_path = "temp_card.jpg"
    image.save(temp_img_path, format="JPEG", quality=100)
    
    # Ubicar la imagen en la disposición de la plantilla
    for row in range(3):  # 3 filas
        for col in range(9):  # 9 columnas
            x = col * card_width
            y = row * card_height
            pdf.image(temp_img_path, x=x, y=y, w=card_width, h=card_height)
    
    # Guardar el PDF en memoria
    pdf_output = io.BytesIO()
    pdf.output(pdf_output, dest='S')
    pdf_output.seek(0)
    return pdf_output

def main():
    st.title("Generador de PDF de Tarjetas")
    st.write("Subí la plantilla y la imagen que se reemplazará en ella.")
    
    template_file = st.file_uploader("Subí la plantilla en formato PNG", type=["png"])
    uploaded_file = st.file_uploader("Subí la imagen de la tarjeta", type=["png", "jpg", "jpeg"])
    
    if template_file is not None and uploaded_file is not None:
        template = Image.open(template_file).convert("RGBA")
        image = Image.open(uploaded_file).convert("RGBA")
        
        # Mostrar vista previa de la plantilla con la imagen reemplazada
        preview = template.copy()
        for row in range(3):
            for col in range(9):
                x = col * 500
                y = row * 900
                preview.paste(adjust_image(image), (x, y))
        
        st.image(preview, caption="Vista previa de la plantilla con la imagen reemplazada", use_column_width=True)
        
        pdf_output = create_pdf(template, image)
        
        st.success("PDF generado con éxito!")
        st.download_button("Descargar PDF", pdf_output, file_name="tarjetas_output.pdf", mime="application/pdf")
        
if __name__ == "__main__":
    main()
