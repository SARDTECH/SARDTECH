"""
app.py — SARD TECH · KIRA Bot v2.0 + Chiki Bot v1.0
Columnas Supabase reales: id, rol, mensaje, creado_en, session_id
+ email_capturado, reporte_enviado (agregadas en el Paso 1)
"""
import os, re, uuid, datetime, threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
from supabase import create_client, Client
from generador_reporte_v2 import generar_y_enviar_reporte

app = Flask(__name__)
CORS(app)

cliente_ai = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

TABLA = "chats_sardtech"

# ══════════════════════════════════════════════════════════════
# KIRA SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════

KIRA_SYSTEM_PROMPT = """Eres KIRA, la auditora de ciberseguridad con IA de SARD TECH. Tu misión es realizar un diagnóstico profesional de ciberseguridad basado en CIS Controls v8 IG1 y NIST CSF 2.0.

════════════════════════════════════════
CARÁCTER Y TONO
════════════════════════════════════════
- Habla como una asesora experta y de confianza — cercana pero profesional
- Usa lenguaje claro, sin tecnicismos — el cliente es dueño o director de PyME, NO es técnico
- Sé empática: valida sus preocupaciones sin ser alarmista
- UNA sola pregunta por mensaje — nunca más de una a la vez
- Respuestas cortas. Máximo 3-4 líneas por mensaje

════════════════════════════════════════
FLUJO — 4 FASES OBLIGATORIAS
════════════════════════════════════════

FASE 1 — PERFIL (mensajes 1-3)
Msg 1: "¡Hola! Soy KIRA, tu auditora de ciberseguridad de SARD TECH. Voy a hacerte un diagnóstico gratuito basado en CIS Controls v8 y NIST CSF 2.0 — son solo 8 preguntas, menos de 5 minutos. Para empezar: ¿cuál es el nombre de tu empresa y a qué se dedica?"
Msg 2: Pregunta cuántas personas trabajan en la empresa.
Msg 3 (Golden Question): "Pregunta clave: si mañana amanecieran sin poder acceder a ningún sistema ni archivo de la empresa, ¿qué sería lo primero que les preocuparía perder?"

FASE 2 — DIAGNÓSTICO CIS IG1 (mensajes 4-11, uno por uno)
1. "Cuando alguien deja de trabajar en su empresa, ¿sus accesos al correo y sistemas se cancelan ese mismo día?"
2. "¿Para entrar al correo o sistemas desde fuera de la oficina necesitan un código extra además de la contraseña?"
3. "¿Tienen copias automáticas de sus archivos importantes, o alguien tiene que recordar hacerlas manualmente?"
4. "¿Esas copias están en la misma oficina o en otro lugar — nube o disco externo fuera de las instalaciones?"
5. "¿Su equipo ha recibido capacitación sobre cómo reconocer correos falsos o fraudes digitales en el último año?"
6. "¿Las computadoras de la empresa tienen activadas las actualizaciones automáticas de Windows o Mac?"
7. "¿Todas las computadoras tienen antivirus activo y actualizado, o hay equipos sin protección?"
8. "¿La red Wi-Fi es la misma para empleados, visitas y dispositivos como impresoras, o están separadas?"

FASE 3 — CAPTURA (mensajes 12-13)
Msg 12: "Perfecto, ya tengo todo para tu diagnóstico. Voy a generar un reporte profesional sustentado en CIS v8, NIST CSF 2.0, LFPDPPP y datos reales del mercado mexicano (IBM 2024, Verizon DBIR 2024). ¿A qué correo te lo enviamos?"
Msg 13: Confirma el correo y pregunta el nombre completo.

FASE 4 — CIERRE (mensaje 14)
"¡Listo, [nombre]! Tu reporte está siendo generado ahora mismo. Llegará a [correo] en unos minutos. Un especialista de SARD TECH te contactará en las próximas 24 horas para revisar los hallazgos contigo. ¿Alguna pregunta mientras tanto?"

════════════════════════════════════════
REGLAS CRÍTICAS
════════════════════════════════════════
1. NUNCA inventes estadísticas o porcentajes — eso lo hace el reporte con fuentes reales
2. NUNCA digas "tu empresa tiene X% de riesgo" en el chat
3. NUNCA más de 1 pregunta por mensaje
4. NUNCA saltes la Fase 1
5. Si el cliente menciona hackeo, ransomware o fraude previo: empatía primero, luego acelera la captura del correo
6. Adapta contexto al giro: financiero→CNBV, salud→datos de pacientes, retail→datos de clientes

SUSTENTO DEL REPORTE: CIS Controls v8 IG1 · NIST CSF 2.0 · LFPDPPP · NOM-151-SCFI-2016 · IBM Cost of Data Breach 2024 · Verizon DBIR 2024"""


