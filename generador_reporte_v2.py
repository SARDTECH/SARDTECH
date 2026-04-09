"""
generador_reporte_v2.py — SARD TECH · KIRA Bot
Motor anti-alucinación basado en CIS Controls v8 IG1 + NIST CSF 2.0
Claude SOLO clasifica — los datos vienen del knowledge_base/
"""
import os, json, re, uuid, datetime
import anthropic, requests

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
KB_DIR     = os.path.join(BASE_DIR, "knowledge_base")
cliente_ai = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ── Carga knowledge base ──────────────────────────────────────
def _kb(nombre):
    with open(os.path.join(KB_DIR, nombre), encoding="utf-8") as f:
        return json.load(f)

CIS          = _kb("cis_controls_ig1.json")
BENCHMARKS   = _kb("benchmarks_mx.json")
CUMPLIMIENTO = _kb("cumplimiento_mx.json")
REMEDS       = _kb("remediaciones.json")


# ── Helpers ───────────────────────────────────────────────────
def _json_limpio(texto):
    texto = re.sub(r"```json|```", "", texto).strip()
    return json.loads(texto)

def _industria_datos(giro):
    giro = giro.lower().strip()
    mapa = {
        "financiero":"financiero","fintech":"financiero","banco":"financiero","seguro":"financiero",
        "salud":"salud","clínica":"salud","hospital":"salud","farmacia":"salud",
        "retail":"retail","comercio":"retail","tienda":"retail","ecommerce":"retail",
        "manufactura":"manufactura","maquiladora":"manufactura","industria":"manufactura",
        "educacion":"educacion","educación":"educacion","escuela":"educacion",
        "logistica":"logistica","logística":"logistica","transporte":"logistica",
        "gobierno":"gobierno","tecnologia":"tecnologia","tecnología":"tecnologia","software":"tecnologia",
        "servicios":"servicios_profesionales","consultoria":"servicios_profesionales",
        "despacho":"servicios_profesionales","contabilidad":"servicios_profesionales",
        "seguridad":"manufactura","equipamiento":"manufactura","proteccion":"manufactura",
    }
    for k, v in mapa.items():
        if k in giro:
            return BENCHMARKS["por_industria"].get(v, BENCHMARKS["por_industria"]["default"])
    return BENCHMARKS["por_industria"]["default"]

def _regulaciones_giro(giro):
    giro  = giro.lower()
    mapa  = CUMPLIMIENTO.get("mapa_regulacion_por_giro", {})
    clave = next((k for k in mapa if k in giro), "default")
    ids   = mapa.get(clave, mapa.get("default", []))
    return [CUMPLIMIENTO["regulaciones"][r] for r in ids if r in CUMPLIMIENTO["regulaciones"]]

def _peso_a_severidad(peso):
    return {5:"CRÍTICO",4:"ALTO",3:"MEDIO",2:"BAJO",1:"INFORMATIVO"}.get(peso,"MEDIO")

def _peso_a_clase(peso):
    return {5:"critico",4:"alto",3:"medio",2:"bajo",1:"bajo"}.get(peso,"medio")

def _score_a_nivel(score):
    if score >= 7: return "ALTO",  "alto"
    if score >= 4: return "MEDIO", "medio"
    return "BAJO", "bajo"

def _calcular_radar(fallidos):
    grupos = {
        "accesos":["Control de Accesos","Gestión de Cuentas","Gestión de Control de Accesos"],
        "nube":   ["Protección de Datos","Seguridad de Aplicaciones"],
        "redes":  ["Gestión de Infraestructura de Red","Monitoreo y Defensa de Red"],
        "humano": ["Conciencia y Entrenamiento"],
        "backup": ["Recuperación de Datos"],
        "comms":  ["Protección de Correo y Navegador"],
    }
    result = {}
    for k, grps in grupos.items():
        rel = [f for f in fallidos if f["grupo"] in grps]
        result[k] = min(95, 40 + max(f["peso"] for f in rel)*11) if rel else 20
    return result


