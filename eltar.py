import streamlit as st
from PIL import Image, ImageOps
from fpdf import FPDF
import io
import os

def adjust_image(image, size):
    """
    Ajusta la imagen a un tamaño específico utilizando ImageOps.fit,
    manteniendo la relación de aspecto. 
    """
    return ImageOps.fit(image, size, method=Image.LANCZOS)

def create_pdf(template, image, grid_positions):
    """
    Crea el PDF, coloca la plantilla y rellena la grilla con la imagen ajustada.
    """
    pdf_width, pdf_height = template.size
    card_width, card_height = grid_positions[0][2], grid_positions[0][3]
    
    pdf = FPDF(unit="pt", format=[pdf_width, pdf_height])
    pdf.add_page()
    
    # Guardamos la plantilla temporalmente (para poder usar pdf.image)
    temp_template_path = "temp_template.jpg"
    template.convert("RGB").save(temp_template_path, format="JPEG", quality=100)
    pdf.image(temp_template_path, x=0, y=0, w=pdf_width, h=pdf_height)
    
    # Ajustamos la imagen al tamaño de cada tarjeta y guardamos temporal
    image = adjust_image(image, (int(card_width), int(card_height)))
    temp_img_path = "temp_card.jpg"
    image.convert("RGB").save(temp_img_path, format="JPEG", quality=100)
    
    # Rellenamos la grilla
    for x, y, w, h in grid_positions:
        pdf.image(temp_img_path, x=x, y=y, w=w, h=h)
    
    # Generamos el PDF en memoria como string (dest='S')
    pdf_str = pdf.output(dest='S')
    
    # Convertimos el string a bytes (necesario para descargar)
    pdf_bytes = pdf_str.encode('latin-1')
    
    # Eliminamos temporales
    try:
        os.remove(temp_template_path)
        os.remove(temp_img_path)
    except OSError:
        pass
    
    return pdf_bytes

def main():
    st.title("Generador de PDF de Tarjetas")
    st.write("Subí la imagen que se reemplazará en la plantilla. Si necesitás girarla, marcá el check.")

    template_path = "tarjetas.png"
    rotate_image = st.checkbox("Girar 90° a la izquierda", value=False)
    
    uploaded_file = st.file_uploader("Subí la imagen de la tarjeta", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        try:
            # Cargamos plantilla
            try:
                template = Image.open(template_path).convert("RGBA")
            except FileNotFoundError:
                st.error("No se encontró la plantilla 'tarjetas.png'. Asegurate de que esté en el repositorio.")
                return
            
            # Cargamos imagen subida
            image = Image.open(uploaded_file).convert("RGBA")
            
            # Giramos si corresponde
            if rotate_image:
                image = image.rotate(90, expand=True)
            
            # Definimos la grilla 9x3
            cols, rows = 9, 3
            template_width, template_height = template.size
            card_width = template_width / cols
            card_height = template_height / rows
            
            # Calculamos las posiciones de cada tarjeta
            grid_positions = []
            for row in range(rows):
                for col in range(cols):
                    x = col * card_width
                    y = row * card_height
                    grid_positions.append((x, y, card_width, card_height))
            
            # Generamos preview
            preview = template.copy()
            for x, y, w, h in grid_positions:
                img_adjusted = adjust_image(image, (int(w), int(h)))
                preview.paste(img_adjusted, (int(x), int(y)))
            
            st.image(preview, caption="Vista previa de la plantilla con la imagen", use_column_width=True)
            
            # Creamos el PDF y obtenemos sus bytes
            pdf_bytes = create_pdf(template, image, grid_positions)
            
            st.success("¡PDF generado con éxito!")
            st.download_button(
                "Descargar PDF",
                data=pdf_bytes,
                file_name="tarjetas_output.pdf",
                mime="application/pdf"
            )
        
        except Exception as e:
            st.error(f"Ocurrió un error al procesar la imagen: {e}")

if __name__ == "__main__":
    main()
