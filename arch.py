import gradio as gr
import tensorflow as tf
import numpy as np
from PIL import Image

model = tf.keras.models.load_model(".\\models\\model.keras")

class_names = ['Achaemenid architecture', 'American', 'American Foursquare architecture', 'American craftsman style', 'Ancient', 'Ancient Egyptian architecture', 'Art Deco architecture', 'Art Nouveau architecture', 'Baroque', 'Bauhaus architecture', 'Beaux-Arts architecture', 'Byzantine architecture', 'Chicago school architecture', 'Colonial architecture', 'Deconstructivism', 'Edwardian architecture', 'Georgian architecture', 'Gothic', 'Greek Revival architecture', 'International style', 'Modern', 'Neoclassical', 'Novelty architecture', 'Postmodern', 'Renaissance', 'Romanesque', 'Tudor Revival architecture']

def preprocess_image(image: Image.Image, target_size=(224, 224)):
    image = image.convert("RGB")
    image = image.resize(target_size)
    image_array = np.array(image)
    image_array = np.expand_dims(image_array, axis=0)
    return image_array

def predict_styles(image: Image.Image):
    preprocessed = preprocess_image(image)
    preds = model.predict(preprocessed)[0]

    top_indices = preds.argsort()[-3:][::-1]
    top_classes = [(class_names[i], float(preds[i])) for i in top_indices]

    return {name: score for name, score in top_classes}

css = """
body {
    background-color: #f7f7f7;
    font-family: 'Playfair Display', serif;
}
.gradio-container {
    max-width: 800px;
    margin: 2rem auto;
}
.gradio-interface .output-label {
    color: #6B0101;
    font-weight: 600;
    margin-top: 0.5rem;
}
.gr-button {
    background-color: #6B0101 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-family: 'Merriweather', serif;
    padding: 0.75rem 1.5rem !important;
    text-transform: uppercase;
}
"""

theme = gr.themes.Monochrome(
    primary_hue="blue",
    secondary_hue="gray",
    spacing_size="md",
    radius_size="sm"
)

with gr.Blocks(css=css, theme=theme) as demo:
    gr.Markdown("## Architectural Style Classifier")
    gr.Markdown("Upload an image of a building to get the top-3 predicted architectural styles.")
    
    with gr.Row():
        img_input = gr.Image(type="pil", label="Upload Building")
        lbl_output = gr.Label(num_top_classes=3, label="Top-3 Styles")
    
    img_input.change(fn=predict_styles, inputs=img_input, outputs=lbl_output)

demo.launch()