# ── PASO 1: Claude clasifica (sin inventar) ───────────────────
def analizar_conversacion(historial):
    txt = "\n".join(
        f"{'KIRA' if m['role']=='assistant' else 'CLIENTE'}: {m['content']}"
        for m in historial
    )
    ids = [c["id"] for c in CIS["controles"]]
    prompt = f"""Eres auditor de ciberseguridad de SARD TECH. Analiza esta conversación y CLASIFICA — no inventes datos.

CONVERSACIÓN:
{txt}

CONTROLES CIS DISPONIBLES: {json.dumps(ids)}

Responde SOLO con JSON válido sin markdown:
{{
  "empresa": "nombre exacto o 'No especificado'",
  "nombre_contacto": "nombre o 'Cliente'",
  "email": "correo exacto o null",
  "giro": "uno de: financiero|salud|retail|manufactura|educacion|logistica|gobierno|tecnologia|servicios_profesionales|seguridad industrial|default",
  "tamanio_empresa": "micro (1-10)|pequena (11-50)|mediana (51-200)|grande (200+)|desconocido",
  "num_empleados": "número si se mencionó o null",
  "miedo_principal": "frase exacta o parafraseada del mayor miedo expresado, máx 25 palabras",
  "incidente_previo": true o false,
  "descripcion_incidente": "descripción si mencionó alguno, o null",
  "controles_fallidos": ["CIS-X.X"],
  "controles_presentes": ["CIS-X.X"],
  "controles_desconocidos": ["CIS-X.X"],
  "infraestructura_mencionada": "herramientas/sistemas mencionados (CRM, ERP, antivirus, etc.) o null",
  "clientes_estrategicos": "clientes importantes mencionados o null",
  "observaciones": "contexto adicional relevante, máx 80 palabras o null"
}}

REGLAS: solo incluye controles con evidencia clara. La duda va en desconocidos. Responde SOLO el JSON."""

    resp = cliente_ai.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role":"user","content":prompt}]
    )
    return _json_limpio(resp.content[0].text)


