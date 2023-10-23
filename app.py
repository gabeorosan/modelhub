from flask import Flask, render_template, request
import requests
import os
API_TOKEN = os.environ.get('API_TOKEN')
app = Flask(__name__)

MODELS = [
    {
        "name": "Mistral-7B-v0.1",
        "url": "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-v0.1",
        "token": API_TOKEN
    },
    {
        "name": "zephyr-7b-alpha",
        "url": "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-alpha",
        "token": API_TOKEN
    },
    {
        "name": "Llama-2-7b-chat-hf",
        "url": "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-chat-hf",
        "token": API_TOKEN
    }
]

@app.route('/', methods=['GET', 'POST'])
def home():
    responses = {}
    if request.method == 'POST':
        user_input = request.form.get('prompt')
        payload = {
            "inputs": user_input,
        }
        for model in MODELS:
            headers = {"Authorization": f"Bearer {model['token']}"}
            try:
                response_data = requests.post(model['url'], headers=headers, json=payload)
                response_data.raise_for_status()  # Raise an error for HTTP errors
                responses[model['name']] = response_data.json()[0]['generated_text']
            except requests.RequestException:
                responses[model['name']] = "Error retrieving response from this model."
    return render_template('index.html', responses=responses, user_input=user_input)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

