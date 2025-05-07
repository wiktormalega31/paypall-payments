from flask import Flask, request, jsonify, render_template, redirect
from config import Config
import requests
import base64

app = Flask(__name__)
app.config.from_object(Config)

# Uzyskaj token dostępu od PayPala
def get_paypal_access_token():
    client_id = app.config['PAYPAL_CLIENT_ID']
    secret = app.config['PAYPAL_CLIENT_SECRET']
    auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(
        f"{app.config['PAYPAL_BASE_URL']}/v1/oauth2/token",
        headers=headers,
        data={"grant_type": "client_credentials"}
    )

    return response.json().get("access_token")

# Endpoint do tworzenia płatności
@app.route("/payments/create", methods=["POST"])
def create_payment():
    data = request.get_json()
    access_token = get_paypal_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payment_data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": data.get("currency", "PLN"),
                "value": data.get("amount", "10.00")
            },
            "description": data.get("description", "Sample payment")
        }],
        "application_context": {
            "return_url": "http://localhost:5000/payments/success",
            "cancel_url": "http://localhost:5000/payments/cancel"
        }
    }

    response = requests.post(
        f"{app.config['PAYPAL_BASE_URL']}/v2/checkout/orders",
        headers=headers,
        json=payment_data
    )

    payment = response.json()
    approval_url = next(
        (link["href"] for link in payment["links"] if link["rel"] == "approve"),
        None
    )

    return jsonify({"approval_url": approval_url})

# Obsługa sukcesu
@app.route("/payments/success")
def payment_success():
    return render_template("payment_success.html")

# Obsługa anulowania
@app.route("/payments/cancel")
def payment_cancel():
    return "Płatność została anulowana", 200

# Webhook (do skonfigurowania w PayPal)
@app.route("/payments/webhook", methods=["POST"])
def paypal_webhook():
    event = request.get_json()
    # Tu można zaktualizować stan płatności w bazie
    print("Webhook received:", event)
    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(debug=True)
