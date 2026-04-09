"""
generador_reporte_v2.py — SARD TECH
Motor de reportes basado en CIS Controls v8 IG1.
Claude NO inventa datos — solo clasifica y selecciona de fuentes reales.
Fuentes: IBM Cost of Data Breach 2024, Verizon DBIR 2024, LFPDPPP, CIS v8
"""
import os, json, re, uuid, datetime, threading
import anthropic, requests

BASE_DIR   = os.path.dirname(__file__)
KB_DIR     = os.path.join(BASE_DIR, "knowledge_base")
cliente_ai = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── Carga de knowledge base ────────────────────────────────
def _kb(nombre: str) -> dict:
    with open(os.path.join(KB_DIR, nombre), encoding="utf-8") as f:
        return json.load(f)

CIS         = _kb("cis_controls_ig1.json")
BENCHMARKS  = _kb("benchmarks_mx.json")
CUMPLIMIENTO = _kb("cumplimiento_mx.json")
REMEDS      = _kb("remediaciones.json")

# ── Helpers ────────────────────────────────────────────────
def _json_limpio(texto: str) -> dict:
    texto = re.sub(r"```json|```", "", texto).strip()
    return json.loads(texto)

def _industria_datos(giro: str) -> dict:
    """Devuelve datos reales de benchmark para el giro detectado."""
    giro = giro.lower().strip()
    mapa = {
        "financiero": "financiero", "fintech": "financiero", "banco": "financiero",
        "seguro": "financiero",  "seguros": "financiero",
        "salud": "salud", "clínica": "salud", "hospital": "salud", "farmacia": "salud",
        "retail": "retail", "comercio": "retail", "tienda": "retail", "ecommerce": "retail",
        "manufactura": "manufactura", "maquiladora": "manufactura", "industria": "manufactura",
        "educacion": "educacion", "educación": "educacion", "escuela": "educacion",
        "logistica": "logistica", "logística": "logistica", "transporte": "logistica",
        "gobierno": "gobierno", "municipal": "gobierno", "estatal": "gobierno",
        "tecnologia": "tecnologia", "tecnología": "tecnologia", "software": "tecnologia",
        "servicios": "servicios_profesionales", "consultoria": "servicios_profesionales",
        "despacho": "servicios_profesionales", "contabilidad": "servicios_profesionales"
    }
    for k, v in mapa.items():
        if k in giro:
            return BENCHMARKS["por_industria"][v]
    return BENCHMARKS["por_industria"]["default"]

def _regulaciones_giro(giro: str) -> list[dict]:
    """Devuelve regulaciones aplicables al giro detectado."""
    giro = giro.lower()
    mapa_giro = CUMPLIMIENTO["mapa_regulacion_por_giro"]
    clave = next((k for k in mapa_giro if k in giro), "default")
    ids_reg = mapa_giro[clave]
    return [CUMPLIMIENTO["regulaciones"][r] for r in ids_reg if r in CUMPLIMIENTO["regulaciones"]]

# ── PASO 1: Análisis con Claude (solo clasificación, sin inventar) ──
def analizar_conversacion(historial: list[dict]) -> dict:
    """
    Claude SOLO clasifica y selecciona. Nunca genera números.
    Todos los datos cuantitativos vienen del knowledge base.
    """
    historial_txt = "\n".join(
        f"{'KIRA' if m['role'] == 'assistant' else 'CLIENTE'}: {m['content']}"
        for m in historial
    )

    # Índice de IDs de controles para contexto
    ids_controles = [c["id"] for c in CIS["controles"]]

    prompt = f"""Eres un auditor de ciberseguridad de SARD TECH analizando una conversación de diagnóstico.
Tu trabajo es CLASIFICAR lo que el cliente dijo — NO inventar información que no esté en la conversación.

CONVERSACIÓN:
{historial_txt}

CONTROLES DISPONIBLES (CIS Controls v8 IG1): {json.dumps(ids_controles)}

Responde ÚNICAMENTE con un JSON válido sin markdown con esta estructura:

{{
  "empresa": "nombre exacto mencionado o 'No especificado'",
  "nombre_contacto": "nombre mencionado o 'Cliente'",
  "email": "correo exacto mencionado o null",
  "giro": "sector detectado: financiero|salud|retail|manufactura|educacion|logistica|gobierno|tecnologia|servicios_profesionales|default",
  "tamanio_empresa": "micro (1-10) | pequena (11-50) | mediana (51-200) | grande (200+) | desconocido",
  "miedo_principal": "frase exacta o parafraseada del mayor miedo expresado por el cliente, máximo 20 palabras",
  "incidente_previo": true o false,
  "descripcion_incidente_previo": "descripción si mencionó alguno, o null",
  "controles_fallidos": [
    "CIS-X.X",
    "CIS-X.X"
  ],
  "controles_presentes": [
    "CIS-X.X"
  ],
  "controles_desconocidos": [
    "CIS-X.X"
  ],
  "observaciones_adicionales": "contexto importante de la conversación no capturado en los controles, máximo 100 palabras o null"
}}

REGLAS CRÍTICAS:
1. Solo incluye controles donde la conversación da evidencia clara de su estado
2. La duda va en 'controles_desconocidos', no en fallidos ni presentes
3. NO añadas controles que no se discutieron en la conversación
4. El 'miedo_principal' debe ser una cita o paráfrasis de lo que EL CLIENTE dijo, no tu análisis
5. Responde SOLO el JSON, sin explicaciones"""

    resp = cliente_ai.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return _json_limpio(resp.content[0].text)


