import streamlit as st
from PIL import Image
from fpdf import FPDF
import io

def create_pdf(image, output_filename="tarjetas_output.pdf"):
    # Definir dimensiones del PDF
    pdf_width = 58.5 * 10  # cm to mm
    pdf_height = 43 * 10  # cm to mm
    card_width = pdf_width / 9  # 9 tarjetas por fila
    card_height = pdf_height / 3  # 3 filas
    
    # Crear un PDF en alta calidad
    pdf = FPDF(unit="mm", format=[pdf_width, pdf_height])
    pdf.add_page()
    
    # Convertir la imagen en alta calidad
    img_io = io.BytesIO()
    image.save(img_io, format="PNG", dpi=(300, 300))
    img_io.seek(0)
    
    # Guardar temporalmente la imagen
    temp_img_path = "temp_image.png"
    image.save(temp_img_path, format="PNG", dpi=(300, 300))
    
    # Agregar 27 tarjetas en la disposición correcta
    for row in range(3):  # 3 filas
        for col in range(9):  # 9 columnas
            x = col * card_width
            y = row * card_height
            pdf.image(temp_img_path, x=x, y=y, w=card_width, h=card_height)
    
    # Guardar el PDF
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
