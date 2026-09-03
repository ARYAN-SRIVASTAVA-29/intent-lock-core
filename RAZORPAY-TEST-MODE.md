# Razorpay Test Mode setup

IntentLock ships in `LOCAL_TEST` mode until you add your own Razorpay Test Mode keys. Test keys are free, but they are account-specific and are not public credentials.

## 1. Generate Test Mode API keys

1. Sign in to the Razorpay Dashboard.
2. Switch the Dashboard to **Test Mode**.
3. Open **Account & Settings → API Keys**.
4. Select **Generate Key**.
5. Copy/download the Test **Key ID** and **Key Secret** immediately. Razorpay shows the secret only when it is generated.

## 2. Paste them into IntentLock

Open `backend/.env` and fill:

```env
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
RAZORPAY_WEBHOOK_SECRET=choose_a_long_random_webhook_secret
```

Never put `RAZORPAY_KEY_SECRET` in `.env.local`, frontend code, screenshots, Git, or a hackathon submission.

Restart FastAPI after changing `.env`. Open `http://localhost:8000/api/v1/payments/config`. A correct setup reports:

```json
{
  "razorpay_enabled": true,
  "mode": "RAZORPAY_TEST",
  "credentials_state": "CONNECTED",
  "checkout_ready": true
}
```

## 3. Configure the Test Mode webhook

For a deployed backend, add this webhook URL in Razorpay Test Mode:

```text
https://YOUR-BACKEND/api/v1/payments/webhook
```

Use the same secret in Razorpay and `RAZORPAY_WEBHOOK_SECRET`. Enable:

- `payment.authorized`
- `payment.captured`
- `payment.failed`
- `order.paid`

Razorpay requires a publicly reachable HTTPS endpoint for normal webhook delivery. A `localhost` URL cannot receive Dashboard webhooks directly. Checkout signature verification still works locally; final capture evidence is completed by the verified webhook when the backend is deployed or exposed through an approved HTTPS development tunnel.

## 4. Run a test payment

Open **Reference Buyer** in the IntentLock console, select a catalog match, and authorize it. IntentLock must return `ALLOW` before a Razorpay order and Checkout can open. Use Razorpay's published Test Mode card/UPI details; no real money is charged.