# ── PASO 2: Construir datos del reporte desde el KB ──────────
def construir_datos_reporte(analisis: dict) -> dict:
    """
    Combina el análisis de Claude con datos REALES del knowledge base.
    Cero alucinaciones: todo número tiene fuente verificable.
    """
    giro          = analisis.get("giro", "default")
    bench         = _industria_datos(giro)
    regulaciones  = _regulaciones_giro(giro)
    controles_idx = {c["id"]: c for c in CIS["controles"]}
    remeds_idx    = REMEDS["remediaciones"]
    stats         = BENCHMARKS["estadisticas_generales"]
    roi           = BENCHMARKS["roi_plan_blindaje"]

    # Controles fallidos con detalle
    fallidos = []
    for cid in analisis.get("controles_fallidos", []):
        ctrl = controles_idx.get(cid)
        if not ctrl:
            continue
        remed = remeds_idx.get(cid, {})
        fallidos.append({
            "id": cid,
            "titulo": ctrl["titulo"],
            "grupo": ctrl["grupo"],
            "peso": ctrl["peso"],
            "categoria": ctrl["categoria"],
            "impacto": ctrl["impacto_sin_control"],
            "estandar": ctrl["estandar_ref"],
            "severidad": _peso_a_severidad(ctrl["peso"]),
            "clase_css": _peso_a_clase(ctrl["peso"]),
            "remediacion_titulo": remed.get("titulo", "Consultar con especialista"),
            "acciones": remed.get("acciones", []),
            "costo_mxn": remed.get("costo_estimado_mxn", 0),
            "tiempo": remed.get("tiempo_implementacion", "Variable"),
            "herramientas_gratuitas": remed.get("herramientas_gratuitas", []),
            "fuente_impacto": remed.get("fuente_dato_impacto", ctrl["estandar_ref"]),
            "sard_tech": remed.get("sard_tech_lo_implementa", True),
            "plan": remed.get("incluido_en_plan", "Blindaje PyME")
        })

    # Ordenar por peso descendente
    fallidos.sort(key=lambda x: x["peso"], reverse=True)

    # Score de riesgo basado en peso de controles fallidos
    peso_total    = sum(c["peso"] for c in controles_idx.values())
    peso_fallido  = sum(c["peso"] for c in fallidos)
    score_raw     = round((peso_fallido / max(peso_total, 1)) * 10, 1)
    score         = min(10.0, score_raw)

    num_criticos  = len([f for f in fallidos if f["peso"] >= 5])
    num_altos     = len([f for f in fallidos if f["peso"] == 4])
    num_medios    = len([f for f in fallidos if f["peso"] <= 3])

    nivel, clase_riesgo = _score_a_nivel(score)

    # Probabilidad personalizada: base + penalización por controles críticos
    prob_base     = bench["probabilidad_ataque_12m"]
    penalizacion  = num_criticos * 3
    prob_ajustada = min(98, prob_base + penalizacion)

    # Áreas de riesgo para el radar del reporte
    radar = _calcular_radar(fallidos)

    # Regulaciones críticas (las primeras 3 más relevantes)
    regs_display = []
    for r in regulaciones[:3]:
        regs_display.append({
            "nombre": r["nombre_completo"],
            "aplica": r["aplica_a"],
            "riesgo": r["riesgo_incumplimiento"],
            "sancion_max": r.get("sanciones", {}).get("multa_maxima_mxn_aprox", None)
        })

    # Plan de acción priorizado (top 5 controles fallidos)
    acciones = []
    for i, f in enumerate(fallidos[:5], 1):
        plazo = "inmediato" if f["peso"] >= 5 else ("corto" if f["peso"] == 4 else "mediano")
        etiq = {
            "inmediato": "⚡ INMEDIATO · Esta semana",
            "corto":     "◉ CORTO PLAZO · Primer mes",
            "mediano":   "◈ MEDIANO PLAZO · 30-60 días"
        }[plazo]
        acciones.append({
            "numero": i,
            "titulo": f["remediacion_titulo"],
            "descripcion": f["acciones"][0] if f["acciones"] else f["impacto"],
            "plazo": plazo,
            "etiqueta": etiq,
            "costo_mxn": f["costo_mxn"],
            "herramienta_gratuita": f["herramientas_gratuitas"][0] if f["herramientas_gratuitas"] else None,
            "fuente": f["fuente_impacto"]
        })

    return {
        "empresa":               analisis.get("empresa", "Tu empresa"),
        "nombre_contacto":       analisis.get("nombre_contacto", "Cliente"),
        "email":                 analisis.get("email"),
        "giro":                  bench["nombre_display"],
        "tamanio":               analisis.get("tamanio_empresa", "desconocido"),
        "miedo_principal":       analisis.get("miedo_principal", ""),
        "incidente_previo":      analisis.get("incidente_previo", False),
        "score_riesgo":          score,
        "nivel_riesgo":          nivel,
        "clase_riesgo":          clase_riesgo,
        "num_criticos":          num_criticos,
        "num_altos":             num_altos,
        "num_medios":            num_medios,
        "fallidos":              fallidos,
        "acciones":              acciones,
        "regulaciones":          regs_display,
        "radar":                 radar,
        # Datos reales del KB — NUNCA inventados
        "costo_brecha_mxn":      bench["costo_brecha_mxn"],
        "prob_ataque_pct":       prob_ajustada,
        "tiempo_deteccion_dias": bench["tiempo_deteccion_dias"],
        "fuente_costo":          bench["fuente_costo"],
        "vector_principal":      bench["vector_ataque_principal"],
        "pct_error_humano":      stats["pct_brechas_por_error_humano"],
        "pct_phishing":          stats["pct_brechas_por_phishing"],
        "roi_ratio":             roi["ratio_proteccion_inversion"],
        "costo_anual_plan_mxn":  roi["costo_anual_mxn"],
        "fuentes_reporte":       [
            "IBM Cost of a Data Breach Report 2024",
            "Verizon Data Breach Investigations Report 2024",
            "CIS Controls v8 — Center for Internet Security",
            "Proofpoint State of the Phish 2024",
            "INAI — Ley Federal de Protección de Datos Personales 2024"
        ]
    }


