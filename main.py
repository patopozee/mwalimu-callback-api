from fastapi import FastAPI, Request
from firebase_init import db  # Dynamically pull your existing Firestore client instance
from datetime import datetime, timedelta, timezone

app = FastAPI()

@app.get("/")
def health_check():
    """
    Standard health check endpoint ensuring Google Cloud 
    can verify the application is fully online and responsive.
    """
    return {"status": "healthy", "service": "mwalimu-callback-api"}


@app.post("/mpesa-callback")
async def mpesa_callback(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"ResponseCode": "1", "ResponseDesc": "Invalid JSON Payload"}
    
    body = data.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")
    checkout_request_id = body.get("CheckoutRequestID")

    if not checkout_request_id:
        return {"ResponseCode": "1", "ResponseDesc": "Missing CheckoutRequestID"}
    
    # Process successful payment signals
    if result_code == 0:
        metadata = body.get("CallbackMetadata", {}).get("Item", [])

        mpesa_receipt = next(
            (str(item["Value"]) for item in metadata if item["Name"] == "MpesaReceiptNumber"),
            "MPESA_REF"
        )

        # Look up matching checkout session rows
        payment_doc = db.collection("pending_payments").document(checkout_request_id).get()

        if not payment_doc.exists:
            print(f"❌ Record mismatch: {checkout_request_id} not found in database.")
            return {"ResponseCode": "0", "ResponseDesc": "Accept Success"}

        payment = payment_doc.to_dict() or {}
        uid = payment.get("uid")
        plan = payment.get("plan")

        if not uid or not plan:
            return {"ResponseCode": "0", "ResponseDesc": "Accept Success"}

        # Calculate a standard 30-day tier expiration timestamp
        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

        # Push subscription details directly to your user node
        db.collection("users").document(uid).update({
            "subscription": {
                "tier": plan,
                "expiry_date": expiry,
                "payment_status": "Completed",
                "reference_id": mpesa_receipt,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        })

        # Remove the processed document entry cleanly
        db.collection("pending_payments").document(checkout_request_id).delete()
        print(f"✅ Core Premium upgrade finalized for user account: {uid}")
        
    return {"ResponseCode": "0", "ResponseDesc": "Accept Success"}
