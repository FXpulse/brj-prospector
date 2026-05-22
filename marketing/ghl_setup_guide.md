# GHL Setup Guide — SCM Prospector Marketing

Pasos para configurar la sub-account "SCM Prospector Marketing" en panel.sclickmedia.com:

1. Funnel (landing page) at theprospector.io
2. Form (lead capture) → Workflow A (warm lead → demo)
3. Workflow B (paid customer → onboarding)
4. Calendar booking (15-min demo)

---

## 1️⃣ Funnel — Landing Page en theprospector.io

### Setup

1. **Sub-account "SCM Prospector Marketing"** → **Sites** → **Funnels** → **+ New Funnel**
2. Name: `SCM Prospector — Main Landing`
3. Type: **Sales Funnel**
4. Domain: seleccionar `theprospector.io` (root)
5. Step 1 page name: `Home`
6. Layout: **Single Page** (no menu, no header complejo)

### Build the page

Usar el editor visual de GHL Funnels. Pegar las secciones del archivo `landing_page.md` en orden:

| Funnel section | Source en landing_page.md | Block type en GHL |
|----------------|---------------------------|-------------------|
| Hero | `🔝 HERO` | Hero section + CTA button |
| Three pillars | `🎯 THREE PILLARS` | 3-column block o feature list |
| Apollo comparison | `⚔️ WHY WE'RE NOT APOLLO` | Table block o image-text |
| Case study | `📊 CASE STUDY` | Testimonial / quote block |
| Pricing | `💰 PRICING` | Pricing table (3-column) |
| FAQ | `❓ FAQ` | Accordion / FAQ block |
| Final CTA | `🎬 FINAL CTA` | CTA section |

### Design — coherente con el app

- **Primary color**: `#0F172A` (charcoal, mismo que app)
- **Accent color**: `#10B981` (emerald, CTAs)
- **Background**: blanco
- **Font**: sans-serif (Inter o similar)
- **CTA buttons**: emerald background, white text, rounded
- **Logo/wordmark**: "SCM Prospector" en charcoal con chip "BETA" verde al lado

### SEO meta

- **Title**: `SCM Prospector — Vacancy & Decision-Maker Intelligence for Staffing`
- **Description**: `Find who's hiring. Find who decides. Built specifically for staffing agencies. From $147/mo.`
- **Keywords**: `staffing prospecting, vacancy data, HR decision-maker contacts, staffing agency tools`

---

## 2️⃣ Form — Lead Capture

### Setup

1. **Sites** → **Forms** → **+ New Form**
2. Name: `Demo Request — SCM Prospector`
3. Fields (en este orden):
   - `First Name` (required)
   - `Last Name` (required)
   - `Email` (required)
   - `Company Name` (required)
   - `Role / Title` (required)
   - `Phone` (optional)
   - `What's your biggest prospecting pain right now?` (textarea, optional)
4. Submit button text: **Book Demo**

### Embed en landing

En todas las CTAs del funnel ("Book 15-min demo", "Book demo →", "Book your demo →"):
- Linkear al form OR
- Mostrar form en modal popup al click

### Form behavior

- On submit: redirect a `theprospector.io/thank-you` (página 2 del funnel)
- Show success message: *"Thanks! We'll be in touch within 24 hours with available demo times."*
- Trigger: **Workflow A** (ver abajo)

---

## 3️⃣ Calendar — 15-min Demo

### Setup

1. **Calendars** → **+ New Calendar**
2. Name: `15-min SCM Prospector Demo`
3. Duration: 15 minutes
4. Buffer: 5 min antes / 5 min después
5. Availability: tus horarios reales (ej. M-F 10am-5pm EST)
6. Auto-confirm: Yes
7. Confirmation email: incluye link a Zoom/Google Meet, plus el case study attached

### Calendar link

Pegar en el funnel como CTA alternativa al form: **"Or skip the form, book directly →"** + button con calendar URL.

---

## 4️⃣ Workflow A — Warm Lead → Demo

Trigger: **Form submission** "Demo Request — SCM Prospector"

### Steps

```
[Trigger: Form submitted]
    ↓
[Wait 0 minutes]
    ↓
[Send email: "Thanks for your interest"]
    Subject: Quick question while we set up your demo, {{contact.first_name}}
    Body:
        Hi {{contact.first_name}},

        Thanks for requesting a demo of SCM Prospector!

        Before we hop on, I want to make sure the demo is useful for you.

        Tell me one thing: What's the most painful part of prospecting
        for your team right now? Hand-searching Indeed? Wrong contacts?
        Wasting time on staffing competitors?

        Just hit reply — even 1 sentence helps me tailor the demo.

        Talk soon,
        Ludmila
        Social Click Media

        P.S. Here's the calendar to grab a 15-min slot if you haven't yet:
        [CALENDAR LINK]
    ↓
[Wait 1 day]
    ↓
[Condition: did they reply?]
    ├─ YES → Tag "engaged" + manual follow-up
    └─ NO  → [Send reminder email]
                    Subject: Still want that demo, {{contact.first_name}}?
                    Body: Brief reminder + calendar link
            ↓
        [Wait 2 days]
            ↓
        [Condition: did they book a demo yet?]
            ├─ YES → Move to Workflow C (post-demo follow-up)
            └─ NO  → Tag "cold" + drop from active sequence
```

