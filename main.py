import logging
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request
from firebase_init import db  # Adjust import path if needed

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mpesa_callback")

app = FastAPI(title="Mwalimu AI M-Pesa Callback Webhook")


@app.get("/")
def health_check():
    """Standard health check endpoint for Cloud Run/App Engine probes."""
    return {"status": "healthy", "service": "mwalimu-callback-api"}


@app.post("/payment-received")
async def mpesa_callback(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON received: {e}")
        return {"ResponseCode": "1", "ResponseDesc": "Invalid JSON Payload"}

    body = data.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")
    result_desc = body.get("ResultDesc", "No description provided")
    checkout_request_id = body.get("CheckoutRequestID")

    if not checkout_request_id:
        logger.warning("Callback received without CheckoutRequestID")
        return {"ResponseCode": "1", "ResponseDesc": "Missing CheckoutRequestID"}

    # Fetch matching pending payment record from Firestore
    pending_ref = db.collection("pending_payments").document(
        checkout_request_id
    )
    payment_doc = pending_ref.get()

    if not payment_doc.exists:
        logger.warning(
            f"Record mismatch: {checkout_request_id} not found in database."
        )
        # Always return 0 to Safaricom so they stop retrying
        return {"ResponseCode": "0", "ResponseDesc": "Accepted Success"}

    payment = payment_doc.to_dict() or {}
    uid = payment.get("uid")
    plan = str(payment.get("plan", "premium")).strip().lower()

    if not uid:
        logger.error(f"Missing UID for CheckoutRequestID: {checkout_request_id}")
        return {"ResponseCode": "0", "ResponseDesc": "Accepted Success"}

    # =========================================================
    # 1. SUCCESSFUL PAYMENT (ResultCode == 0)
    # =========================================================
    if result_code == 0:
        metadata = body.get("CallbackMetadata", {}).get("Item", [])

        # Safely parse M-Pesa Transaction Reference Number
        mpesa_receipt = "MPESA_REF"
        amount_paid = payment.get("amount", 0)

        for item in metadata:
            name = item.get("Name")
            val = item.get("Value")
            if name == "MpesaReceiptNumber":
                mpesa_receipt = str(val)
            elif name == "Amount":
                amount_paid = val

        # Normalize plan display text names for frontend
        display_tier = (
            "Mwalimu AI Plus" if "plus" in plan else "Premium"
        )

        start_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        expiry_date = (
            datetime.now(timezone.utc) + timedelta(days=30)
        ).strftime("%Y-%m-%d")

        # Atomic batch / direct update to activate user subscription
        try:
            db.collection("users").document(uid).update(
                {
                    "subscription.tier": display_tier,
                    "subscription.start_date": start_date,
                    "subscription.expiry_date": expiry_date,
                    "subscription.payment_status": "Completed",
                    "subscription.reference_id": mpesa_receipt,
                    "subscription.updated_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
            )

            # Record completed transaction log for accounting
            db.collection("payment_history").document(mpesa_receipt).set(
                {
                    "uid": uid,
                    "plan": display_tier,
                    "amount": amount_paid,
                    "mpesa_receipt": mpesa_receipt,
                    "checkout_request_id": checkout_request_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Clean up pending request
            pending_ref.delete()
            logger.info(
                f"✅ Payment success! User {uid} upgraded to {display_tier} ({mpesa_receipt})."
            )

        except Exception as ex:
            logger.error(
                f"❌ Error updating database for user {uid}: {str(ex)}"
            )

    # =========================================================
    # 2. FAILED PAYMENT (Cancelled, Wrong PIN, Timeout, etc.)
    # =========================================================
    else:
        logger.warning(
            f"⚠️ STK Push Failed for {checkout_request_id}. Code: {result_code}, Reason: {result_desc}"
        )

        # Update pending state to failed so polling frontend can stop waiting instantly
        pending_ref.update(
            {
                "status": "Failed",
                "failure_reason": result_desc,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Safaricom expects standard 200 OK with ResponseCode 0
    return {"ResponseCode": "0", "ResponseDesc": "Accepted Success"}