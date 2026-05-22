# Chrome Extension Prompt #2 — GHL Marketing Engine

Corré este DESPUÉS del Prompt #1. Crea funnel/landing + form + calendar + 3 workflows de marketing con todo el email copy embebido.

Copiá TODO el bloque debajo y pegalo en Claude Chrome extension:

---

```
============================================================
SCM PROSPECTOR — MARKETING AUTOMATIONS (GHL)
============================================================

You are inside the GoHighLevel sub-account "SCM Prospector Marketing".
URL must start with: https://panel.sclickmedia.com/v2/location/8hNmUNqvL4rhep3XwsFf/

PREREQUISITES (verify before starting):
  - The first setup prompt completed successfully
  - 6 custom fields, 5 tags, 5 products exist
  - 3 transactional workflows are active

GOAL: Build the customer-facing marketing engine:
  - Landing page (Funnel) on theprospector.io
  - Demo Request form
  - 15-minute demo calendar
  - 3 marketing workflows with all email copy embedded

Execute IN ORDER. Confirm after each task.

==========================================================
TASK 1 — FUNNEL (Landing Page on theprospector.io)
==========================================================

Navigate: Sidebar → Sites → Funnels → "+ New Funnel"

  • Funnel Name: "SCM Prospector — Main Landing"
  • Type: Sales Funnel
  • Domain: theprospector.io (root)
  • Step 1 Name: Home

Use the visual editor. Add these sections IN ORDER:

────── HERO SECTION ──────
  Headline (H1): Find who's hiring. Find who decides. Get back to placing.
  Sub-headline (H3): The first prospecting platform built specifically for staffing agencies.
                     Stop hand-searching Indeed. Stop landing at CEOs who ignore staffing pitches.
  Primary CTA Button: "Book 15-min demo →"  (linked to Demo Request form — created in TASK 2)
  Sub-text: "15 minutes. Real search in your market. No slides."

────── THREE PILLARS SECTION (3-column layout) ──────
  Column 1:
    Icon: 🎯
    Title: VACANCY SIGNAL
    Body: Real-time data from Indeed, LinkedIn, Glassdoor & Google.
          Filter for companies with 5+ vacancies in 30 days = active-hiring signal.

  Column 2:
    Icon: 📞
    Title: RIGHT-CONTACT ENRICHMENT
    Body: Surfaces HR Coordinators, Plant Managers, Talent Acquisition.
          Not the CEO. The actual decision-maker for staffing pitches.

  Column 3:
    Icon: 🛡️
    Title: COMPETITOR FILTER
    Body: Auto-excludes Adecco, Robert Half, PrideStaff, and 20+ staffing
          agencies. Stop pitching your own competition.

────── COMPARISON SECTION ──────
  Headline (H2): We're not Apollo. We're the staffing agency's version of Apollo.
  Add a table block with these columns and rows:

  | Feature                          | Apollo/Hunter/ZoomInfo | SCM Prospector |
  | Built for staffing?              | ❌ General B2B         | ✅ Vertical     |
  | Filters competitor agencies?     | ❌                     | ✅             |
  | Vacancy signal?                  | ❌                     | ✅             |
  | Operational role priority?       | ❌                     | ✅             |
  | Bilingual market focus?          | ❌                     | ✅             |
  | Monthly price                    | $200–$800              | $147–$497     |

────── CASE STUDY SECTION ──────
  Headline (H2): 3-day ROI. Real customer. Anonymous to protect their advantage.
  Stats (4-column):
    • 1,594 vacancies analyzed
    • 137 unique companies surfaced
    • 21 priority decision-makers
    • <30 min recruiter time

  Testimonial quote:
    "In three days, the tool paid for itself. We stopped chasing C-suite contacts
    that ignore staffing pitches and started reaching HR Coordinators and Plant
    Managers who actually need our help."
    — Director of Recruiting, Regional Staffing Agency

  CTA button: "See it for your market →" (links to Demo Request form)

────── PRICING SECTION (3-column) ──────
  Header: "Pick where it makes sense to start."

  Tier 1: STARTER ($147/month)
    • 300 emails + 30 phones
    • 1 user
    • CSV exports + History tracking
    Best for: testing
    CTA: "Get Started"

  Tier 2: PRO ⭐ ($297/month)  [highlighted/featured]
    • 1,000 emails + 100 phones
    • 3 users
    • All Starter features + priority industries
    Best for: 2-5 recruiters
    CTA: "Get Started" (most popular)

  Tier 3: CUSTOM ($497+/month)
    • Unlimited usage
    • Multi-team + API access
    • Workflow automation
    Best for: Enterprise
    CTA: "Contact Us"

  Footer text: "No setup fees · Cancel anytime · First demo search included free"

────── FAQ SECTION (accordion) ──────
  Q: How is this different from Apollo or ZoomInfo?
  A: Apollo is general B2B sales. We're built specifically for staffing agencies —
     auto-filter competitor agencies, prioritize HR Coordinators over CEOs, surface
     companies with active vacancy signals.

  Q: Do I need to switch my CRM?
  A: No. SCM Prospector exports CSV. Use with Bullhorn, Crelate, Recruiterflow, or any CRM.

  Q: What if I exhaust my tier limit?
  A: Your sidebar shows real-time usage. Request a top-up when near the limit —
     we add bonus credits manually for the rest of the month, no auto-charges.

  Q: How accurate is the data?
  A: Email match confidence shown per contact. Verified vs unverified labeled.

  Q: Is there a free trial?
  A: We do a live demo search in YOUR market on a call. You see real prospects.

  Q: Does it work outside the US?
  A: Currently optimized for US/Canada. International coverage Q3 2026.

────── FINAL CTA ──────
  Headline (H2): Ready to stop hand-searching Indeed?
  Sub: 15 minutes. Real search in your market, your industry.
  CTA button: "Book your demo →"

────── FOOTER ──────
  Made by Social Click Media · hello@theprospector.io

────── SEO META ──────
  Page Title: SCM Prospector — Vacancy & Decision-Maker Intelligence for Staffing
  Meta Description: Find who's hiring. Find who decides. Built specifically for
                    staffing agencies. From $147/mo.

────── DESIGN ──────
  Primary color: #0F172A (charcoal)
  Accent color: #10B981 (emerald — for all CTA buttons)
  Background: white
  Font: sans-serif

Publish the funnel to theprospector.io (root domain).

✅ Confirm: theprospector.io now shows the landing page.

==========================================================
TASK 2 — FORM (Demo Request)
==========================================================

Navigate: Sidebar → Sites → Forms → "+ New Form"

Form Name: "Demo Request — SCM Prospector"

Fields (in this order):
  1. First Name (text, required)
  2. Last Name (text, required)
  3. Email (email, required)
  4. Company Name (text, required)
  5. Role / Title (text, required)
  6. Phone (phone, optional)
  7. "What's your biggest prospecting pain right now?" (textarea, optional)

Submit Button text: "Book Demo"
On Submit:
  • Show success message: "Thanks! We'll be in touch within 24 hours with available demo times."
  • Trigger Workflow A (created in TASK 4)

Embed this form in ALL CTA buttons of the funnel (Hero, Case Study, Pricing,
Final CTA). Use modal popup style.

✅ Confirm: form created and embedded in funnel CTAs.

==========================================================
TASK 3 — CALENDAR (15-min Demo)
==========================================================

Navigate: Sidebar → Calendars → "+ New Calendar"

  • Name: "15-min SCM Prospector Demo"
  • Duration: 15 minutes
  • Buffer time: 5 minutes before / 5 minutes after
  • Availability: Monday–Friday, 10:00 AM – 5:00 PM EST (user can adjust)
  • Auto-confirm: ON
  • Confirmation email: enable, include Zoom/Google Meet link

Get the booking URL (looks like calendar.theprospector.io/15-min-demo).

Add this URL as a secondary CTA in the Hero section of the funnel:
  "Or skip the form, book directly →"

✅ Confirm: calendar created with availability + URL is shareable.

==========================================================
TASK 4 — WORKFLOW A: Warm Lead → Demo
==========================================================

Navigate: Sidebar → Automation → Workflows → "+ Create Workflow"

Name: "SCM Prospector — Warm Lead to Demo"

TRIGGER:
  Type: Form Submitted
  Form: "Demo Request — SCM Prospector"

ACTION 1: Add Contact Tag → lead-prospector

ACTION 2: Wait — 0 minutes (immediate)

ACTION 3: Send Email
  From: hello@theprospector.io
  Subject: Quick question while we set up your demo, {{contact.first_name}}
  Body:

  ────── EMAIL #1 BODY ──────
  Hi {{contact.first_name}},

  Thanks for requesting a demo of SCM Prospector!

  Before we hop on, I want to make sure the demo is actually useful for you.

  Tell me one thing: What's the most painful part of prospecting for your
  team right now? Hand-searching Indeed? Wrong contacts? Wasting time on
  staffing competitors?

  Just hit reply — even 1 sentence helps me tailor the demo specifically
  for what you need.

  Talk soon,
  Ludmila
  Social Click Media

  P.S. Here's the calendar to grab a 15-min slot if you haven't yet:
  [CALENDAR LINK FROM TASK 3]
  ──────────────────────────

ACTION 4: Wait — 1 day (24 hours)

ACTION 5: Condition — "Did contact reply?"
  IF YES → Add tag "engaged" → exit workflow (manual handling)
  IF NO  → continue

ACTION 6: Send Email
  Subject: Still want that demo, {{contact.first_name}}?
  Body:

  ────── EMAIL #2 BODY ──────
  Hey {{contact.first_name}},

  Just bumping this up — wanted to make sure my first email didn't get buried.

  If you're still interested in seeing SCM Prospector run a real search in
  your market, grab a 15-min slot here:

  [CALENDAR LINK]

  No slides, no fluff — we just open the tool and pull prospects in your
  industry, your area.

  If timing isn't right, no worries — let me know and I'll follow up in a few weeks.

  — Ludmila
  ──────────────────────────

ACTION 7: Wait — 2 days

ACTION 8: Condition — "Did contact book demo on calendar?"
  IF YES → Move to "Workflow C — Post-Demo Follow-up"
  IF NO  → Add tag "cold" → drop from active sequence

Save & Activate workflow.

==========================================================
TASK 5 — WORKFLOW B: Customer Onboarding (Paid)
==========================================================

Navigate: Workflows → "+ Create Workflow"

Name: "SCM Prospector — Customer Onboarding"

TRIGGER:
  Type: Tag Added
  Tag: paid-customer

ACTION 1: Wait — 5 minutes

ACTION 2: Send Email
  From: hello@theprospector.io
  Subject: Welcome to SCM Prospector — your access is on the way 🎉
  Body:

  ────── EMAIL #1 — WELCOME (CREDENTIALS SEPARATE) ──────
  Hi {{contact.first_name}},

  Welcome to SCM Prospector! Your subscription is active and we're setting
  up your account right now.

  📬 You'll receive a second email within the next hour with:
     - Your login URL
     - Email + temporary password
     - Quick-start guide

  In the meantime, here's what you can expect:

  ✅ You'll find HR decision-makers at companies actively hiring in your market
  ✅ Avoid wasting outreach on competitor staffing agencies (auto-filtered)
  ✅ Export everything as CSV — use with your existing CRM
  ✅ Run unlimited searches within your tier — {{custom_field.prospector_tier}}

  Questions before your credentials arrive? Just reply to this email.

  Welcome aboard!
  Ludmila Henry
  Social Click Media
  ──────────────────────────────────────────────────────

ACTION 3: Send Internal Notification
  To: hello@theprospector.io
  Subject: 🔔 Onboard {{contact.first_name}} {{contact.last_name}}
  Body: "Run this command now to issue credentials:
         python scripts/create_tenant.py --email {{contact.email}} --name '{{contact.first_name}} {{contact.last_name}}' --tenant <SLUG> --tier {{custom_field.prospector_tier}}
         Then paste the user block in Streamlit Secrets and send credentials email."

ACTION 4: Wait — 2 days

ACTION 5: Send Email
  Subject: How did your first search go, {{contact.first_name}}?
  Body:

  ────── EMAIL #2 — DAY 2 CHECK-IN ──────
  Hi {{contact.first_name}},

  Quick check-in — did you get a chance to run your first search?

  Most agencies see the value within the first 30 minutes. If you've hit
  any friction, hit reply and tell me what you're running into. I'll help
  unstuck whatever it is.

  If you haven't logged in yet, here's the link to make it easy:
  https://brjprospector.streamlit.app

  — Ludmila
  ──────────────────────────────────────

ACTION 6: Wait — 5 days

ACTION 7: Send Email
  Subject: 🔍 Pro tip — get more out of SCM Prospector
  Body:

  ────── EMAIL #3 — DAY 7 TIP ──────
  Hi {{contact.first_name}},

  Quick pro tip from how our power users get the most out of SCM Prospector:

  💡 Use the "Companies" page (Pipeline B), not "Job Search" (Pipeline A),
     for client acquisition.

  Why: Job Search finds vacancies. Companies finds COMPANIES with multiple
  vacancies AND surfaces the HR decision-maker who actually places orders
  for staffing services. That's the contact you want.

  Default settings to try:
    - Industry: pick yours (Manufacturing, Logistics, Healthcare, etc.)
    - Min vacancies: 5
    - Lookback: 14d
    - Locations: your 2-3 main metros

  Run that and look at the "Priority role" checkmark column —
  those are the highest-value contacts to call first.

  Hit reply if any question.

  — Ludmila
  ──────────────────────────────────

ACTION 8: Wait — 14 days

ACTION 9: Send Email
  Subject: How's your first month going?
  Body:

  ────── EMAIL #4 — MONTH 1 REVIEW ──────
  Hi {{contact.first_name}},

  You've had SCM Prospector for ~3 weeks now. Two quick asks:

  1️⃣ How's it going? Honest feedback — what's working, what's confusing,
     what would you change?

  2️⃣ If you've had wins (closed deals, scheduled calls, found great
     contacts), would you be open to a quick 5-min call so I can write
     a short anonymized case study? Helps us help other staffing agencies.

  Either way, thanks for being one of the first SCM Prospector customers.
  Your feedback shapes what we build next.

  — Ludmila
  ──────────────────────────────────────

Save & Activate workflow.

==========================================================
TASK 6 — WORKFLOW C: Post-Demo Follow-up
==========================================================

Navigate: Workflows → "+ Create Workflow"

Name: "SCM Prospector — Post-Demo Follow-up"

TRIGGER:
  Type: Calendar Appointment — Attended
  Calendar: "15-min SCM Prospector Demo"

ACTION 1: Wait — 1 hour

ACTION 2: Send Email
  From: hello@theprospector.io
  Subject: Recap from our demo, {{contact.first_name}}
  Body:

  ────── EMAIL #1 — POST-DEMO RECAP ──────
  Hi {{contact.first_name}},

  Thanks for your time today on the SCM Prospector demo.

  Quick recap of what we covered:

  • You saw a live search in your market
  • We surfaced [X] companies hiring with [Y] decision-makers (numbers
    you saw on screen)
  • Pro tier ($297/mo) is the sweet spot for your team size

  Next steps — three options:

  1️⃣ Ready to start: reply YES and I'll set up your account today.
     You're using the tool by tomorrow morning.

  2️⃣ Need to think: take 48 hours, I'll follow up.

  3️⃣ Questions or concerns: just reply, I'll address them.

  — Ludmila
  ──────────────────────────────────────

ACTION 3: Wait — 2 days

ACTION 4: Condition — "Did contact reply YES or has tag 'paid-customer'?"
  IF YES → Exit workflow (handled by Workflow B onboarding)
  IF NO  → continue

ACTION 5: Send Email
  Subject: Anything holding you back from trying SCM Prospector?
  Body:

  ────── EMAIL #2 — OBJECTION HANDLING ──────
  Hi {{contact.first_name}},

  Wanted to follow up after our demo. I noticed you haven't moved forward yet.

  Totally fine — but I'd love to know what's holding you back. Is it:

  • Budget? (We can talk about a smaller starter tier or phased rollout)
  • Timing? (We can hold the Pro pricing for 30 days while you decide)
  • Internal approval? (I can join a call with your team to walk them through)
  • Something else?

  Hit reply with whatever it is — happy to address it honestly.

  — Ludmila
  ──────────────────────────────────────────

ACTION 6: Wait — 4 days

ACTION 7: Condition — "Did contact reply or convert?"
  IF YES → Exit
  IF NO  → continue

ACTION 8: Send Email — "Final"
  Subject: Closing the door for now, {{contact.first_name}}
  Body:

  ────── EMAIL #3 — FINAL ──────
  Hi {{contact.first_name}},

  Last email from me about SCM Prospector.

  I'm closing the door for now — but if timing changes or you want to
  revisit in a few months, just reply to this email and I'll get you set up.

  In the meantime, here's the case study I mentioned, in case useful:
  [LINK TO CASE STUDY PDF when ready]

  Best of luck with prospecting either way.

  — Ludmila
  ──────────────────────────────────

ACTION 9: Add Contact Tag → "lost"
ACTION 10: Remove all active sequence tags

Save & Activate workflow.

==========================================================
TASK 7 — TEST END-TO-END
==========================================================

Test by submitting the form from the live theprospector.io site
(use a test email like ludmila+test@theprospector.io). Verify:

  [ ] Form submission triggers Workflow A
  [ ] Email #1 arrives within 5 minutes
  [ ] Contact appears in CRM with tag "lead-prospector"

==========================================================
FINAL CHECKLIST — REPORT BACK
==========================================================

[ ] Funnel "SCM Prospector — Main Landing" published on theprospector.io
[ ] Form "Demo Request" created and embedded in funnel CTAs
[ ] Calendar "15-min SCM Prospector Demo" with availability set
[ ] Workflow A (Warm Lead → Demo) — active, 2 emails configured
[ ] Workflow B (Customer Onboarding) — active, 4 emails + 1 internal alert
[ ] Workflow C (Post-Demo Follow-up) — active, 3 emails configured
[ ] Test form submission triggered Workflow A successfully

If all checks pass, confirm: "Marketing engine complete. Ready for first lead."

If anything failed, list the task number + what failed + error message.
```
