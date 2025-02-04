import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io

def adjust_image(image):
    # Ajustar la imagen a un tamaño fijo de 5cm x 9cm (500x900 px en 100 dpi aprox)
    target_size = (500, 900)
    image = ImageOps.fit(image, target_size, method=Image.LANCZOS)
    return image

def create_pdf(image, output_filename="tarjetas_output.pdf"):
    # Definir dimensiones del PDF
    pdf_width = 58.5 * 10  # cm to mm
    pdf_height = 43 * 10  # cm to mm
    card_width = 5 * 10  # 5 cm en mm
    card_height = 9 * 10  # 9 cm en mm
    
    # Crear un PDF en alta calidad
    pdf = FPDF(unit="mm", format=[pdf_width, pdf_height])
    pdf.add_page()
    
    # Ajustar la imagen
    image = adjust_image(image)
    
    # Guardar imagen en memoria en alta calidad
    img_io = io.BytesIO()
    image = image.convert("RGB")  # Convertir a RGB para evitar errores con PNGs con transparencia
    image.save(img_io, format="JPEG", quality=95)  # Guardar en alta calidad
    img_io.seek(0)
    
    # Guardar temporalmente la imagen
    temp_img_path = "temp_image.jpg"
    image.save(temp_img_path, format="JPEG", quality=95)
    
    # Agregar 27 tarjetas en la disposición correcta
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
    st.write("Subí una imagen y generá un PDF con 27 tarjetas en la disposición correcta.")
    
    uploaded_file = st.file_uploader("Subí la imagen de la tarjeta", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGBA")
        pdf_output = create_pdf(image)
        
        st.success("PDF generado con éxito!")
        st.download_button("Descargar PDF", pdf_output, file_name="tarjetas_output.pdf", mime="application/pdf")
        
if __name__ == "__main__":
    main()
