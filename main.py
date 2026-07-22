from fastapi import FastAPI, Request
from firebase_init import db
from datetime import datetime, timedelta
import collections

app = FastAPI()

# Store the last 20 callbacks for debugging
PAYMENT_AUDIT_LOGS = collections.deque(maxlen=20)


# --------------------------------------------------
# Health Check
# --------------------------------------------------
@app.get("/")
async def home():
    return {
        "status": "Mwalimu Callback API Running"
    }


# --------------------------------------------------
# Audit Endpoint
# --------------------------------------------------
@app.get("/mpesa-audit-vault")
async def audit():
    return list(PAYMENT_AUDIT_LOGS)


# --------------------------------------------------
# M-Pesa Callback Endpoint
# --------------------------------------------------
@app.post("/mpesa-callback")
async def mpesa_callback(request: Request):

    data = await request.json()

    # Save raw callback for debugging
    PAYMENT_AUDIT_LOGS.append({
        "timestamp": datetime.utcnow().isoformat(),
        "payload": data
    })

    body = data.get("Body", {}).get("stkCallback", {})

    result_code = body.get("ResultCode")

    checkout_request_id = (
        body.get("CheckoutRequestID")
        or body.get("CheckoutRequestId")
        or data.get("Body", {}).get("CheckoutRequestID")
    )

    # --------------------------------------------------
    # Only process successful payments
    # --------------------------------------------------
    if result_code == 0:

        metadata = body.get("CallbackMetadata", {}).get("Item", [])

        metadata_dict = {
            item.get("Name"): item.get("Value")
            for item in metadata
        }

        phone = str(metadata_dict.get("PhoneNumber", ""))

        mpesa_receipt = str(
            metadata_dict.get("MpesaReceiptNumber", "UNKNOWN")
        )

        amount = metadata_dict.get("Amount")

        print("=" * 60)
        print("📥 CALLBACK RECEIVED")
        print("CheckoutRequestID:", checkout_request_id)
        print("Phone:", phone)
        print("Receipt:", mpesa_receipt)
        print("Amount:", amount)
        print("=" * 60)

        # ----------------------------------------------
        # Validate CheckoutRequestID
        # ----------------------------------------------
        if not checkout_request_id:
            print("❌ Callback missing CheckoutRequestID.")

            return {
                "ResponseCode": "0",
                "ResponseDesc": "Accept Success"
            }

        # ----------------------------------------------
        # Retrieve Pending Payment
        # ----------------------------------------------
        payment_doc = (
            db.collection("pending_payments")
            .document(checkout_request_id)
            .get()
        )

        if not payment_doc.exists:
            print(f"❌ Pending payment not found: {checkout_request_id}")

            return {
                "ResponseCode": "0",
                "ResponseDesc": "Accept Success"
            }

        payment = payment_doc.to_dict()

        if payment is None:
            print("❌ Pending payment document is empty.")

            return {
                "ResponseCode": "0",
                "ResponseDesc": "Accept Success"
            }

        uid = payment.get("uid")
        plan = payment.get("plan")

        if not uid or not plan:
            print("❌ Pending payment missing uid or plan.")

            return {
                "ResponseCode": "0",
                "ResponseDesc": "Accept Success"
            }

        # ----------------------------------------------
        # Upgrade Subscription
        # ----------------------------------------------
        expiry = (
            datetime.utcnow() + timedelta(days=30)
        ).strftime("%Y-%m-%d")

        db.collection("users").document(uid).update({
            "subscription": {
                "tier": plan,
                "expiry_date": expiry,
                "payment_status": "Completed",
                "reference_id": mpesa_receipt,
                "updated_at": datetime.utcnow().isoformat()
            }
        })

        print(f"✅ Subscription upgraded to '{plan}'")

        # ----------------------------------------------
        # Remove Pending Payment
        # ----------------------------------------------
        db.collection("pending_payments") \
            .document(checkout_request_id) \
            .delete()

        print(f"🗑 Pending payment deleted: {checkout_request_id}")

    else:
        print(f"❌ Payment failed. ResultCode={result_code}")

    # --------------------------------------------------
    # Always acknowledge Safaricom
    # --------------------------------------------------
    return {
        "ResponseCode": "0",
        "ResponseDesc": "Accept Success"
    }