# ── PASO 2: Construir datos desde KB (cero alucinaciones) ─────
def construir_datos_reporte(analisis):
    giro         = analisis.get("giro","default")
    bench        = _industria_datos(giro)
    regulaciones = _regulaciones_giro(giro)
    ctrl_idx     = {c["id"]:c for c in CIS["controles"]}
    rem_idx      = REMEDS["remediaciones"]
    stats        = BENCHMARKS["estadisticas_generales"]
    roi          = BENCHMARKS["roi_plan_blindaje"]

    fallidos = []
    for cid in analisis.get("controles_fallidos",[]):
        ctrl = ctrl_idx.get(cid)
        if not ctrl: continue
        rem  = rem_idx.get(cid, {})
        fallidos.append({
            "id":    cid,
            "titulo": ctrl["titulo"],
            "grupo":  ctrl["grupo"],
            "peso":   ctrl["peso"],
            "categoria": ctrl["categoria"],
            "impacto":   ctrl["por_que_critico_es"],
            "estandar":  ctrl["nist_csf"],
            "severidad": _peso_a_severidad(ctrl["peso"]),
            "clase":     _peso_a_clase(ctrl["peso"]),
            "acciones":  rem.get("acciones",[]),
            "herramientas_gratuitas": rem.get("herramientas_gratuitas",[]),
            "tiempo":    rem.get("tiempo_implementacion","Variable"),
            "costo_mxn": rem.get("costo_estimado_mxn",0),
            "fuente":    rem.get("fuente_dato_impacto", ctrl["nist_csf"]),
            "plan":      rem.get("incluido_en_plan","Blindaje PyME"),
        })
    fallidos.sort(key=lambda x: x["peso"], reverse=True)

    peso_total  = sum(c["peso"] for c in ctrl_idx.values())
    peso_fall   = sum(f["peso"] for f in fallidos)
    score       = min(10.0, round((peso_fall / max(peso_total,1))*10, 1))
    num_c       = len([f for f in fallidos if f["peso"]>=5])
    num_a       = len([f for f in fallidos if f["peso"]==4])
    num_m       = len([f for f in fallidos if f["peso"]<=3])
    nivel, cls  = _score_a_nivel(score)
    prob        = min(98, bench["probabilidad_ataque_12m"] + num_c*3)

    acciones = []
    for i,f in enumerate(fallidos[:5],1):
        pl = "inmediato" if f["peso"]>=5 else ("corto" if f["peso"]==4 else "mediano")
        etq = {"inmediato":"⚡ INMEDIATO — Esta semana","corto":"◉ CORTO PLAZO — Primer mes","mediano":"◈ MEDIANO PLAZO — 30-60 días"}[pl]
        acciones.append({
            "num": i,
            "titulo": f["acciones"][0] if f["acciones"] else f["titulo"],
            "desc":   f["acciones"][1] if len(f["acciones"])>1 else f["impacto"][:120]+"…",
            "plazo":  pl, "etiqueta": etq,
            "costo":  f["costo_mxn"],
            "gratis": f["herramientas_gratuitas"][0] if f["herramientas_gratuitas"] else None,
            "fuente": f["fuente"],
        })

    regs_display = []
    for r in regulaciones[:3]:
        regs_display.append({
            "nombre": r.get("nombre_completo",""),
            "aplica": r.get("aplica_a",""),
            "riesgo": r.get("riesgo_incumplimiento",""),
        })

    return {
        "empresa":           analisis.get("empresa","Tu empresa"),
        "contacto":          analisis.get("nombre_contacto","Cliente"),
        "email":             analisis.get("email",""),
        "giro":              bench["nombre_display"],
        "tamanio":           analisis.get("tamanio_empresa","desconocido"),
        "num_empleados":     analisis.get("num_empleados",""),
        "miedo":             analisis.get("miedo_principal",""),
        "incidente_previo":  analisis.get("incidente_previo",False),
        "desc_incidente":    analisis.get("descripcion_incidente",""),
        "infraestructura":   analisis.get("infraestructura_mencionada",""),
        "clientes":          analisis.get("clientes_estrategicos",""),
        "observaciones":     analisis.get("observaciones",""),
        "score":             score,
        "nivel":             nivel,
        "clase_riesgo":      cls,
        "num_criticos":      num_c,
        "num_altos":         num_a,
        "num_medios":        num_m,
        "fallidos":          fallidos,
        "acciones":          acciones,
        "regulaciones":      regs_display,
        "radar":             _calcular_radar(fallidos),
        # Datos reales del KB — jamás inventados
        "costo_brecha_mxn":  bench["costo_brecha_mxn"],
        "prob_ataque":       prob,
        "tiempo_deteccion":  bench["tiempo_deteccion_dias"],
        "vector_principal":  bench["vector_ataque_principal"],
        "fuente_bench":      bench["fuente_costo"],
        "roi_ratio":         roi["ratio_proteccion_inversion"],
        "costo_anual_plan":  roi["costo_anual_mxn"],
        "pct_error_humano":  stats["pct_brechas_por_error_humano"],
        "fuentes":           [
            "IBM Cost of a Data Breach Report 2024",
            "Verizon Data Breach Investigations Report 2024",
            "CIS Controls v8 — Center for Internet Security",
            "Proofpoint State of the Phish 2024",
            "LFPDPPP — INAI México 2024",
        ],
    }