### Tags created in this workflow

- `lead-prospector` (todos los que llenan form)
- `engaged` (respondieron al primer email)
- `demo-booked` (agendaron via calendar)
- `cold` (no respondieron después de 3 días)

---

## 5️⃣ Workflow B — Paid Customer → Onboarding

Trigger: **Tag "paid-customer" added** (manual o desde Stripe webhook futuro)

### Steps

```
[Trigger: Tag "paid-customer" added]
    ↓
[Send email: Welcome + credentials]
    Subject: Welcome to SCM Prospector, {{contact.first_name}} 🎉
    Body:
        You're in. Here's everything you need:

        🔐 LOGIN
        URL: https://brjprospector.streamlit.app
        Email: {{contact.email}}
        Password: {{custom_field.temp_password}}
        (You'll be prompted to change this on first login)

        📚 GETTING STARTED
        1. Log in with the credentials above
        2. Run your first search in "Companies" page —
           pick your industry, set Min vacancies to 5, click Find
        3. Within 5 minutes, you'll have a list of prospects
           with HR decision-maker contacts

        💬 SUPPORT
        Email hello@theprospector.io for any question.
        Average response: under 4 hours during business days.

        📊 YOUR TIER
        You're on the {{custom_field.tier}} tier.
        - Monthly emails: {{custom_field.email_limit}}
        - Monthly phones: {{custom_field.phone_limit}}
        - Users: {{custom_field.user_limit}}

        Need more capacity mid-month? Reply to this email and
        we'll grant a top-up manually.

        Welcome aboard,
        Ludmila Henry
        Social Click Media
    ↓
[Wait 2 days]
    ↓
[Send email: First search check-in]
    Subject: Did your first search go well?
    Body: Short message asking for feedback + offering 15-min call if stuck
    ↓
[Wait 5 days]
    ↓
[Send email: Tip of the week]
    Subject: 🔍 Pro tip — get more out of SCM Prospector
    Body: Useful tip (e.g., "Use 'priority role' filter to skip C-suite")
    ↓
[Wait 14 days]
    ↓
[Send email: Month-1 review]
    Subject: How's month 1 going?
    Body: Ask for testimonial / case study consent / referrals
```

---

## 6️⃣ Workflow C — Post-Demo Follow-up

Trigger: **Calendar event completed** (demo attended)

### Steps

```
[Trigger: Demo attended]
    ↓
[Wait 1 hour]
    ↓
[Send email: Follow-up + pricing recap]
    Subject: Recap from our demo, {{contact.first_name}}
    Body:
        Hi {{contact.first_name}},

        Thanks for your time today. Quick recap of what we covered:

        - You saw a live search in [their market/industry]
        - We surfaced [X] companies with [Y] decision-makers
        - The Pro tier ($297/mo) fits your team size

        Next steps:
        1. If you're ready to start: reply YES and I'll set up your
           account today. You're using the tool by tomorrow morning.
        2. If you need to think: take 48 hours, I'll follow up.
        3. Questions: just reply.

        — Ludmila
    ↓
[Wait 2 days]
    ↓
[Condition: did they reply YES?]
    ├─ YES → Tag "ready-to-pay" + send Stripe payment link
    └─ NO  → [Send: "Anything holding you back?"]
            ↓
        [Wait 4 days]
            ↓
        [Final: "Closing the door, ping me when ready"]
```

---

## 📋 Checklist setup completo en GHL

- [ ] Funnel `SCM Prospector — Main Landing` creado y publicado en theprospector.io
- [ ] Domain DNS apunta a GHL (debería ser automático si compraste el dominio ahí)
- [ ] Form `Demo Request — SCM Prospector` creado y embed en CTAs del funnel
- [ ] Calendar `15-min SCM Prospector Demo` configurado con disponibilidad real
- [ ] Workflow A (warm lead → demo) creado y activado
- [ ] Workflow B (paid customer → onboarding) creado pero **NO activado** todavía (espera primer cliente)
- [ ] Workflow C (post-demo follow-up) creado y activado
- [ ] Test: enviar tu propio email al form → verificar que workflow A se dispara

---

## ⏱ Tiempo estimado

- Funnel/landing page: 2-3 horas (la primera vez, después es plug-and-play)
- Form + Calendar: 30 min
- 3 Workflows: 1.5 horas
- Testing end-to-end: 30 min

**Total**: ~5 horas de setup en GHL. Después corre solo.

---

## 🎯 Lo más importante

Si tenés que priorizar y solo hacés UNA cosa hoy: **el Funnel (landing page) en theprospector.io**.

Sin landing page, el dominio + email + sub-account están sin uso. Con landing + form básico, ya podés mandar links sin vergüenza a cualquier prospect.

Lo de Workflows B y C podés armar después — los enciendo cuando tengas tu primer cliente real.
