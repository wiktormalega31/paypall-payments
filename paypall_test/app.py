from flask import Flask, request, jsonify, render_template, redirect
from config import Config
import requests
import base64

app = Flask(__name__)
app.config.from_object(Config)

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

    if not response.ok:
        print("Błąd przy uzyskiwaniu tokenu:", response.status_code, response.text)
        return None

    return response.json().get("access_token")

@app.route("/payments/create", methods=["POST"])
def create_payment():
    data = request.get_json()
    access_token = get_paypal_access_token()

    if not access_token:
        return jsonify({"error": "Nie można uzyskać tokenu dostępu"}), 500

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
            "description": data.get("description", "Płatność testowa")
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

    print("PayPal response status:", response.status_code)
    print("PayPal response body:", response.text)

    if not response.ok:
        return jsonify({
            "error": "Błąd przy tworzeniu płatności",
            "paypal_status": response.status_code,
            "paypal_response": response.text
        }), 500

    payment = response.json()
    approval_url = next(
        (link["href"] for link in payment.get("links", []) if link.get("rel") == "approve"),
        None
    )

    return jsonify({"approval_url": approval_url})

@app.route("/payments/success")
def payment_success():
    return render_template("payment_success.html")

@app.route("/payments/cancel")
def payment_cancel():
    return "Płatność została anulowana", 200

if __name__ == "__main__":
    app.run(debug=True)
