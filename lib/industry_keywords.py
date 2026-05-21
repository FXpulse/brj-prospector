"""
industry_keywords.py - Keyword sets por industria para detectar empresas que CONTRATAN
(target de Pipeline B — clientes potenciales de BRJ).

Manufacturing es el más detallado porque es el core target de BRJ en Jacksonville/NE Florida.
"""

INDUSTRY_KEYWORDS = {
    # ─── MANUFACTURING — el más profundo (core de BRJ) ─────────
    "Manufacturing": {
        "description": "Plantas de producción, ensamblaje, procesamiento. Usan staffing para lineas de producción + roles técnicos rotativos.",
        "ne_florida_density": "Alta (Jacksonville Industrial, Westside, Clay County)",
        "queries": [
            # Roles operacionales (volumen alto = staffing signal)
            "production worker",
            "production operator",
            "assembly worker",
            "assembly line worker",
            "machine operator",
            "CNC operator",
            "press operator",
            "injection molding operator",
            # Roles de calidad y mantenimiento
            "quality control inspector",
            "quality assurance technician",
            "maintenance technician",
            "industrial maintenance",
            # Soporte de planta
            "material handler",
            "packaging operator",
            "forklift operator manufacturing",
            "shipping receiving manufacturing",
            # Roles especializados / trades
            "welder",
            "electrician industrial",
            "mechanic industrial",
            "process operator",
        ],
        # Senior roles que SÍ son nuestros decision-makers (Hunter target)
        "decision_maker_roles": [
            "hr manager", "human resources director", "hr director",
            "plant manager", "operations manager", "operations director",
            "vp operations", "vp manufacturing", "general manager",
            "production manager", "manufacturing manager",
            "talent acquisition", "hiring manager",
            "people operations", "head of people",
        ],
        # Empresas a EXCLUIR (chains/franchises sin local decision-making)
        "exclude_companies": [],
    },

    # ─── HOSPITALITY ───────────────────────────────────────────
    "Hospitality": {
        "description": "Hoteles, resorts. Alta rotación + seasonality → staffing constante.",
        "ne_florida_density": "Alta (Jax Beach, Amelia Island, downtown Jacksonville)",
        "queries": [
            "housekeeper hotel",
            "hotel front desk",
            "hotel concierge",
            "hotel maintenance",
            "kitchen staff hotel",
            "hotel cook",
            "bartender hotel",
            "hotel server",
            "hotel host",
            "dishwasher hotel",
            "bellhop",
            "hotel laundry",
            "banquet server",
            "valet attendant hotel",
        ],
        "decision_maker_roles": [
            "hr manager", "general manager", "gm",
            "director of operations", "operations manager",
            "director of housekeeping", "rooms director",
            "f&b director", "food beverage director",
            "talent acquisition", "people operations",
        ],
        "exclude_companies": [
            "marriott corporate", "hilton corporate", "hyatt corporate",
        ],
    },

    # ─── LOGISTICS & WAREHOUSE ─────────────────────────────────
    "Logistics & Warehouse": {
        "description": "Almacenes, distribution centers, port logistics. Picos estacionales → staffing intenso.",
        "ne_florida_density": "Muy alta (puerto JAXPORT + 95 corridor + Westside)",
        "queries": [
            "warehouse worker",
            "warehouse associate",
            "forklift operator",
            "picker packer",
            "order picker",
            "shipping receiving clerk",
            "loader unloader",
            "inventory clerk",
            "warehouse maintenance",
            "CDL driver",
            "truck driver",
            "delivery driver",
            "logistics coordinator",
            "distribution center worker",
        ],
        "decision_maker_roles": [
            "warehouse manager", "operations manager", "dc manager",
            "logistics director", "vp logistics",
            "hr manager", "hr director",
            "general manager", "site manager",
            "talent acquisition", "people operations",
        ],
        "exclude_companies": [
            "amazon",  # corporate, no local hire decisions
            "fedex", "ups",  # mismos
            "walmart distribution", "target distribution",
        ],
    },

    # ─── HEALTHCARE ────────────────────────────────────────────
    "Healthcare": {
        "description": "Clínicas, hospitales, home health. Shortage permanente + shifts 24/7.",
        "ne_florida_density": "Media-alta (Baptist Health, UF Health Jax, Mayo Jacksonville)",
        "queries": [
            "CNA",
            "certified nursing assistant",
            "medical assistant",
            "phlebotomist",
            "patient care technician",
            "home health aide",
            "caregiver",
            "LPN",
            "licensed practical nurse",
            "medical receptionist",
            "patient registrar",
            "EMT",
            "medical scribe",
        ],
        "decision_maker_roles": [
            "director of nursing", "don",
            "hr manager", "hr director",
            "chief nursing officer", "cno",
            "talent acquisition healthcare", "nurse recruiter",
            "people operations", "vp human resources",
        ],
        "exclude_companies": [],
    },

    # ─── CONSTRUCTION ──────────────────────────────────────────
    "Construction": {
        "description": "General contractors + sub-contractors. Project-based hiring → staffing común.",
        "ne_florida_density": "Media (residential growth en Clay/St Johns counties)",
        "queries": [
            "construction laborer",
            "general laborer",
            "carpenter helper",
            "electrician helper",
            "plumber helper",
            "roofer",
            "painter construction",
            "concrete worker",
            "framer",
            "drywall installer",
            "construction foreman",
            "mason",
            "tile installer",
        ],
        "decision_maker_roles": [
            "project manager construction", "operations manager",
            "general manager", "hr manager",
            "superintendent", "construction manager",
            "talent acquisition",
        ],
        "exclude_companies": [],
    },

    # ─── RESTAURANTS & FOOD SERVICE ────────────────────────────
    "Restaurants & Food Service": {
        "description": "Restaurants chain + independents, food service. Rotación más alta de cualquier industria.",
        "ne_florida_density": "Muy alta (downtown, beaches, todos los corridors)",
        "queries": [
            "line cook",
            "prep cook",
            "server restaurant",
            "host hostess restaurant",
            "busser",
            "dishwasher restaurant",
            "food prep",
            "kitchen helper",
            "barista",
            "bartender restaurant",
            "cashier restaurant",
            "fast food crew",
        ],
        "decision_maker_roles": [
            "restaurant manager", "general manager restaurant",
            "hr manager", "operations manager",
            "kitchen manager", "executive chef",
            "talent acquisition",
        ],
        "exclude_companies": [
            "mcdonalds", "burger king", "starbucks", "subway",
            "wendy's", "taco bell", "kfc",
            # franchises grandes no toman decisión local
        ],
    },

    # ─── RETAIL ────────────────────────────────────────────────
    "Retail": {
        "description": "Tiendas, malls, big box. Más estable que restaurants pero high volume seasonal.",
        "ne_florida_density": "Media (St. Johns Town Center, malls, shopping)",
        "queries": [
            "cashier retail",
            "sales associate",
            "stocker",
            "store associate",
            "retail clerk",
            "merchandiser",
            "department lead",
            "retail supervisor",
        ],
        "decision_maker_roles": [
            "store manager", "district manager",
            "hr manager", "operations manager",
            "talent acquisition retail",
        ],
        "exclude_companies": [
            "walmart", "target", "home depot", "lowe's", "costco",
        ],
    },
}


def get_industries():
    """Lista de industrias disponibles para el selector UI."""
    return list(INDUSTRY_KEYWORDS.keys())


def get_industry_config(industry):
    """Devuelve el dict completo de una industria."""
    return INDUSTRY_KEYWORDS.get(industry)


def get_queries_for_industry(industry):
    """Devuelve las queries (lista de strings) de una industria."""
    cfg = INDUSTRY_KEYWORDS.get(industry, {})
    return cfg.get("queries", [])


def get_decision_maker_roles(industry):
    """Devuelve los role keywords para priorizar en Hunter para esta industria."""
    cfg = INDUSTRY_KEYWORDS.get(industry, {})
    return cfg.get("decision_maker_roles", [])


def get_exclude_companies_for_industry(industry):
    """Empresas a excluir specific a esta industria (chains gigantes que no toman decision local)."""
    cfg = INDUSTRY_KEYWORDS.get(industry, {})
    return cfg.get("exclude_companies", [])