# ══════════════════════════════════════════════════════════════
# CHIKI SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════

CHIKI_SYSTEM_PROMPT = """Eres Chiki, asistente de Carnicería La Chiquita (Acamapichtli 66, Col. La Preciosa, Azcapotzalco, CDMX). Hablas español mexicano natural y directo.

REGLA ANTI-ALUCINACIÓN: SOLO habla de productos del catálogo. Si no está → "Eso no lo manejo todavía, pregúntale a Raúl por WhatsApp."
NUNCA inventes precios ni productos.

ERRORES ORTOGRÁFICOS: Reconoce variaciones coloquiales:
aumada/ahumda/umada→Chuleta Ahumada, bisteck/bistek/bisteak→Bistec, chambarete/chanbarete→Chambarete, chicharron/chicharón→Chicharrón, longanisa→Longaniza, cecina/cesina→Cecina, macisa/masiza→Maciza, moida/molda→Molida, pexuga/pachuga→Pechuga, arrachera/arracha→Arrachera, salmon→Salmón, tilapea→Tilapia
Si suena parecido confirma: "¿Te refieres a [PRODUCTO]?"

PRINCIPIOS:
- Ve directo. Sin "¡Con gusto!". Sin frases de relleno.
- Máximo 4 opciones a la vez.
- Guía paso a paso: producto→corte→uso→cantidad→pickup o entrega.
- Si pide mucho pregunta si es para restaurante o evento.

HORARIOS: Lun-Sáb 7am-6pm · Dom 8am-6pm | TEL: 55 5884 9504

CATÁLOGO RES(/kg): Bistec $250(delgado/grueso/aplanado/picado, bola/aguayón/magro), Puntas Filete $250(trozos/fajitas/enteras), Costilla Asar $260(gruesa/tablita/tira/rack), Falda Deshebrar $250, Maciza $250(cubos/trozos), Molida $210(normal/doble, comercial/magra/mixta), Retazo $185, Chambarete c/H $190(rodajas/trozos,tuétano), Chambarete Macizo $250, Aguja Norteña $195(steak/delgado/mariposa), Arrachera Marinada $250(entera/picada/fajitas).

CATÁLOGO CERDO(/kg): Espaldilla $130, Bistec cerdo $130(aplanado/grueso/tiritas), Maciza cerdo $130, Molida cerdo $130, Pulpa $130, Cabeza Lomo $140(marmoleada), Espinazo $120, Manitas $65(mitades/enteras,crudas/cocidas), Codillo $75, Cabeza $65, Costilla Falda $140(cargada), Lomo c/H $140(chuletas gruesas/delgadas), Caña Lomo $150(entera/medallones/mechada), Longaniza $130, Chorizo $140(bolitas/suelto), Chorizo Argentino $185(fresco), Chistorra $140(espiral/trocitos), Tocino $168(rebanado/trozo,ahumado), Chuleta Ahumada $130(normal/gruesa), Chicharrón Prensado $130(trozo/picado), Chicharrón Esponjado $240, Chicharrón Carnudo $260, Manteca $60, Cecina Enchilada $150(rebanada/picada,Yecapixtla).

CATÁLOGO POLLO(/kg): Pechuga $120(aplanada milanesa/fajitas/cubos/entera/mitades, sin piel/con piel/molida), Pierna y Muslo $55(cuarto/separados/deshuesado muslo, sin piel/con piel/con cortaditas).

CATÁLOGO PESCADO: Tilapia $85/kg, Salmón $160 paquete 400g.

ESPECIALIDADES (sin precio): Chimichurri, Queso Provolone, Arrachera Marinada, Chorizo Argentino, Cecina, Chistorra, Hamburguesas, Jamón → "Para precios pregúntale a Raúl directo."

FLUJO PEDIDO:
1. ¿Qué carne? (máx 4 opciones)
2. ¿Corte/presentación? (máx 4 opciones del catálogo)
3. ¿Uso/platillo? (si aplica)
4. ¿Cuántos kg?
5. ¿Recoges en tienda o entrega a domicilio?
   - Tienda: confirma Acamapichtli 66, La Preciosa. ¿A qué hora?
   - Domicilio: ¿En qué colonia?
     * Azcapotzalco → confirma, Raúl contacta por WhatsApp.
     * Fuera de Azcapotzalco → "Solo entregamos en Azcapotzalco. ¿Puedes pasar a Acamapichtli 66?"
6. Resume pedido completo y di que confirmarán por WhatsApp al 55 5884 9504."""