# ── PASO 3: Generar HTML del email (autocontenido) ─────────────
def generar_html_email(d):
    folio = f"SARD-{datetime.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    fecha = datetime.date.today().strftime("%d de %B de %Y")

    # Colores por nivel de riesgo
    colores = {
        "alto":  {"bg":"#fff5f5","borde":"#ff4e4e","texto":"#cc2222","label":"RIESGO ALTO"},
        "medio": {"bg":"#fffbf0","borde":"#f59e0b","texto":"#b45309","label":"RIESGO MEDIO"},
        "bajo":  {"bg":"#f0fff4","borde":"#22c55e","texto":"#15803d","label":"RIESGO BAJO"},
    }
    col = colores.get(d["clase_riesgo"], colores["alto"])

    sev_color = {"critico":"#ff4e4e","alto":"#f59e0b","medio":"#3b82f6","bajo":"#22c55e"}
    sev_bg    = {"critico":"#fff5f5","alto":"#fffbf0","medio":"#f0f7ff","bajo":"#f0fff4"}

    # Hallazgos HTML
    hallazgos_html = ""
    for f in d["fallidos"]:
        c    = f["clase"]
        acc1 = f["acciones"][0] if f["acciones"] else "Consultar con un especialista de SARD TECH."
        grat = f"<br><small style='color:#059669;'>Herramienta gratuita: {f['herramientas_gratuitas'][0]}</small>" if f.get("herramientas_gratuitas") else ""
        hallazgos_html += f"""
        <div style="border-left:4px solid {sev_color.get(c,'#888')};background:{sev_bg.get(c,'#f8f9fc')};border-radius:0 8px 8px 0;padding:16px 18px;margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;gap:12px;">
            <strong style="font-size:14px;color:#1a1f2e;flex:1;">{f['titulo']}</strong>
            <span style="background:{sev_color.get(c,'#888')};color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:100px;white-space:nowrap;">{f['severidad']}</span>
          </div>
          <p style="font-size:13px;color:#4b5563;line-height:1.6;margin-bottom:10px;">{f['impacto']}</p>
          <div style="background:rgba(0,0,0,0.04);border-radius:6px;padding:10px 12px;font-size:13px;color:#1a1f2e;">
            <strong style="color:#0891b2;">Acción recomendada:</strong> {acc1}{grat}
          </div>
          <p style="font-size:11px;color:#9ca3af;margin-top:8px;">Fuente: {f['fuente']} · Estándar: {f['estandar']}</p>
        </div>"""

    # Acciones HTML
    acciones_html = ""
    plazo_color = {"inmediato":"#ff4e4e","corto":"#f59e0b","mediano":"#3b82f6"}
    for a in d["acciones"]:
        costo_txt = "Sin costo" if a["costo"]==0 else f"${a['costo']:,.0f} MXN"
        gratis_txt = f" · Herramienta gratuita: {a['gratis']}" if a.get("gratis") else ""
        acciones_html += f"""
        <div style="display:flex;gap:14px;align-items:flex-start;padding:14px 0;border-bottom:1px solid #eef0f4;">
          <div style="width:32px;height:32px;border-radius:50%;background:#00a0b8;color:#fff;font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">{a['num']}</div>
          <div style="flex:1;">
            <strong style="font-size:14px;color:#1a1f2e;display:block;margin-bottom:4px;">{a['titulo']}</strong>
            <p style="font-size:13px;color:#4b5563;margin-bottom:6px;">{a['desc']}</p>
            <span style="display:inline-block;font-size:11px;font-weight:700;color:{plazo_color.get(a['plazo'],'#888')};background:rgba(0,0,0,0.05);padding:3px 10px;border-radius:4px;">{a['etiqueta']}</span>
            <span style="font-size:11px;color:#9ca3af;margin-left:8px;">{costo_txt}{gratis_txt}</span>
            <p style="font-size:11px;color:#9ca3af;margin-top:4px;">Fuente: {a['fuente']}</p>
          </div>
        </div>"""

    # Regulaciones HTML
    regs_html = ""
    for r in d["regulaciones"]:
        riesgo_col = {"CRÍTICO":"#ff4e4e","MUY ALTO":"#ff4e4e","ALTO":"#f59e0b","MEDIO-ALTO":"#f59e0b","MEDIO":"#3b82f6"}.get(r["riesgo"],"#888")
        regs_html += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #eef0f4;font-size:13px;font-weight:600;color:#1a1f2e;vertical-align:top;">{r['nombre']}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #eef0f4;font-size:12px;color:#4b5563;vertical-align:top;">{r['aplica']}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #eef0f4;font-size:12px;font-weight:700;color:{riesgo_col};vertical-align:top;white-space:nowrap;">{r['riesgo']}</td>
        </tr>"""

    # Sección de infraestructura si existe
    infra_html = ""
    if d.get("infraestructura"):
        infra_html = f"""
        <tr>
          <td style="padding:10px 0;font-size:13px;color:#6b7280;width:160px;vertical-align:top;">Infraestructura</td>
          <td style="padding:10px 0;font-size:13px;color:#1a1f2e;font-weight:500;">{d['infraestructura']}</td>
        </tr>"""

    clientes_html = ""
    if d.get("clientes"):
        clientes_html = f"""
        <tr>
          <td style="padding:10px 0;font-size:13px;color:#6b7280;width:160px;">Clientes clave</td>
          <td style="padding:10px 0;font-size:13px;color:#1a1f2e;font-weight:500;">{d['clientes']}</td>
        </tr>"""

    incidente_html = ""
    if d.get("incidente_previo") and d.get("desc_incidente"):
        incidente_html = f"""
        <div style="background:#fff5f5;border:1px solid #ff4e4e;border-radius:8px;padding:14px 16px;margin-bottom:20px;">
          <strong style="font-size:13px;color:#cc2222;">⚠ Incidente previo registrado:</strong>
          <p style="font-size:13px;color:#4b5563;margin-top:6px;">{d['desc_incidente']}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Reporte de Diagnóstico SARD TECH — {d['empresa']}</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:680px;margin:0 auto;background:#ffffff;">

  <!-- PORTADA -->
  <div style="background:#080c10;padding:48px 40px 36px;text-align:center;">
    <div style="font-size:24px;font-weight:900;color:#00e5ff;letter-spacing:4px;margin-bottom:4px;">SARD TECH</div>
    <div style="font-size:11px;color:#7d8590;letter-spacing:2px;margin-bottom:36px;">// CYBERSECURITY AI PLATFORM · KIRA</div>
    <div style="display:inline-block;background:rgba(0,229,255,0.1);border:1px solid rgba(0,229,255,0.35);color:#00e5ff;font-size:11px;padding:6px 18px;border-radius:100px;letter-spacing:2px;margin-bottom:20px;">DIAGNÓSTICO CONFIDENCIAL</div>
    <h1 style="font-size:28px;font-weight:900;color:#e6edf3;margin:0 0 10px;">Reporte de<br><span style="color:#00e5ff;">Vulnerabilidades</span></h1>
    <p style="font-size:13px;color:#7d8590;margin:0;">Análisis basado en CIS Controls v8 IG1 · NIST CSF 2.0 · LFPDPPP</p>
    <div style="display:flex;justify-content:center;gap:32px;margin-top:28px;padding-top:24px;border-top:1px solid rgba(0,229,255,0.12);flex-wrap:wrap;">
      <div style="text-align:center;"><div style="font-size:11px;color:#7d8590;margin-bottom:4px;">EMPRESA</div><div style="font-size:14px;color:#e6edf3;font-weight:700;">{d['empresa']}</div></div>
      <div style="text-align:center;"><div style="font-size:11px;color:#7d8590;margin-bottom:4px;">CONTACTO</div><div style="font-size:14px;color:#e6edf3;font-weight:700;">{d['contacto']}</div></div>
      <div style="text-align:center;"><div style="font-size:11px;color:#7d8590;margin-bottom:4px;">FECHA</div><div style="font-size:14px;color:#e6edf3;font-weight:700;">{fecha}</div></div>
      <div style="text-align:center;"><div style="font-size:11px;color:#7d8590;margin-bottom:4px;">FOLIO</div><div style="font-size:14px;color:#e6edf3;font-weight:700;">{folio}</div></div>
    </div>
  </div>

  <!-- NIVEL DE RIESGO -->
  <div style="background:{col['bg']};border-left:6px solid {col['borde']};padding:24px 32px;display:flex;align-items:center;gap:24px;">
    <div style="text-align:center;flex-shrink:0;">
      <div style="font-size:40px;font-weight:900;color:{col['borde']};line-height:1;">{d['score']}</div>
      <div style="font-size:11px;color:#6b7280;">/10</div>
    </div>
    <div>
      <div style="display:inline-block;background:{col['borde']};color:#fff;font-size:11px;font-weight:700;padding:3px 12px;border-radius:100px;margin-bottom:8px;">{col['label']}</div>
      <h2 style="font-size:16px;font-weight:700;color:#1a1f2e;margin:0 0 6px;">Tu empresa presenta {d['num_criticos']} hallazgo(s) crítico(s) y {d['num_altos']} de alto impacto</h2>
      <p style="font-size:13px;color:#4b5563;margin:0;">Se requiere atención inmediata para proteger la continuidad del negocio.</p>
    </div>
  </div>

  <!-- RESUMEN EJECUTIVO -->
  <div style="padding:36px 40px;border-bottom:1px solid #eef0f4;">
    <h2 style="font-size:18px;font-weight:800;color:#1a1f2e;margin:0 0 16px;padding-left:12px;border-left:4px solid #00a0b8;">01 · Resumen Ejecutivo</h2>
    <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
      <div style="flex:1;min-width:120px;background:#f8f9fc;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:28px;font-weight:900;color:#ff4e4e;">{d['num_criticos']}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">Hallazgos Críticos</div>
      </div>
      <div style="flex:1;min-width:120px;background:#f8f9fc;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:28px;font-weight:900;color:#f59e0b;">{d['num_altos']}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">Riesgo Alto</div>
      </div>
      <div style="flex:1;min-width:120px;background:#f8f9fc;border-radius:8px;padding:16px;text-align:center;">
        <div style="font-size:28px;font-weight:900;color:#3b82f6;">{d['num_medios']}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">Riesgo Medio/Bajo</div>
      </div>
    </div>
    {incidente_html}
    <p style="font-size:14px;color:#374151;line-height:1.75;">{d['empresa']} opera en el sector <strong>{d['giro']}</strong> y presenta un perfil de riesgo <strong>{d['nivel'].lower()}</strong>. De acuerdo con el IBM Cost of a Data Breach Report 2024, una brecha de datos en su industria tiene un costo promedio de <strong>${d['costo_brecha_mxn']:,.0f} MXN</strong>, con una probabilidad de ataque estimada de <strong>{d['prob_ataque']}%</strong> en los próximos 12 meses. El {d['pct_error_humano']}% de las brechas involucran error humano como vector inicial (Verizon DBIR 2024).</p>
    {f'<p style="font-size:13px;color:#6b7280;margin-top:12px;font-style:italic;">Mayor preocupación expresada: "{d["miedo"]}"</p>' if d.get("miedo") else ""}
  </div>

  <!-- PERFIL DE LA EMPRESA -->
  <div style="padding:36px 40px;border-bottom:1px solid #eef0f4;">
    <h2 style="font-size:18px;font-weight:800;color:#1a1f2e;margin:0 0 20px;padding-left:12px;border-left:4px solid #00a0b8;">02 · Perfil de la Empresa</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <tr style="background:#f8f9fc;">
        <td style="padding:12px 16px;color:#6b7280;font-weight:600;width:160px;border-bottom:1px solid #eef0f4;">Razón Social</td>
        <td style="padding:12px 16px;color:#1a1f2e;font-weight:700;border-bottom:1px solid #eef0f4;">{d['empresa']}</td>
      </tr>
      <tr>
        <td style="padding:12px 16px;color:#6b7280;font-weight:600;border-bottom:1px solid #eef0f4;">Sector</td>
        <td style="padding:12px 16px;color:#1a1f2e;border-bottom:1px solid #eef0f4;">{d['giro']}</td>
      </tr>
      <tr style="background:#f8f9fc;">
        <td style="padding:12px 16px;color:#6b7280;font-weight:600;border-bottom:1px solid #eef0f4;">Tamaño</td>
        <td style="padding:12px 16px;color:#1a1f2e;border-bottom:1px solid #eef0f4;">{d['tamanio']}{(' · ' + str(d['num_empleados']) + ' colaboradores') if d.get('num_empleados') else ''}</td>
      </tr>
      {('<tr><td style="padding:12px 16px;color:#6b7280;font-weight:600;border-bottom:1px solid #eef0f4;">Infraestructura</td><td style="padding:12px 16px;color:#1a1f2e;border-bottom:1px solid #eef0f4;">' + d['infraestructura'] + '</td></tr>') if d.get('infraestructura') else ''}
      {('<tr style="background:#f8f9fc;"><td style="padding:12px 16px;color:#6b7280;font-weight:600;">Clientes clave</td><td style="padding:12px 16px;color:#1a1f2e;font-weight:600;color:#0891b2;">' + d['clientes'] + '</td></tr>') if d.get('clientes') else ''}
    </table>
  </div>

  <!-- HALLAZGOS -->
  <div style="padding:36px 40px;border-bottom:1px solid #eef0f4;">
    <h2 style="font-size:18px;font-weight:800;color:#1a1f2e;margin:0 0 20px;padding-left:12px;border-left:4px solid #00a0b8;">03 · Hallazgos Detallados</h2>
    {hallazgos_html}
  </div>

  <!-- CONTEXTO DE INDUSTRIA -->
  <div style="padding:36px 40px;background:#f8f9fc;border-bottom:1px solid #eef0f4;">
    <h2 style="font-size:18px;font-weight:800;color:#1a1f2e;margin:0 0 20px;padding-left:12px;border-left:4px solid #00a0b8;">04 · Contexto de Industria</h2>
    <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
      <div style="flex:1;min-width:140px;background:#fff;border-radius:8px;padding:16px;text-align:center;border:1px solid #eef0f4;">
        <div style="font-size:26px;font-weight:900;color:#ff4e4e;">{d['prob_ataque']}%</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">Probabilidad de ataque<br>en 12 meses</div>
      </div>
      <div style="flex:1;min-width:140px;background:#fff;border-radius:8px;padding:16px;text-align:center;border:1px solid #eef0f4;">
        <div style="font-size:16px;font-weight:900;color:#f59e0b;">${d['costo_brecha_mxn']:,.0f}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">Costo promedio de brecha<br>en tu industria (MXN)</div>
      </div>
      <div style="flex:1;min-width:140px;background:#fff;border-radius:8px;padding:16px;text-align:center;border:1px solid #eef0f4;">
        <div style="font-size:26px;font-weight:900;color:#3b82f6;">{d['tiempo_deteccion']}d</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">Tiempo promedio para<br>detectar una brecha</div>
      </div>
    </div>
    <div style="background:#fff;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #eef0f4;">
      <strong style="font-size:13px;color:#1a1f2e;">Vector de ataque principal en tu sector:</strong>
      <p style="font-size:13px;color:#4b5563;margin-top:6px;">{d['vector_principal']}</p>
    </div>
    <div style="background:#e0f7fa;border-radius:8px;padding:16px;border:1px solid #b2ebf2;">
      <strong style="font-size:13px;color:#1a1f2e;">ROI de la protección:</strong>
      <p style="font-size:13px;color:#374151;margin-top:6px;">El plan Blindaje PyME cuesta <strong>${d['costo_anual_plan']:,.0f} MXN/año</strong>. Por cada peso invertido, evitas <strong>${d['roi_ratio']:,.0f} MXN</strong> en costo potencial de una brecha. Ratio de protección: <strong>{d['roi_ratio']}:1</strong>.</p>
    </div>
    <p style="font-size:11px;color:#9ca3af;margin-top:12px;">Fuente: {d['fuente_bench']}</p>
  </div>

  <!-- PLAN DE ACCIÓN -->
  <div style="padding:36px 40px;border-bottom:1px solid #eef0f4;">
    <h2 style="font-size:18px;font-weight:800;color:#1a1f2e;margin:0 0 20px;padding-left:12px;border-left:4px solid #00a0b8;">05 · Plan de Acción Priorizado</h2>
    {acciones_html}
  </div>

  <!-- REGULACIONES -->
  <div style="padding:36px 40px;border-bottom:1px solid #eef0f4;">
    <h2 style="font-size:18px;font-weight:800;color:#1a1f2e;margin:0 0 20px;padding-left:12px;border-left:4px solid #00a0b8;">06 · Marco Regulatorio Aplicable</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="background:#f8f9fc;">
          <th style="padding:10px 16px;text-align:left;font-size:11px;color:#6b7280;border-bottom:2px solid #eef0f4;">REGULACIÓN</th>
          <th style="padding:10px 16px;text-align:left;font-size:11px;color:#6b7280;border-bottom:2px solid #eef0f4;">APLICA A</th>
          <th style="padding:10px 16px;text-align:left;font-size:11px;color:#6b7280;border-bottom:2px solid #eef0f4;">NIVEL DE RIESGO</th>
        </tr>
      </thead>
      <tbody>{regs_html}</tbody>
    </table>
  </div>

  <!-- CTA FINAL -->
  <div style="background:#080c10;padding:40px;text-align:center;">
    <h2 style="font-size:22px;font-weight:900;color:#e6edf3;margin:0 0 12px;">¿Listo para <span style="color:#00e5ff;">blindar</span> tu empresa?</h2>
    <p style="font-size:14px;color:#7d8590;margin:0 0 28px;line-height:1.65;">Un especialista de SARD TECH revisará estos hallazgos contigo<br>en las próximas 24 horas sin costo ni compromiso.</p>
    <table style="margin:0 auto;border-collapse:collapse;">
      <tr>
        <td style="padding:0 8px;">
          <a href="https://wa.me/525633212240?text=Hola,%20recibí%20mi%20reporte%20de%20KIRA%20y%20quiero%20hablar%20con%20un%20especialista" style="display:inline-block;background:#25D366;color:#fff;font-size:14px;font-weight:700;padding:14px 28px;border-radius:8px;text-decoration:none;">WhatsApp</a>
        </td>
        <td style="padding:0 8px;">
          <a href="mailto:contacto@sardtech.com.mx?subject=Seguimiento%20reporte%20KIRA%20—%20{d['empresa']}" style="display:inline-block;background:#00e5ff;color:#000;font-size:14px;font-weight:700;padding:14px 28px;border-radius:8px;text-decoration:none;">Correo</a>
        </td>
      </tr>
    </table>
  </div>

  <!-- FOOTER -->
  <div style="background:#0d1117;padding:20px 40px;text-align:center;">
    <p style="font-size:12px;color:#4a5058;margin:0;">© {datetime.date.today().year} SARD TECH · Cybersecurity AI Platform · sardtech.com.mx</p>
    <p style="font-size:11px;color:#374151;margin-top:6px;">Fuentes: {" · ".join(d['fuentes'])}</p>
    <p style="font-size:11px;color:#4a5058;margin-top:4px;">Folio: {folio} · Documento confidencial generado por KIRA IA</p>
  </div>

