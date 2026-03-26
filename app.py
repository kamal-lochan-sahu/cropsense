from flask import Flask, request, jsonify, render_template

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(force=True, silent=True)
    print("Data received:", data)

    if not data:
        return jsonify({'error': 'No data received'}), 400

    try:
        nitrogen = float(data['nitrogen'])
        phosphorus = float(data['phosphorus'])
        potassium = float(data['potassium'])
        temperature = float(data['temperature'])
        humidity = float(data['humidity'])
        pH = float(data['pH'])
        rainfall = float(data['rainfall'])
        return jsonify({'crop': 'Rice'})
    except KeyError as e:
        print("Missing key:", e)
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)