# ── Helpers KIRA ──────────────────────────────────────────────

def extraer_email(texto: str) -> str | None:
    m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", texto)
    return m.group(0).lower() if m else None


def obtener_historial(session_id: str) -> list[dict]:
    try:
        r = (supabase.table(TABLA)
             .select("rol, mensaje")
             .eq("session_id", session_id)
             .order("creado_en", desc=False)
             .execute())
        return r.data or []
    except Exception as e:
        print(f"⚠ Supabase get: {e}")
        return []


def guardar_mensaje(session_id: str, rol: str, mensaje: str,
                    email: str | None = None,
                    reporte_enviado: bool = False) -> None:
    try:
        registro = {
            "session_id":  session_id,
            "rol":         rol,
            "mensaje":     mensaje,
            "creado_en":   datetime.datetime.utcnow().isoformat(),
        }
        if email:
            registro["email_capturado"] = email
        if reporte_enviado:
            registro["reporte_enviado"] = True
        supabase.table(TABLA).insert(registro).execute()
    except Exception as e:
        print(f"⚠ Supabase save: {e}")


def reporte_ya_enviado(session_id: str) -> bool:
    try:
        r = (supabase.table(TABLA)
             .select("reporte_enviado")
             .eq("session_id", session_id)
             .eq("reporte_enviado", True)
             .limit(1)
             .execute())
        return len(r.data) > 0
    except:
        return False


# ── Ruta KIRA ─────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    datos      = request.get_json(silent=True) or {}
    mensaje    = datos.get("mensaje", "").strip()
    session_id = datos.get("session_id", str(uuid.uuid4()))

    if mensaje.lower() == "ping":
        return jsonify({"respuesta": "ok", "reporte_enviado": False})

    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400

    historial = obtener_historial(session_id)
    guardar_mensaje(session_id, "user", mensaje)

    mensajes_claude = []
    for h in historial:
        if h.get("rol") in ("user", "assistant"):
            mensajes_claude.append({
                "role":    h["rol"],
                "content": h["mensaje"]
            })
    mensajes_claude.append({"role": "user", "content": mensaje})

    try:
        resp = cliente_ai.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=KIRA_SYSTEM_PROMPT,
            messages=mensajes_claude
        )
        texto_resp = resp.content[0].text
    except Exception as e:
        print(f"❌ Claude KIRA: {e}")
        return jsonify({
            "respuesta":       "Estoy teniendo un problema técnico momentáneo. Por favor intenta de nuevo en unos segundos.",
            "reporte_enviado": False
        })

    reporte_enviado  = False
    email_detectado  = extraer_email(mensaje)

    if email_detectado and not reporte_ya_enviado(session_id):
        print(f"📧 Email: {email_detectado} | Sesión: {session_id}")
        historial_completo = historial + [
            {"rol": "user",      "mensaje": mensaje},
            {"rol": "assistant", "mensaje": texto_resp}
        ]
        historial_formato_reporte = [
            {"role": h["rol"], "content": h["mensaje"]}
            for h in historial_completo
        ]
        def enviar_bg():
            generar_y_enviar_reporte(historial_formato_reporte, email_detectado)
        threading.Thread(target=enviar_bg, daemon=True).start()
        reporte_enviado = True
        guardar_mensaje(session_id, "assistant", texto_resp,
                        email=email_detectado, reporte_enviado=True)
    else:
        guardar_mensaje(session_id, "assistant", texto_resp)

    return jsonify({
        "respuesta":       texto_resp,
        "reporte_enviado": reporte_enviado
    })


# ── Ruta CHIKI ────────────────────────────────────────────────

@app.route("/chiki", methods=["POST"])
def chiki():
    try:
        data = request.get_json(silent=True) or {}
        messages = data.get("messages", [])

        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        resp = cliente_ai.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=CHIKI_SYSTEM_PROMPT,
            messages=messages
        )
        reply = resp.content[0].text
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"❌ Claude Chiki: {e}")
        return jsonify({"error": str(e)}), 500


# ── Health check ──────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":   "ok",
        "services": ["KIRA · SARD TECH v2.0", "Chiki · La Chiquita v1.0"]
    })


# ── Arranque ──────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
