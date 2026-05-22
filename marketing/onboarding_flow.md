# Onboarding Flow — Nuevo cliente SCM Prospector

Flujo end-to-end desde "lead acepta pagar" hasta "cliente está usando el tool".

**Total target time**: 30 minutos del momento que pagan hasta que están adentro de la app.

---

## ⏱ Timeline

```
Day 0  ─ Lead paga (Stripe / Zelle / wire)
   ↓ (5 min)
Day 0  ─ Vos corrés create_tenant.py → tenés credentials listas
   ↓ (3 min)
Day 0  ─ Pegás user block en config.json (local) + Streamlit Secrets (cloud)
   ↓ (2 min, auto-rebuild cloud)
Day 0  ─ Cloud reinicia → user puede loguear
   ↓ (5 min)
Day 0  ─ Mandás welcome email con credentials
   ↓ (15 min — esperando que abra)
Day 0  ─ Cliente loguea + corre primer search
```

---

## Step-by-step checklist

### 1. Lead aceptó pagar — Recibís confirmación

- [ ] Lead te confirma por email/WhatsApp que quiere arrancar
- [ ] Decisión de tier: **Starter ($147) / Pro ($297) / Custom ($497+)**
  - Pro es default a menos que pidan otra cosa
- [ ] Confirmás pago (Stripe link, Zelle, wire, lo que sea)
- [ ] **Apenas confirmás pago**, arrancás el setup técnico

### 2. Decidís el tenant slug

El tenant slug es el ID interno corto de la agencia.

**Regla**: lowercase, sin espacios, sin caracteres especiales. Idealmente algo memorable + corto.

Ejemplos:
- BRJ (Bilingual Recruiters Jacksonville) → `brj`
- Acme Staffing Inc → `acme_staffing` o `acme`
- StaffPro Inc → `staffpro`

### 3. Corré el script create_tenant.py

```powershell
cd C:\Users\chemm\brj-prospector
python scripts\create_tenant.py --email john@acme.com --name "John Doe" --tenant acme --tier pro
```

El script va a imprimir:
- Bloque JSON para config.json local
- Bloque TOML para Streamlit Secrets
- Random temp password (12 chars)
- Email de bienvenida pre-formateado

**Copialos a un lugar seguro temporalmente** (Notepad). Los necesitás en step 4 + 5.

### 4. Pegá el user block en config.json (local)

1. Abrí `C:\Users\chemm\brj-prospector\config.json`
2. En la sección `auth.users`, agregá la nueva entrada (pegar el bloque JSON del script)
3. Guardá el archivo

(Esto es para tu testing local. Cliente accede via cloud, no local.)

### 5. Pegá el user block en Streamlit Cloud Secrets

1. Andá a https://share.streamlit.io
2. App **brjprospector** → 3 puntos → **Settings → Secrets**
3. Bajá hasta `[auth.users.ludmila@theprospector.io]`
4. Agregá el nuevo bloque TOML del script
5. **Save**
6. Cloud va a reiniciar automático en ~30 seg-2 min

### 6. Verificá que el user puede loguear

1. Esperá que cloud termine de reiniciar (Streamlit Cloud "Manage app" muestra status)
2. Abrí incognito window (para no usar tu propia sesión admin)
3. Andá a https://brjprospector.streamlit.app
4. Probá login con email del nuevo cliente + temp password
5. Deberías ver:
   - Dashboard vacío (tenant nuevo, sin data)
   - Sidebar muestra "{Display Name} · {TENANT} · {TIER}"
   - Usage bars en 0/X

### 7. Mandá el welcome email

Copiá el email pre-formateado del output del script, ajustá si querés, y mandalo desde:
- **hello@theprospector.io** (vía GHL sub-account "SCM Prospector Marketing")
- O desde Gmail si querés más personal

**Tag al contact** en GHL como `paid-customer` para disparar Workflow B (onboarding sequence automático).

### 8. Follow-up dentro de 24-48 horas

Si **no usaron el tool todavía**:
- Mandá "Hi {name}, want to do a 15-min onboarding call?"
- Ofreceles pantalla compartida para hacer el primer search juntos

Si **ya corrieron 1+ search**:
- "Loved seeing your first search! How did the data quality look?"
- Pide feedback → si bueno, pedí testimonial / case study consent

---

## 🛡️ Cosas que NO se pueden olvidar

| Item | Por qué importa |
|------|----------------|
| Cambiar temp password en first login | Si el cliente reusa la password generada por nosotros, está en logs/memoria. Forzar cambio. (TODO: implementar force-change en lib/auth.py — Phase 2) |
| Tag `paid-customer` en GHL | Sin esto, Workflow B no se dispara, no reciben onboarding sequence |
| Comunicar tier limits | Cliente debería saber su quota mensual desde día 1 — el email lo dice pero confirmalo en la primera call |
| Test access desde incognito | Para no confundir tu sesión admin con la del cliente. Verificar que SOLO ven SU data |

---

## 🔧 Si algo sale mal

| Síntoma | Diagnóstico | Fix |
|---------|-------------|-----|
| Cliente dice "no me deja loguear" | Streamlit secrets no actualizado | Verificar en Streamlit Cloud → Settings → Secrets que el bloque está y bien indentado |
| "Veo datos que no son míos" | Tenant slug mal asignado, comparten data con otro | Revisar config: `tenant` field del user debe ser único o intencionalmente compartido |
| "Las búsquedas se bloquean" | Tier limit alcanzado | Ir a Admin panel → Grant credits → grant +500 emails |
| "No me llegó el welcome email" | GHL sub-account no configurado o email en spam | Reenviar desde Gmail manual |

---

## 🚀 Para automatizar en Phase 2 (cuando haya 5+ clientes)

- [ ] Stripe webhook → auto-trigger create_tenant.py
- [ ] Force password change on first login
- [ ] Self-serve signup page con captura de pago integrada
- [ ] Per-user audit log (login history, search history)
- [ ] Auto-send welcome email vía GHL workflow trigger (no manual paste)

Por ahora — Phase 1 con manual flow es perfecto para 1-5 clientes.

---

## 📝 Template del welcome email (corto)

```
Subject: Welcome to SCM Prospector — your access inside

Hi {name},

Welcome aboard. Your SCM Prospector account is ready:

🔐 LOGIN
URL:      https://brjprospector.streamlit.app
Email:    {email}
Password: {temp_password}

Please change this password on first login.

Your tier: {TIER} — {email_limit} emails/mo, {phone_limit} phones/mo, {users} users

📚 START HERE
1. Log in
2. Go to "Companies" page
3. Pick your industry, set Min vacancies to 5, click 🚀 Find Companies
4. ~5 minutes later: prospects + HR decision-maker contacts in your hand

Questions? Reply this email or hello@theprospector.io

— Ludmila
Social Click Media
```
