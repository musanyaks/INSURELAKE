"""Safaricom M-PESA Daraja STK push + callback -> Kafka -> payments_stream."""
import base64
import os
import time

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

MPESA_ENV      = os.getenv("MPESA_ENV", "sandbox")
CONSUMER_KEY   = os.getenv("MPESA_CONSUMER_KEY", "")
CONSUMER_SECRET= os.getenv("MPESA_CONSUMER_SECRET", "")
SHORTCODE      = os.getenv("MPESA_SHORTCODE", "174379")
PASSKEY        = os.getenv("MPESA_PASSKEY", "")
CALLBACK_URL   = os.getenv("MPESA_CALLBACK_URL", "")

BASE = ("https://sandbox.safaricom.co.ke"
        if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke")

router = APIRouter(prefix="/webhooks/mpesa", tags=["mpesa"])

_token_cache = {"token": None, "expires_at": 0.0}


def _access_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    r = requests.get(
        f"{BASE}/oauth/v1/generate?grant_type=client_credentials",
        auth=(CONSUMER_KEY, CONSUMER_SECRET), timeout=10)
    r.raise_for_status()
    body = r.json()
    _token_cache["token"]      = body["access_token"]
    _token_cache["expires_at"] = time.time() + int(body.get("expires_in", 3599)) - 30
    return _token_cache["token"]


class STKRequest(BaseModel):
    phone: str              # 2547xxxxxxxx
    amount: float
    account_reference: str  # policy_id
    description: str = "Insurance premium"


@router.post("/stk-push")
def initiate(payload: STKRequest):
    token     = _access_token()
    timestamp = time.strftime("%Y%m%d%H%M%S")
    password  = base64.b64encode(
        f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()

    body = {
        "BusinessShortCode": SHORTCODE,
        "Password":          password,
        "Timestamp":         timestamp,
        "TransactionType":   "CustomerPayBillOnline",
        "Amount":            int(payload.amount),
        "PartyA":            payload.phone,
        "PartyB":            SHORTCODE,
        "PhoneNumber":       payload.phone,
        "CallBackURL":       CALLBACK_URL,
        "AccountReference":  payload.account_reference,
        "TransactionDesc":   payload.description,
    }
    r = requests.post(
        f"{BASE}/mpesa/stkpush/v1/processrequest",
        headers={"Authorization": f"Bearer {token}"},
        json=body, timeout=15)
    if not r.ok:
        raise HTTPException(r.status_code, r.text)
    return r.json()


def _register_callback_route(app, producer_getter):
    """Register the callback on the app; producer_getter returns the KafkaProducer."""
    @router.post("/callback")
    def callback(body: dict):
        """Publish Daraja result onto insurance.mpesa."""
        producer = producer_getter()
        try:
            stk = body["Body"]["stkCallback"]
            meta = {m["Name"]: m.get("Value")
                    for m in stk.get("CallbackMetadata", {}).get("Item", [])}
            event = {
                "checkout_request_id": stk["CheckoutRequestID"],
                "merchant_request_id": stk["MerchantRequestID"],
                "result_code":         stk["ResultCode"],
                "result_desc":         stk["ResultDesc"],
                "amount":              meta.get("Amount"),
                "mpesa_receipt":       meta.get("MpesaReceiptNumber"),
                "phone":               meta.get("PhoneNumber"),
                "received_at":         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        except (KeyError, TypeError):
            event = {"raw": body,
                     "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "parse_error": True}
        producer.send("insurance.mpesa", value=event)
        producer.flush()
        return {"ResultCode": 0, "ResultDesc": "Accepted"}