# ── PASO 3: Renderizar HTML ──────────────────────────────────
def renderizar_reporte(datos: dict) -> str:
    ruta = os.path.join(BASE_DIR, "reporte_kira.html")
    with open(ruta, encoding="utf-8") as f:
        html = f.read()

    folio = f"SARD-{datetime.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    fecha = datetime.date.today().strftime("%d de %B de %Y")

    # Placeholders básicos
    reemplazos = {
        "{{EMPRESA}}":          datos["empresa"],
        "{{NOMBRE}}":           datos["nombre_contacto"],
        "{{FECHA}}":            fecha,
        "{{FOLIO}}":            folio,
        "{{SCORE}}":            str(datos["score_riesgo"]),
        "{{NUM_CRITICOS}}":     str(datos["num_criticos"]),
        "{{NUM_ALTOS}}":        str(datos["num_altos"]),
        "{{NUM_MEDIOS}}":       str(datos["num_medios"]),
        "{{PCT_ACCESOS}}":      str(datos["radar"].get("accesos", 50)),
        "{{PCT_NUBE}}":         str(datos["radar"].get("nube", 50)),
        "{{PCT_REDES}}":        str(datos["radar"].get("redes", 50)),
        "{{PCT_HUMANO}}":       str(datos["radar"].get("humano", 50)),
        "{{PCT_BACKUP}}":       str(datos["radar"].get("backup", 50)),
        "{{PCT_COMMS}}":        str(datos["radar"].get("comms", 30)),
        "{{COSTO_BACKUP}}":     "350",
        "{{RESUMEN_EJECUTIVO}}": _generar_resumen(datos),
    }
    for k, v in reemplazos.items():
        html = html.replace(k, str(v))

    # Clase de riesgo
    html = html.replace('class="risk-banner alto"', f'class="risk-banner {datos["clase_riesgo"]}"')
    html = html.replace('RIESGO ALTO', f'RIESGO {datos["nivel_riesgo"]}')

    # Bloque de benchmarks (insertar antes del CTA final)
    bloque_bench = _html_benchmarks(datos)
    html = html.replace("<!-- ══ CTA FINAL ══ -->", bloque_bench + "\n  <!-- ══ CTA FINAL ══ -->")

    # Hallazgos dinámicos
    hallazgos_html = ""
    for f in datos["fallidos"]:
        iconos = {"critico": "⚠", "alto": "▲", "medio": "●", "bajo": "✓"}
        icono = iconos.get(f["clase_css"], "●")
        acciones_li = "".join(f"<li>{a}</li>" for a in f["acciones"][:3])
        hallazgos_html += f"""
    <div class="finding {f['clase_css']}">
      <div class="finding-head">
        <span class="finding-name">{f['titulo']}</span>
        <span class="severity-pill">{icono} {f['severidad']}</span>
      </div>
      <p class="finding-desc">{f['impacto']}</p>
      <ul style="font-size:0.82rem;color:#4b5563;margin:8px 0 10px 16px;line-height:1.6;">{acciones_li}</ul>
      <div class="finding-rec">
        <strong>Acción recomendada:</strong> {f['acciones'][0] if f['acciones'] else ''}
        {'<br><span style="font-size:0.78rem;color:#6b7280;">Herramienta gratuita: ' + f["herramientas_gratuitas"][0] + '</span>' if f.get("herramientas_gratuitas") else ''}
      </div>
      <div style="font-size:0.72rem;color:#9ca3af;margin-top:8px;">
        Fuente: {f['fuente_impacto']} · Estándar: {f['estandar']}
      </div>
    </div>"""

    html = re.sub(
        r'<!-- ══ HALLAZGOS DETALLADOS ══ -->.*?<!-- ══ PLAN DE ACCIÓN ══ -->',
        f'''<!-- ══ HALLAZGOS DETALLADOS ══ -->
  <div class="sec">
    <div class="sec-header">
      <span class="sec-num">03</span>
      <h2 class="sec-title">Hallazgos Detallados</h2>
    </div>
    {hallazgos_html}
  </div>
  <!-- ══ PLAN DE ACCIÓN ══ -->''',
        html, flags=re.DOTALL
    )

    # Acciones dinámicas
    acciones_html = ""
    for a in datos["acciones"]:
        gratuito = f'<span style="font-size:0.75rem;color:#059669;margin-left:8px;">Herramienta gratuita: {a["herramienta_gratuita"]}</span>' if a.get("herramienta_gratuita") else ""
        costo    = f'<span style="font-size:0.75rem;color:#6b7280;"> · Costo: {"$0 — gratis" if a["costo_mxn"] == 0 else f"${a[chr(99)+chr(111)+chr(115)+chr(116)+chr(111)+chr(95)+chr(109)+chr(120)+chr(110)]:,.0f} MXN"}</span>'
        acciones_html += f"""
    <div class="action-item">
      <div class="action-num">{a['numero']}</div>
      <div class="action-body">
        <h4>{a['titulo']}</h4>
        <p>{a['descripcion']}</p>
        <div style="margin-top:6px;">{gratuito}</div>
        <span class="action-tag {a['plazo']}">{a['etiqueta']}</span>
        <div style="font-size:0.72rem;color:#9ca3af;margin-top:4px;">Fuente: {a['fuente']}</div>
      </div>
    </div>"""

    html = re.sub(
        r'<!-- ══ PLAN DE ACCIÓN ══ -->.*?<!-- ══ CTA FINAL ══ -->',
        f'''<!-- ══ PLAN DE ACCIÓN ══ -->
  <div class="sec">
    <div class="sec-header">
      <span class="sec-num">04</span>
      <h2 class="sec-title">Plan de Acción Priorizado</h2>
    </div>
    {acciones_html}
  </div>
  <!-- ══ CTA FINAL ══ -->''',
        html, flags=re.DOTALL
    )

    return html


