# Chrome Extension Prompt #1 — GHL Billing/Status Setup

Copiá TODO el bloque debajo y pegalo en Claude Chrome extension mientras tenés abierto `panel.sclickmedia.com` con sesión activa en la sub-account "SCM Prospector Marketing".

Corré este PRIMERO. Después de verificar que terminó OK, corré el Prompt #2 (`ghl_chrome_prompt_2_marketing.md`).

---

```
============================================================
SCM PROSPECTOR — GHL FULL SETUP (sub-account configuration)
============================================================

You are operating inside the GoHighLevel sub-account "SCM Prospector Marketing".
The URL must start with:
   https://panel.sclickmedia.com/v2/location/8hNmUNqvL4rhep3XwsFf/

If you are not on this sub-account, navigate there first via panel.sclickmedia.com → Sub-Accounts → select "SCM Prospector Marketing".

GOAL: Configure this sub-account end-to-end for a SaaS product called
"SCM Prospector". You will create:
  - 6 custom contact fields
  - 5 tags
  - 5 products (3 recurring subscriptions + 2 one-time)
  - 3 workflows (subscribe / cancel / payment-failed)
  - 1 sales pipeline with 6 stages

Execute tasks IN ORDER. After each task, briefly confirm what was created.
If a step fails or the UI differs, stop and ask the user.

==========================================================
TASK 1 — CREATE 6 CUSTOM FIELDS ON CONTACT OBJECT
==========================================================

Navigate: Sidebar → Settings → Custom Fields → click "Contact" tab.

For EACH of the 6 fields below, click "+ Add Field" and fill in exactly:

Field 1:
  • Field Name: prospector_tier
  • Field Type: Dropdown (Single Option)
  • Options (add one by one): starter, pro, custom
  • Display in Contact Card: ON
  • Save

Field 2:
  • Field Name: prospector_tenant
  • Field Type: Text
  • Placeholder: "tenant_slug (e.g., acme)"
  • Display in Contact Card: ON
  • Save

Field 3:
  • Field Name: prospector_username
  • Field Type: Text
  • Placeholder: "email used for login"
  • Save

Field 4:
  • Field Name: prospector_password_hash
  • Field Type: Text (Long Text or Textarea)
  • Placeholder: "bcrypt hash from scripts/hash_password.py"
  • Display in Contact Card: OFF (hide — sensitive)
  • Save

Field 5:
  • Field Name: prospector_status
  • Field Type: Dropdown (Single Option)
  • Options: active, trial, paused, cancelled
  • Display in Contact Card: ON
  • Save

Field 6:
  • Field Name: prospector_signup_date
  • Field Type: Date
  • Display in Contact Card: ON
  • Save

✅ After completion: confirm all 6 fields appear in the Custom Fields list.

==========================================================
TASK 2 — CREATE 5 TAGS
==========================================================

Navigate: Sidebar → Settings → Tags

Click "+ Add Tag" and create EACH of these exactly (case-sensitive):
  1. paid-customer
  2. trial
  3. cancelled
  4. paused
  5. prospector-customer

✅ Confirm all 5 tags now appear in the Tags list.

==========================================================
TASK 3 — CREATE 5 PRODUCTS (subscriptions + one-time)
==========================================================

Navigate: Sidebar → Payments → Products → click "+ Create Product".

PRODUCT 1: SCM Prospector — Starter
  • Name: SCM Prospector — Starter
  • Description: "300 email lookups + 30 phone lookups per month. 1 user. CSV exports. History tracking."
  • Type: Service (Recurring)
  • Price: $147.00 USD
  • Billing: Monthly (recurring)
  • Image: (skip)
  • Save & Publish

PRODUCT 2: SCM Prospector — Pro
  • Name: SCM Prospector — Pro
  • Description: "1,000 email lookups + 100 phone lookups per month. 3 users. All Starter features + priority industry presets."
  • Type: Service (Recurring)
  • Price: $297.00 USD
  • Billing: Monthly (recurring)
  • Save & Publish

PRODUCT 3: SCM Prospector — Custom
  • Name: SCM Prospector — Custom
  • Description: "Unlimited usage. Multi-team. Workflow automation hooks. API access. Custom integrations."
  • Type: Service (Recurring)
  • Price: $497.00 USD
  • Billing: Monthly (recurring)
  • Save & Publish

PRODUCT 4: Credits Pack — 500 Emails
  • Name: Credits Pack — 500 Emails
  • Description: "Add 500 bonus email lookups to your current month. Non-recurring top-up."
  • Type: Service (One-time)
  • Price: $50.00 USD
  • Billing: One-time
  • Save & Publish

PRODUCT 5: Credits Pack — 50 Phones
  • Name: Credits Pack — 50 Phones
  • Description: "Add 50 bonus phone lookups to your current month. Non-recurring top-up."
  • Type: Service (One-time)
  • Price: $50.00 USD
  • Billing: One-time
  • Save & Publish

✅ Confirm all 5 products are listed and Published.

==========================================================
TASK 4 — CREATE 3 WORKFLOWS
==========================================================

Navigate: Sidebar → Automation → Workflows.

────────────────────────────────────────
WORKFLOW A: "Customer Subscribed"
────────────────────────────────────────
Click "+ Create Workflow" → Start from Scratch.

Name: "SCM Prospector — Customer Subscribed"

ADD TRIGGER:
  • Trigger Type: "Order Submitted" (or "Subscription Created" if available)
  • Filter: Product is "SCM Prospector — Starter" OR "SCM Prospector — Pro" OR "SCM Prospector — Custom"

ADD ACTION 1: "Add Contact Tag" → paid-customer
ADD ACTION 2: "Add Contact Tag" → prospector-customer
ADD ACTION 3: "Update Custom Field" → prospector_status → active
ADD ACTION 4: "Update Custom Field" → prospector_signup_date → {{contact.date_added}}

ADD ACTION 5 (CONDITIONAL on which product was purchased):
  Use if/else logic OR 3 separate workflows. For now, use one workflow:
  • If product = "SCM Prospector — Starter" → Set prospector_tier = starter
  • Else if product = "SCM Prospector — Pro"   → Set prospector_tier = pro
  • Else if product = "SCM Prospector — Custom" → Set prospector_tier = custom

ADD ACTION 6: "Send Internal Notification"
  • To: hello@theprospector.io
  • Subject: "🎉 New SCM Prospector customer — {{contact.first_name}} {{contact.last_name}}"
  • Body: "Tier: {{custom_field.prospector_tier}}. Now run scripts/create_tenant.py to issue credentials."

Save & Activate the workflow.

────────────────────────────────────────
WORKFLOW B: "Subscription Cancelled"
────────────────────────────────────────
Click "+ Create Workflow" → Start from Scratch.

Name: "SCM Prospector — Subscription Cancelled"

ADD TRIGGER:
  • Trigger Type: "Subscription Cancelled" (or "Order Refunded" if cancel-specific not available)

ADD ACTION 1: "Remove Contact Tag" → paid-customer
ADD ACTION 2: "Add Contact Tag" → cancelled
ADD ACTION 3: "Update Custom Field" → prospector_status → cancelled

ADD ACTION 4: "Send Internal Notification"
  • To: hello@theprospector.io
  • Subject: "⚠️ Cancellation — {{contact.first_name}} {{contact.last_name}}"
  • Body: "Tier was {{custom_field.prospector_tier}}. Consider follow-up."

Save & Activate.

────────────────────────────────────────
WORKFLOW C: "Payment Failed"
────────────────────────────────────────
Click "+ Create Workflow" → Start from Scratch.

Name: "SCM Prospector — Payment Failed"

ADD TRIGGER:
  • Trigger Type: "Payment Failed" (Stripe webhook)

ADD ACTION 1: "Add Contact Tag" → paused
ADD ACTION 2: "Update Custom Field" → prospector_status → paused

ADD ACTION 3: "Send Email to Contact"
  • From: hello@theprospector.io
  • Subject: "Action needed: payment for SCM Prospector failed"
  • Body:
        Hi {{contact.first_name}},
        We could not process your most recent payment for SCM Prospector.
        Your account has been paused. Please update your payment method
        at [link to billing portal] to restore access.
        Reply to this email if you need help.
        — Ludmila

ADD ACTION 4: "Send Internal Notification" → hello@theprospector.io
  • Subject: "💳 Payment failed — {{contact.first_name}} ({{custom_field.prospector_tier}} tier)"

Save & Activate.

==========================================================
TASK 5 — CREATE SALES PIPELINE
==========================================================

Navigate: Sidebar → Opportunities → Pipelines → click "+ Create Pipeline".

Pipeline Name: "SCM Prospector — Sales"

Add the following stages (in order):
  1. Lead (from form submission)
  2. Demo Booked
  3. Demo Completed
  4. Trial / Negotiating
  5. Paid (Active Customer)
  6. Churned / Cancelled

Save.

==========================================================
FINAL VERIFICATION
==========================================================

After completing all 5 tasks, run this checklist and report back:

[ ] 6 custom fields created on Contact (prospector_tier, prospector_tenant,
    prospector_username, prospector_password_hash, prospector_status,
    prospector_signup_date)
[ ] 5 tags exist (paid-customer, trial, cancelled, paused, prospector-customer)
[ ] 5 products published in Payments → Products
[ ] 3 workflows active (Customer Subscribed, Subscription Cancelled, Payment Failed)
[ ] 1 pipeline created with 6 stages

If anything failed, list what failed and the error message you saw.

If everything succeeded, confirm: "GHL setup complete. Ready for Stripe
connection (next step) and first customer flow."

==========================================================
NOTE FOR USER
==========================================================

After this prompt completes:
  - You'll still need to CONNECT STRIPE in Payments → Settings → Integrations
    (Claude can't do this — it requires Stripe OAuth from you personally).
  - You'll still need to set up the FUNNEL/landing page → use Prompt #2.
  - These can be done after this configuration is in place.
```
