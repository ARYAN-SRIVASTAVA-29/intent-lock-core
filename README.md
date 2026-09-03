# IntentLock

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [How IntentLock Solves the Problem](#2-how-intentlock-solves-the-problem)
3. [IntentLock Architecture](#3-intentlock-architecture)
4. [Features and Product Walkthrough](#4-features-and-product-walkthrough)
5. [Demo Walkthrough: How to Use IntentLock](#5-demo-walkthrough-how-to-use-intentlock)

<p align="center">
  <img src="./docs/intentlock-system-architecture.svg" alt="IntentLock system architecture" width="75%" />
</p>

<p align="center"><em>IntentLock system architecture — from human intent and untrusted agent input to deterministic enforcement, Razorpay execution, and audit evidence.</em></p>

---

## 1. Problem Statement

> **IntentLock is a deterministic financial firewall for agentic commerce.** It enables AI agents to discover and recommend products while ensuring that no money-moving action can exceed the authority granted by the human, the merchant, or the active payment policy.

### The shift from AI recommendations to AI transactions

AI assistants are quickly moving beyond answering questions. They can search product catalogs, compare prices, select products, call merchant APIs, initiate checkouts, retry failed operations, and act on behalf of a user. This creates the foundation for **agentic commerce**: a world in which software agents participate directly in economic activity.

The opportunity is significant, but so is the risk. A traditional e-commerce application assumes that the application constructing the checkout request is trusted. If a correctly formatted request reaches the payment layer, the system generally focuses on whether the payment can be processed. That assumption is no longer safe when an autonomous agent constructs the request.

An AI agent can be affected by:

- prompt injection hidden inside product descriptions or external content;
- misunderstood or incomplete human instructions;
- stale price, inventory, or merchant information;
- compromised tools, plugins, models, or agent runtimes;
- duplicated tool calls caused by retries or network timeouts;
- malicious changes to product, quantity, price, or payee details;
- reuse of an old authorization for a new transaction;
- recovery logic that accidentally expands the original purchase authority.

The core problem is therefore not simply **“Can an AI agent make a payment?”** The real problem is:

> **How can an AI agent participate in commerce without becoming the final authority over money?**

### A practical example

Consider a customer who instructs an AI buyer:

> “Buy one Sony headphone from this merchant for no more than ₹20,000.”

The human has defined a narrow commercial boundary:

| Constraint | Human authorization |
|---|---|
| Product scope | Sony headphones |
| Maximum quantity | 1 |
| Maximum amount | ₹20,000 |
| Approved merchant | Current onboarded merchant |
| Approved agent | Registered buyer agent |
| Validity | Limited authorization period |

A compromised or malfunctioning agent may later attempt to buy five units, substitute a different product, use a modified price, redirect payment to another merchant, or replay the same signed request. The request may still be valid JSON. It may even carry a valid agent signature. Neither fact proves that the resulting purchase matches what the human authorized.

For example, the agent might submit:

```text
Requested product: Sony headphones
Requested quantity: 5
Asserted total: ₹94,995
Payee: different merchant
```

A payment gateway should not be expected to understand the original natural-language intent, the merchant's catalog rules, or the human's permitted quantity. It executes payment instructions; it is not the authorization boundary for autonomous-agent behavior.

### The missing enforcement layer

Before an AI-generated transaction can reach the payment provider, a secure system must independently answer:

1. Which human intent does this transaction belong to?
2. What product, quantity, amount, merchant, and agent did the human authorize?
3. Is the mandate authentic, unexpired, and still usable?
4. Is the requesting agent registered, and is its signature valid?
5. Did the merchant—not the AI—determine the final product price and inventory?
6. Does the checkout match the signed request exactly?
7. Was any product, quantity, amount, currency, or payee field modified?
8. Does the transaction satisfy per-transaction, daily-spend, and step-up policies?
9. Is this a legitimate retry, a duplicate invocation, or a malicious replay?
10. Can a failed payment be recovered without increasing the original authority?
11. Will inventory be reduced exactly once after verified payment?
12. Can the complete decision be explained and audited afterward?

Most agentic-commerce demos focus on discovery and payment orchestration. IntentLock focuses on the missing layer between them: **deterministic authorization and enforcement before money moves**.

---

## 2. How IntentLock Solves the Problem

IntentLock separates the parties that propose, authorize, price, evaluate, and execute a purchase. No single participant—including the AI agent—can independently cause payment.

### A separation-of-authority model

| Participant | What it controls | What it cannot control |
|---|---|---|
| Human | Intent and maximum permitted authority | Merchant price, inventory, or firewall result |
| AI buyer | Discovery, comparison, recommendation, and proposal | Final financial authorization |
| Merchant | Catalog truth, price, inventory, and payee identity | Expansion of the human mandate |
| IntentLock | Deterministic validation and enforcement | Rewriting human or merchant evidence |
| Razorpay | Test order and payment execution | Interpretation of the original human intent |

IntentLock calculates effective authority as an intersection:

```text
Effective Authority
    = Human Mandate
    ∩ Merchant Checkout Truth
    ∩ Verified Agent Identity
    ∩ Merchant Policy
    ∩ Runtime Safety Controls
```

A transaction proceeds only when it is valid in every set. Passing one control never compensates for failing another.

### Step 1: Convert human intent into bounded authority

The buyer may search broadly, but the human authorizes one exact commercial action. IntentLock creates a mandate containing the approved merchant, registered agent, product constraints, maximum quantity, maximum amount, currency, expiry time, and a unique nonce.

The mandate is canonicalized, hashed, signed, and stored. This produces durable evidence of what the human approved. The AI cannot silently rewrite the mandate after authorization.

### Step 2: Obtain commercial truth from the merchant

The merchant backend creates the authoritative checkout snapshot. It resolves the selected SKU, current unit price, available inventory, quantity, total amount, currency, and payee merchant. A canonical checkout hash binds these values together.

The AI may submit an asserted total, but that value is treated as untrusted input and compared with the merchant's stored checkout. This prevents an agent from inventing or modifying the payable amount.

### Step 3: Bind the agent to the exact economic action

The registered agent signs an envelope containing the mandate, SKU, quantity, checkout identifier, checkout hash, nonce, timestamp, and idempotency key. IntentLock verifies the Ed25519 signature and confirms that the request came from the agent authorized by the mandate.

A valid signature establishes agent identity. It does **not** bypass product, price, policy, replay, or merchant checks.

### Step 4: Evaluate the action through the deterministic kernel

The IntentLock kernel compares three views of the transaction:

- **Human authority:** what may be purchased;
- **Merchant truth:** what is actually being sold and for how much;
- **Agent request:** what the agent is attempting to execute.

It then evaluates identity, signatures, mandate validity, product binding, quantity, price, checkout integrity, payee, inventory, merchant policy, nonces, idempotency, and recovery lineage. The same inputs always produce the same decision and reason codes.

The kernel returns one of three outcomes:

| Decision | Meaning | Effect on payment |
|---|---|---|
| `ALLOW` | Every hard control passed | Razorpay Test order creation is permitted |
| `STEP-UP` | Core controls passed, but policy requires human confirmation | Payment remains `NOT_SENT` until approval |
| `BLOCKED` | One or more mandatory controls failed | Razorpay is never called |

### Step 5: Hard-gate payment execution

The Razorpay order-creation function is placed behind the kernel. A frontend flag, AI instruction, or malformed request cannot directly reach it. Only an `ALLOW` result opens the privileged execution path.

This is why IntentLock is a **financial firewall**, not merely a policy configuration screen. Policy values are inputs. The firewall is the mandatory server-side boundary that blocks access to payment when those values or any other security control fail.

### Step 6: Verify payment and commit inventory exactly once

After Razorpay Test Checkout succeeds, the backend validates the expected order and payment signature before updating transaction state. Inventory is reduced only after the verified payment transition. Repeated callbacks or duplicate confirmation requests return the existing result instead of reducing stock again.

### Step 7: Preserve authority during recovery

If a payment fails and becomes eligible for recovery, IntentLock retains a link to the original transaction and mandate. A recovery attempt creates fresh checkout evidence and re-enters the same deterministic kernel. It cannot increase the authorized amount, quantity, product scope, or merchant scope.

### What IntentLock guarantees

- The AI may recommend, but it cannot authorize itself.
- The merchant controls price and inventory, not the model.
- Payment is unreachable unless the deterministic kernel returns `ALLOW`.
- Blocked transactions generate evidence without creating a Razorpay order.
- Duplicate delivery and malicious replay are handled as different threats.
- Successful inventory movement is idempotent.
- Recovery preserves rather than expands the original authority.
- Every decision carries inspectable checks and reason codes.

---

## 3. IntentLock Architecture

The architecture diagram at the top of this README shows the complete trust path. IntentLock separates untrusted agent input, signed authority, deterministic enforcement, privileged payment execution, and persistent evidence.

### Architectural layers

#### A. Commerce interaction layer

The Next.js application provides the merchant console, onboarding, Reference Buyer, Policies, Agents, Transactions, Attack Lab, Recovery, and Audit Log. External agents can also use merchant discovery and catalog APIs rather than relying on the browser interface.

This layer is intentionally treated as untrusted for payment authorization. It can request an action, but it cannot declare that the action is safe.

#### B. Signed authority layer

IntentLock constructs three independent evidence objects:

1. **Human mandate:** the bounded authority granted by the user;
2. **Merchant checkout:** the authoritative commercial snapshot;
3. **Agent envelope:** the signed action proposed by the registered agent.

Each object has a distinct owner and purpose. The kernel checks their cryptographic and semantic consistency before payment.

#### C. IntentLock control plane

The FastAPI backend is the central enforcement service. Its major responsibilities include:

| Component | Responsibility |
|---|---|
| API gateway | Validates requests and exposes merchant and agent interfaces |
| Authentication boundary | Maintains secure merchant sessions and tenant isolation |
| Intent and mandate service | Persists user intent and signed bounded authority |
| Checkout service | Creates merchant-authoritative price and inventory evidence |
| Agent identity service | Registers keys and verifies signed economic actions |
| Deterministic kernel | Produces `ALLOW`, `STEP-UP`, or `BLOCKED` with reason codes |
| Policy engine | Applies transaction, daily-spend, and escalation limits |
| Replay and idempotency guard | Separates malicious nonce reuse from safe duplicate delivery |
| Recovery controller | Preserves original authority across recovery attempts |

#### D. Privileged execution layer

Payment orchestration is deliberately isolated from normal application requests. The Razorpay Test order function becomes reachable only after an `ALLOW` decision. Payment confirmation verifies the Razorpay signature and legal state transition before inventory is committed.

`STEP-UP` and `BLOCKED` actions remain outside this layer. This creates a measurable security property: a blocked Attack Lab request can show **zero Razorpay API calls**.

#### E. Persistent evidence layer

PostgreSQL stores merchants, catalogs, policies, agents, intents, mandates, checkouts, transactions, payment state, inventory, recovery cases, idempotency records, and audit events.

Every important event is also written to a merchant-scoped SHA-256 hash-linked audit ledger. A Transaction Passport assembles the relevant evidence for one economic action, allowing the merchant to inspect what was authorized, what was requested, which controls passed or failed, whether payment was sent, and how inventory changed.

### End-to-end transaction sequence

```mermaid
sequenceDiagram
    participant H as Human
    participant A as AI Buyer
    participant M as Merchant API
    participant K as IntentLock Kernel
    participant R as Razorpay Test

    H->>A: Describe purchase intent
    A->>M: Discover and search catalog
    M-->>A: Return eligible SKUs
    H->>K: Authorize bounded mandate
    A->>M: Request exact checkout
    M-->>A: Return price, stock, payee and hash
    A->>K: Submit signed economic action
    K->>K: Verify authority, identity, integrity, policy and replay safety
    alt ALLOW
        K->>R: Create one test order
        R-->>H: Razorpay Test Checkout
        H->>K: Return payment proof
        K->>K: Verify payment and commit inventory once
    else STEP-UP
        K-->>H: Require explicit approval
    else BLOCKED
        K-->>A: Return reason codes; payment not sent
    end
```

### Trust boundaries and failure behavior

| Boundary | Input treated as untrusted | Enforced behavior |
|---|---|---|
| AI to merchant | Search query and product proposal | Catalog remains authoritative |
| AI to kernel | SKU, quantity, asserted total, merchant, signature | Compared against mandate and checkout |
| Browser to backend | Session-bound API request | Server validates merchant ownership |
| Kernel to payment | Decision and transaction state | Only `ALLOW` reaches Razorpay |
| Razorpay to backend | Payment identifiers, signature, webhook | Signature and transition are verified |
| Recovery to kernel | Alternative action | Original authority is re-applied |

The architecture therefore fails closed: missing, inconsistent, expired, duplicated, or forged evidence prevents payment rather than relying on the agent to recover safely.

---

## 4. Features and Product Walkthrough

IntentLock combines merchant operations, safe agent commerce, payment enforcement, and auditable security evidence in one console.

| Feature | What it does |
|---|---|
| Six-stage onboarding | Configures merchant, Razorpay Test Mode, catalog, policy, identity, and discovery |
| Control-room dashboard | Shows store-level GMV, decisions, blocked value, inventory, recovery, and audit health |
| Reference Buyer | Searches the live catalog, ranks eligible products, and lets the human authorize one exact SKU |
| Policy controls | Enforces transaction limits, daily spend, step-up thresholds, and recovery boundaries |
| Agent identity | Registers agents and verifies Ed25519-signed economic actions |
| Financial firewall | Returns explainable `ALLOW`, `STEP-UP`, or `BLOCKED` decisions before payment |
| Razorpay Test Checkout | Creates a server-side order only after an `ALLOW` decision |
| Exactly-once inventory | Reduces stock once after verified payment, even if callbacks are repeated |
| Transaction Passport | Combines intent, mandate, checkout, controls, payment, inventory, and audit evidence |
| Attack Lab | Runs adversarial payloads through the real deterministic kernel |
| Bounded recovery | Re-evaluates recovery without expanding the original human authority |
| Audit Log | Maintains a merchant-scoped SHA-256 hash-linked evidence chain |
| Authentication | Uses HttpOnly sessions, merchant isolation, and direct logout to the landing page |

### Product walkthrough

The **Dashboard** is the merchant's operational control room. It greets the store by name and summarizes financial activity, firewall decisions, unsafe GMV prevented, catalog status, inventory movement, recovery cases, duplicate containment, replay protection, and audit integrity.

<p align="center">
  <img src="./docs/images/control-room-dashboard.png" alt="IntentLock merchant control room" width="100%" />
</p>

The **Reference Buyer** converts a natural-language request such as “show me phones under ₹50,000” into a catalog search. It returns multiple eligible SKUs with merchant-controlled price, inventory, delivery, and match scores. The agent recommends, but the human selects and authorizes the exact product.

<p align="center">
  <img src="./docs/images/reference-buyer.png" alt="IntentLock Reference Buyer" width="100%" />
</p>

After authorization, the kernel compares the signed human mandate, merchant checkout, agent envelope, and active policy. An allowed action opens Razorpay Test Checkout. A blocked or step-up action remains `NOT_SENT`.

The **Transaction Passport** explains the result by showing the original intent, signed authority, checkout hash, agent identity, control results, reason codes, Razorpay state, and inventory outcome.

The **Attack Lab** places immutable Human Authority beside editable Agent Input. Scenarios such as quantity escalation, wrong product, checkout mutation, forged signature, wrong merchant, replay, duplicate invocation, expired authorization, and unauthorized recovery are evaluated by the same backend kernel used for ordinary transactions.

<p align="center">
  <img src="./docs/images/attack-lab.png" alt="IntentLock Attack Lab" width="100%" />
</p>

**Recovery** keeps failed-payment alternatives within the original mandate, while **Audit Log** records and verifies the complete decision chain.

---

## 5. Demo Walkthrough: How to Use IntentLock

### Demo links

- **Application:** [https://intent-lock-seven.vercel.app](https://intent-lock-seven.vercel.app)
- **Backend health:** [https://intent-lock-core.onrender.com/api/v1/health](https://intent-lock-core.onrender.com/api/v1/health)
- **API documentation:** [https://intent-lock-core.onrender.com/docs](https://intent-lock-core.onrender.com/docs)

Render may need a short cold start after inactivity. Open the health URL once before recording the demo.

### A. Onboard a merchant

1. Open the application and select **Create account**.
2. Enter the store name, email, and password.
3. Complete the six onboarding stages:

| Stage | Action |
|---|---|
| Merchant | Confirm the store identity |
| Payment | Verify Razorpay Test Mode |
| Catalog | Load demo products or import CSV/JSON |
| Policy | Set transaction, daily-spend, and step-up limits |
| Identity | Provision merchant and buyer-agent identities |
| Discovery | Activate the agent-readable storefront |

4. Enter Dashboard and confirm that the store name and system-health indicators appear.

### B. Complete a valid transaction

1. Open **Reference Buyer** and search for a product, for example: `Show me all phones under ₹50,000`.
2. Review the matching products, merchant prices, stock, delivery estimates, and scores.
3. Select one exact SKU and verify the Authorization Preview.
4. Select **Authorize exact purchase**.
5. Confirm that the kernel returns `ALLOW` and Razorpay Test Checkout opens.
6. Complete the test payment.
7. Open the Transaction Passport and verify the mandate, agent, checkout, payment, and inventory evidence.
8. Open **Catalog** and confirm that stock decreased by exactly one.
9. Refresh Dashboard and confirm that the transaction and GMV are updated.

### C. Prove the firewall in Attack Lab

1. Open **Attack Lab** and select **Quantity Escalation**.
2. Compare Human Authority quantity `1` with Agent Input quantity `5`.
3. Select **Run adversarial request**.
4. Confirm `BLOCKED`, inspect the failed controls and reason codes, and verify that Razorpay calls remain `0`.
5. Confirm that inventory did not change.

Additional scenarios:

| Scenario | Expected result |
|---|---|
| Wrong Product | Product or variant binding fails |
| Checkout Mutation | Checkout-integrity check fails |
| Forged Signature | Agent-signature check fails |
| Wrong Merchant | Merchant or payee binding fails |
| Expired Authorization | Mandate-expiry check fails |
| Replay Mandate | Reused nonce is blocked |
| Duplicate Invocation | One action is retained; duplicates are contained |
| Unauthorized Recovery | Recovery outside the original mandate is blocked |

### D. Verify evidence and finish

1. Open **Transactions** and compare the successful and blocked Transaction Passports.
2. Open **Audit Log**, select **Verify Chain**, and confirm `VERIFIED`.
3. If a recovery case exists, open **Recovery** and show that the alternative re-enters the kernel under the original mandate.
4. Return to Dashboard and point out captured GMV, blocked activity, inventory movement, and audit health.
5. Select **Log out** and confirm that the session returns to the landing page.

For the submission video, use this order: problem statement → architecture → onboarding → valid Razorpay purchase → inventory reduction → blocked quantity escalation → Transaction Passport → verified audit chain.

> **The agent may propose. The human defines authority. The merchant supplies truth. IntentLock decides whether money may move.**