</div>
</body>
</html>"""


# ── PASO 4: Envío con Resend ──────────────────────────────────
def enviar_reporte_resend(email, nombre, empresa, html):
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        print("⚠ RESEND_API_KEY no configurada")
        return False
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","Accept":"application/json"},
            json={
                "from":     "KIRA · SARD TECH <kira@sardtech.com.mx>",
                "to":       [email],
                "subject":  f"Tu Reporte de Ciberseguridad · {empresa} · SARD TECH",
                "html":     html,
                "reply_to": "contacto@sardtech.com.mx",
            },
            timeout=20
        )
        ok = r.status_code in (200,201)
        print(f"{'✅' if ok else '❌'} Resend {r.status_code} → {email}")
        return ok
    except Exception as e:
        print(f"❌ Resend excepción: {e}")
        return False


# ── FUNCIÓN PRINCIPAL ─────────────────────────────────────────
def generar_y_enviar_reporte(historial, email):
    try:
        print(f"🔍 Analizando conversación ({len(historial)} mensajes)…")
        analisis = analizar_conversacion(historial)
        print(f"   Empresa: {analisis.get('empresa')} | Fallidos: {len(analisis.get('controles_fallidos',[]))}")

        print("📊 Construyendo datos desde knowledge base…")
        datos = construir_datos_reporte(analisis)
        datos["email"] = datos.get("email") or email
        print(f"   Score: {datos['score']}/10 | Nivel: {datos['nivel']}")

        print("📄 Generando HTML del email…")
        html = generar_html_email(datos)

        print(f"📧 Enviando a {email}…")
        return enviar_reporte_resend(email, datos["contacto"], datos["empresa"], html)

    except json.JSONDecodeError as e:
        print(f"❌ JSON inválido de Claude: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback; traceback.print_exc()
        return False
