import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io

def adjust_image(image, size):
    # Ajustar la imagen para que encaje en la plantilla
    image = ImageOps.fit(image, size, method=Image.LANCZOS)
    return image

def create_pdf(template_path, image, grid_positions, output_filename="tarjetas_output.pdf"):
    # Cargar la plantilla desde el repositorio
    template = Image.open(template_path)
    pdf_width, pdf_height = template.size  # Tamaño de la plantilla
    card_width, card_height = grid_positions[0][2], grid_positions[0][3]  # Tamaño de cada tarjeta
    
    # Crear PDF
    pdf = FPDF(unit="pt", format=[pdf_width, pdf_height])
    pdf.add_page()
    
    # Guardar plantilla en un archivo temporal
    temp_template_path = "temp_template.jpg"
    template.convert("RGB").save(temp_template_path, format="JPEG", quality=100)
    pdf.image(temp_template_path, x=0, y=0, w=pdf_width, h=pdf_height)
    
    # Ajustar la imagen y guardarla temporalmente
    image = adjust_image(image, (card_width, card_height))
    temp_img_path = "temp_card.jpg"
    image.save(temp_img_path, format="JPEG", quality=100)
    
    # Insertar la imagen en cada posición de la grilla
    for x, y, w, h in grid_positions:
        pdf.image(temp_img_path, x=x, y=y, w=w, h=h)
    
    # Guardar el PDF en memoria
    pdf_output = io.BytesIO()
    pdf.output(pdf_output, dest='S')
    pdf_output.seek(0)
    return pdf_output

def main():
    st.title("Generador de PDF de Tarjetas")
    st.write("Subí la imagen que se reemplazará en la plantilla.")
    
    template_path = "tarjetas.png"  # Plantilla almacenada en el repositorio
    uploaded_file = st.file_uploader("Subí la imagen de la tarjeta", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        template = Image.open(template_path).convert("RGBA")
        image = Image.open(uploaded_file).convert("RGBA")
        
        # Definir posiciones basadas en la plantilla
        grid_positions = []
        cols, rows = 9, 3  # 9 columnas, 3 filas
        template_width, template_height = template.size
        card_width = template_width / cols
        card_height = template_height / rows
        
        for row in range(rows):
            for col in range(cols):
                x = col * card_width
                y = row * card_height
                grid_positions.append((x, y, card_width, card_height))
        
        # Mostrar vista previa
        preview = template.copy()
        for x, y, w, h in grid_positions:
            preview.paste(adjust_image(image, (int(w), int(h))), (int(x), int(y)))
        
        st.image(preview, caption="Vista previa de la plantilla con la imagen reemplazada", use_column_width=True)
        
        pdf_output = create_pdf(template_path, image, grid_positions)
        
        st.success("PDF generado con éxito!")
        st.download_button("Descargar PDF", pdf_output, file_name="tarjetas_output.pdf", mime="application/pdf")
        
if __name__ == "__main__":
    main()