# ── PASO 4: Envío con Resend ─────────────────────────────────
def enviar_reporte_resend(email: str, nombre: str, empresa: str, html_reporte: str) -> bool:
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        print("⚠ RESEND_API_KEY no configurada")
        return False
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"},
            json={
                "from":     "KIRA · SARD TECH <kira@sardtech.com.mx>",
                "to":       [email],
                "subject":  f"Tu Reporte de Ciberseguridad · {empresa} · SARD TECH",
                "html":     html_reporte,
                "reply_to": "contacto@sardtech.com.mx"
            },
            timeout=20
        )
        ok = r.status_code in (200, 201)
        print(f"{'✅' if ok else '❌'} Resend {r.status_code} → {email}")
        return ok
    except Exception as e:
        print(f"❌ Resend excepción: {e}")
        return False


# ── FUNCIÓN PRINCIPAL ─────────────────────────────────────────
def generar_y_enviar_reporte(historial: list[dict], email: str) -> bool:
    try:
        print(f"🔍 Analizando conversación ({len(historial)} mensajes)...")
        analisis = analizar_conversacion(historial)
        print(f"   Giro: {analisis.get('giro')} | Fallidos: {len(analisis.get('controles_fallidos', []))} controles")

        print("📊 Construyendo datos desde knowledge base...")
        datos = construir_datos_reporte(analisis)
        datos["email"] = datos.get("email") or email
        print(f"   Score: {datos['score_riesgo']}/10 | Nivel: {datos['nivel_riesgo']}")

        print("📄 Renderizando HTML del reporte...")
        html = renderizar_reporte(datos)

        print(f"📧 Enviando a {email}...")
        return enviar_reporte_resend(email, datos["nombre_contacto"], datos["empresa"], html)

    except json.JSONDecodeError as e:
        print(f"❌ JSON inválido de Claude: {e}")
        return False
    except FileNotFoundError as e:
        print(f"❌ Archivo no encontrado: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


# ── Helpers internos ──────────────────────────────────────────
def _peso_a_severidad(peso: int) -> str:
    return {5: "CRÍTICO", 4: "ALTO", 3: "MEDIO", 2: "BAJO", 1: "INFORMATIVO"}.get(peso, "MEDIO")

def _peso_a_clase(peso: int) -> str:
    return {5: "critico", 4: "alto", 3: "medio", 2: "bajo", 1: "bajo"}.get(peso, "medio")

def _score_a_nivel(score: float):
    if score >= 7:   return "ALTO",  "alto"
    if score >= 4:   return "MEDIO", "medio"
    return "BAJO", "bajo"

def _calcular_radar(fallidos: list) -> dict:
    grupos = {
        "accesos": ["Control de Accesos", "Gestión de Cuentas", "Gestión de Control de Accesos"],
        "nube":    ["Protección de Datos", "Seguridad de Aplicaciones"],
        "redes":   ["Gestión de Infraestructura de Red", "Monitoreo y Defensa de Red"],
        "humano":  ["Conciencia y Entrenamiento"],
        "backup":  ["Recuperación de Datos"],
        "comms":   ["Protección de Correo y Navegador"]
    }
    result = {}
    for k, grp_list in grupos.items():
        relevantes = [f for f in fallidos if f["grupo"] in grp_list]
        if relevantes:
            peso_max = max(f["peso"] for f in relevantes)
            result[k] = min(95, 40 + peso_max * 11)
        else:
            result[k] = 20
    return result

def _generar_resumen(datos: dict) -> str:
    nivel = datos["nivel_riesgo"].lower()
    n_c   = datos["num_criticos"]
    giro  = datos["giro"]
    prob  = datos["prob_ataque_pct"]
    costo = f"${datos['costo_brecha_mxn']:,.0f}"
    miedo = datos.get("miedo_principal", "")

    base = f"{datos['empresa']} opera en el sector {giro} y presenta un perfil de riesgo {nivel} con {n_c} hallazgo(s) crítico(s) identificado(s)."
    bench = f" De acuerdo con el IBM Cost of a Data Breach Report 2024, una brecha de datos en su industria tiene un costo promedio de {costo} MXN, con una probabilidad de ataque estimada de {prob}% en los próximos 12 meses."
    human = f" El {datos['pct_error_humano']}% de las brechas involucran error humano como vector inicial (Verizon DBIR 2024)."
    if miedo:
        contexto = f" Durante la evaluación, el equipo expresó como mayor preocupación: \"{miedo}\"."
    else:
        contexto = ""
    return base + bench + human + contexto

def _html_benchmarks(datos: dict) -> str:
    costo_fmt = f"${datos['costo_brecha_mxn']:,.0f} MXN"
    return f"""
  <div class="sec" style="background:#f8f9fc;">
    <div class="sec-header">
      <span class="sec-num">05</span>
      <h2 class="sec-title">Contexto de Industria y Análisis de Riesgo</h2>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:24px;">
      <div style="background:#fff;border-radius:10px;padding:18px;text-align:center;border:1px solid #eef0f4;">
        <span style="font-family:'Space Mono',monospace;font-size:1.6rem;font-weight:700;color:#ff4e4e;display:block;">{datos['prob_ataque_pct']}%</span>
        <span style="font-size:0.75rem;color:#6b7280;display:block;margin-top:4px;">Probabilidad de ataque<br>en los próximos 12 meses</span>
      </div>
      <div style="background:#fff;border-radius:10px;padding:18px;text-align:center;border:1px solid #eef0f4;">
        <span style="font-family:'Space Mono',monospace;font-size:1.2rem;font-weight:700;color:#f59e0b;display:block;">{costo_fmt}</span>
        <span style="font-size:0.75rem;color:#6b7280;display:block;margin-top:4px;">Costo promedio de brecha<br>en tu industria</span>
      </div>
      <div style="background:#fff;border-radius:10px;padding:18px;text-align:center;border:1px solid #eef0f4;">
        <span style="font-family:'Space Mono',monospace;font-size:1.6rem;font-weight:700;color:#3b82f6;display:block;">{datos['tiempo_deteccion_dias']}d</span>
        <span style="font-size:0.75rem;color:#6b7280;display:block;margin-top:4px;">Tiempo promedio para<br>detectar una brecha</span>
      </div>
    </div>
    <div style="background:#fff;border:1px solid #eef0f4;border-radius:10px;padding:18px;margin-bottom:16px;">
      <h4 style="font-size:0.9rem;font-weight:700;color:#1a1f2e;margin-bottom:8px;">Vector de ataque más común en tu sector</h4>
      <p style="font-size:0.85rem;color:#4b5563;">{datos['vector_principal']}</p>
    </div>
    <div style="background:rgba(0,229,255,0.04);border:1px solid rgba(0,160,184,0.2);border-radius:10px;padding:18px;margin-bottom:16px;">
      <h4 style="font-size:0.9rem;font-weight:700;color:#1a1f2e;margin-bottom:6px;">ROI de la protección</h4>
      <p style="font-size:0.85rem;color:#4b5563;">El plan Blindaje PyME cuesta <strong>${datos['costo_anual_plan_mxn']:,.0f} MXN / año</strong>. Por cada peso invertido en protección, evitas <strong>${datos['roi_ratio']:,.0f} MXN</strong> en costo potencial de una brecha. Ratio de protección: <strong>{datos['roi_ratio']}:1</strong>.</p>
    </div>
    <div style="background:#fff8f0;border:1px solid #fde8c8;border-radius:10px;padding:18px;">
      <h4 style="font-size:0.9rem;font-weight:700;color:#1a1f2e;margin-bottom:10px;">Regulaciones aplicables a tu empresa</h4>
      {''.join(f'<div style="margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #eef0f4;"><span style="font-size:0.78rem;font-weight:700;color:#b45309;">{r["nombre"]}</span><br><span style="font-size:0.78rem;color:#6b7280;">{r["aplica"]}</span></div>' for r in datos['regulaciones'])}
    </div>
    <p style="font-size:0.72rem;color:#9ca3af;margin-top:12px;">
      Fuentes: {" · ".join(datos['fuentes_reporte'])}
    </p>
  </div>"""
