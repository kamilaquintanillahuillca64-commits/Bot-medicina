import sqlite3
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# REEMPLAZA EL TEXTO DENTRO DE LAS COMILLAS CON TU CLAVE DE TELEGRAM:
TOKEN = "8965292549:AAFbUykh_g5ZKSdJUhqgeHG7UYF3k8s6pvo"
DB_NAME = "banco_medicina_peru.db"

# Intervalos de repetición espaciada:
# Nivel 0 (Fallo): 10 min | Nivel 1: 1 día | Nivel 2: 3 días | Nivel 3: 7 días | Nivel 4: 15 días
INTERVALOS = {
    0: timedelta(minutes=10),
    1: timedelta(days=1),
    2: timedelta(days=3),
    3: timedelta(days=7),
    4: timedelta(days=15),
}

# BANCO ESTADÍSTICO DE ALTA RENTABILIDAD (EsSalud, ENAM, Residentado Médico)
BANCO_DATOS_MAESTRO = [
    {
        "origen": "EsSalud",
        "area": "Cirugía General",
        "frecuencia": "Muy Alta",
        "pregunta": "[EsSalud - Cirugía]\nVarón de 23 años con dolor periumbilical que migra a fosa ilíaca derecha hace 14 horas, náuseas y febrícula. Al presionar la fosa ilíaca izquierda, se desencadena dolor agudo en la fosa ilíaca derecha. ¿Qué signo semiológico representa?",
        "opciones": ["Signo de Rovsing", "Signo de Blumberg", "Signo de Murphy", "Signo del Psoas"],
        "correcta": 0,
        "justificacion": "El signo de Rovsing consiste en el dolor referido en FID al comprimir la FII por desplazamiento retrógrado de gas colónico hacia el ciego inflamado."
    },
    {
        "origen": "Residentado Médico",
        "area": "Cirugía / Vía Biliar",
        "frecuencia": "Muy Alta",
        "pregunta": "[Residentado - Cirugía]\nPaciente mujer de 58 años acude por dolor en hipocondrio derecho, ictericia marcada, fiebre con escalofríos (39°C), confusión mental e hipotensión arterial refractaria. ¿Cuál es el diagnóstico sindrómico?",
        "opciones": ["Pentalogía de Reynolds (Colangitis supurativa)", "Tríada de Charcot (Colecistitis)", "Absceso hepático amebiano", "Pancreatitis aguda necrohemorrágica"],
        "correcta": 0,
        "justificacion": "La tríada de Charcot (fiebre, dolor e ictericia) más shock e hipotensión y alteración del sensorio conforma la Pentalogía de Reynolds, indicativa de colangitis aguda grave."
    },
    {
        "origen": "ENAM",
        "area": "Traumatología",
        "frecuencia": "Muy Alta",
        "pregunta": "[ENAM - Traumatología]\nAdulto joven tras colisión vehicular presenta fractura diafisaria del cúbito con luxación concomitante de la cabeza del radio en la articulación radiocubital proximal. ¿A qué lesión corresponde?",
        "opciones": ["Fractura-luxación de Monteggia", "Fractura-luxación de Galeazzi", "Fractura de Colles", "Fractura de Essex-Lopresti"],
        "correcta": 0,
        "justificacion": "Monteggia = Fractura de cúbito (tercio proximal o medio) + Luxación de la cabeza radial. Diferenciar de Galeazzi: Fractura de radio + Luxación radiocubital distal."
    },
    {
        "origen": "EsSalud",
        "area": "Traumatología",
        "frecuencia": "Alta",
        "pregunta": "[EsSalud - Traumatología]\nPaciente de 65 años cae con la muñeca en hiperextensión. Radiografía revela fractura de radio distal con desplazamiento dorsal del fragmento ('dorso de tenedor'). ¿Diagnóstico más probable?",
        "opciones": ["Fractura de Colles", "Fractura de Smith (Colles invertido)", "Fractura de Rhea-Barton", "Fractura de Monteggia"],
        "correcta": 0,
        "justificacion": "La fractura de Colles es una fractura del extremo distal del radio con desplazamiento dorsal del fragmento distal tras caída en hiperextensión."
    },
    {
        "origen": "Residentado Médico",
        "area": "Obstetricia",
        "frecuencia": "Muy Alta",
        "pregunta": "[Residentado - Obstetricia]\nGestante de 33 semanas con PA 160/110 mmHg, proteinuria +++, cefalea intensa y escotomas. ¿Cuál es el fármaco de elección para la prevención de convulsiones maternas y cuál es su antídoto?",
        "opciones": [
            "Sulfato de magnesio - Gluconato de calcio",
            "Diazepam - Flumazenil",
            "Fenitoína - Vitamina B6",
            "Labetalol - Atropina"
        ],
        "correcta": 0,
        "justificacion": "El sulfato de magnesio (esquema de Zuspan) previene y trata las convulsiones en preeclampsia severa. Su antídoto ante toxicidad respiratoria o arreflexia es el gluconato de calcio al 10%."
    },
    {
        "origen": "ENAM",
        "area": "Obstetricia",
        "frecuencia": "Muy Alta",
        "pregunta": "[ENAM - Obstetricia]\nGestante de 35 semanas acude por sangrado vaginal rojo oscuro, dolor abdominal súbito e intenso. Al examen: útero leñoso (hipertonía marcada) y sufrimiento fetal agudo. ¿Diagnóstico primordial?",
        "opciones": [
            "Desprendimiento prematuro de placenta (DPP)",
            "Placenta previa total",
            "Rotura de vasa previa",
            "Rotura de seno marginal"
        ],
        "correcta": 0,
        "justificacion": "El sangrado oscuro, dolor abdominal continuo e hipertonía uterina con compromiso fetal es patognomónico de desprendimiento prematuro de placenta (abruptio placentae)."
    },
    {
        "origen": "EsSalud",
        "area": "Neonatología",
        "frecuencia": "Muy Alta",
        "pregunta": "[EsSalud - Neonatología]\nEn reanimación neonatal, tras los pasos iniciales (calor, posición, secado y estímulo), el recién nacido persiste en apnea y con frecuencia cardíaca de 80 lpm. ¿Conducta inmediata prioritaria?",
        "opciones": [
            "Iniciar Ventilación a Presión Positiva (VPP)",
            "Iniciar compresiones torácicas",
            "Administrar adrenalina endotraqueal",
            "Aplicar oxígeno libre en flujo directo"
        ],
        "correcta": 0,
        "justificacion": "Según el programa de Reanimación Neonatal: si tras 30 segundos hay apnea, boqueo o FC < 100 lpm, el paso mandatorio es iniciar ventilación a presión positiva (VPP)."
    },
    {
        "origen": "ENAM",
        "area": "Pediatría",
        "frecuencia": "Muy Alta",
        "pregunta": "[ENAM - Pediatría]\nLactante de 9 meses presenta fiebre elevada (39.5 °C) durante 3 días sin foco aparente. Al caer la fiebre bruscamente, aparece un exantema maculopapular rosado en tronco que respeta cara. ¿Diagnóstico?",
        "opciones": [
            "Exantema súbito (Roséola infantil - HHV-6)",
            "Eritema infeccioso (Megaloeitema)",
            "Sarampión",
            "Escarlatina"
        ],
        "correcta": 0,
        "justificacion": "El exantema súbito (Virus Herpes Humano 6) se caracteriza clásicamente por la aparición del brote exantemático exactamente al descender la curva febril en lisis."
    },
    {
        "origen": "EsSalud",
        "area": "Infectología",
        "frecuencia": "Muy Alta",
        "pregunta": "[EsSalud - Infectología]\nPaciente en tratamiento por tuberculosis pulmonar sensible con esquema 2HRZE/4H3R3 presenta hiperuricemia asintomática y artralgias. ¿Cuál es el fármaco antituberculoso causante?",
        "opciones": ["Pirazinamida", "Isoniazida", "Etambutol", "Rifampicina"],
        "correcta": 0,
        "justificacion": "La pirazinamida inhibe la secreción tubular renal de ácido úrico, provocando hiperuricemia frecuente. (Etambutol da neuritis óptica, Isoniazida neuropatía por déficit de piridoxina)."
    },
    {
        "origen": "Residentado Médico",
        "area": "Nefrología / Cardiología",
        "frecuencia": "Muy Alta",
        "pregunta": "[Residentado - Medicina Interna]\nPaciente renal crónico estadio 5 llega con potasio sérico de 7.4 mEq/L. El ECG muestra ensanchamiento del QRS y pérdida de ondas P. ¿Cuál es la primera medida inmediata para estabilizar la membrana miocárdica?",
        "opciones": [
            "Gluconato de calcio al 10% EV",
            "Nebulización con Salbutamol",
            "Insulina rápida + Dextrosa al 33%",
            "Bicarbonato de sodio EV"
        ],
        "correcta": 0,
        "justificacion": "El gluconato de calcio no baja el potasio sérico, pero estabiliza la membrana del cardiomiocito en 3-5 minutos para prevenir arritmias letales y paro cardíaco."
    },
    {
        "origen": "ENAM",
        "area": "Salud Pública",
        "frecuencia": "Alta",
        "pregunta": "[ENAM - Epidemiología]\nSe desea investigar la asociación entre una enfermedad rara o de baja prevalencia y una exposición ocurrida en el pasado. ¿Cuál es el diseño de estudio analítico más costo-eficiente?",
        "opciones": [
            "Estudio de Casos y Controles",
            "Estudio de Cohortes prospectivo",
            "Ensayo clínico aleatorizado",
            "Estudio de corte transversal"
        ],
        "correcta": 0,
        "justificacion": "Para enfermedades raras o con periodos de latencia prolongados, el estudio de elección es Casos y Controles, midiendo la asociación mediante el Odds Ratio (OR)."
    }
]

# --- BASE DE DATOS ---
def inicializar_sistema():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            origen TEXT,
            area TEXT,
            frecuencia TEXT,
            pregunta TEXT,
            opciones TEXT,
            correcta INTEGER,
            justificacion TEXT,
            nivel INTEGER DEFAULT 0,
            aciertos INTEGER DEFAULT 0,
            fallos INTEGER DEFAULT 0,
            proximo_envio TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def sincronizar_usuario(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM preguntas WHERE user_id = ?", (user_id,))
    if cur.fetchone()[0] == 0:
        for item in BANCO_DATOS_MAESTRO:
            cur.execute("""
                INSERT INTO preguntas (
                    user_id, origen, area, frecuencia, pregunta, opciones, correcta, 
                    justificacion, nivel, aciertos, fallos, proximo_envio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?)
            """, (
                user_id, item["origen"], item["area"], item["frecuencia"],
                item["pregunta"], "|".join(item["opciones"]), item["correcta"],
                item["justificacion"], datetime.now()
            ))
        conn.commit()
    conn.close()

# --- COMANDOS ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sincronizar_usuario(user_id)
    mensaje = (
        "🩺 **Sistema de Repaso Médico (EsSalud / ENAM / CONAREME)**\n\n"
        "Banco cargado con 'Las Fijas' de alta recurrencia estadística.\n\n"
        "📌 **Comandos:**\n"
        "• `/repasar` - Recibir una pregunta al instante.\n"
        "• `/stats` - Dashboard de aciertos y preguntas dominadas.\n"
        "• `/modo` - Filtrar preguntas por examen.\n\n"
        "Las preguntas pendientes llegarán automáticamente según el calendario de repaso."
    )
    await update.message.reply_text(mensaje, parse_mode="Markdown")

async def cmd_repasar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sincronizar_usuario(user_id)
    await enviar_pregunta(user_id, context, forzar=True)

async def cmd_modo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    botones = [
        [InlineKeyboardButton("Todos los exámenes", callback_data="set_modo:Todos")],
        [InlineKeyboardButton("Exclusivo EsSalud", callback_data="set_modo:EsSalud")],
        [InlineKeyboardButton("Exclusivo Residentado (CONAREME)", callback_data="set_modo:Residentado Médico")],
        [InlineKeyboardButton("Exclusivo ENAM", callback_data="set_modo:ENAM")]
    ]
    teclado = InlineKeyboardMarkup(botones)
    await update.message.reply_text("🎯 **Selecciona el examen a repasar:**", reply_markup=teclado, parse_mode="Markdown")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*),
            SUM(CASE WHEN nivel >= 4 THEN 1 ELSE 0 END),
            SUM(CASE WHEN nivel BETWEEN 1 AND 3 THEN 1 ELSE 0 END),
            SUM(CASE WHEN nivel = 0 THEN 1 ELSE 0 END),
            SUM(aciertos),
            SUM(fallos)
        FROM preguntas 
        WHERE user_id = ?
    """, (user_id,))
    fila = cur.fetchone()
    conn.close()

    total_p = fila[0] or 0
    dominadas = fila[1] or 0
    en_proceso = fila[2] or 0
    por_reforzar = fila[3] or 0
    aciertos = fila[4] or 0
    fallos = fila[5] or 0
    total_intentos = aciertos + fallos

    precision = (aciertos / total_intentos * 100) if total_intentos > 0 else 0.0
    pct_dominadas = (dominadas / total_p * 100) if total_p > 0 else 0.0

    bloques = int(round(pct_dominadas / 10))
    barra = "🟩" * bloques + "⬜" * (10 - bloques)

    dashboard = (
        "📊 **Dashboard de Rendimiento Médico**\n"
        "────────────────────────\n"
        f"🎯 **Tasa de Acierto:** `{precision:.1f}%`\n"
        f"• Respuestas acertadas: `{aciertos}`\n"
        f"• Respuestas falladas: `{fallos}`\n"
        f"• Intentos totales: `{total_intentos}`\n\n"
        f"🧠 **Dominio del Banco:** `{pct_dominadas:.1f}%`\n"
        f"[{barra}]\n\n"
        f"• 🏆 Dominadas (Intervalo 15d): `{dominadas}/{total_p}`\n"
        f"• ⏳ En afianzamiento: `{en_proceso}`\n"
        f"• ⚠️ Falladas / Nivel 0: `{por_reforzar}`\n"
        "────────────────────────"
    )
    await update.message.reply_text(dashboard, parse_mode="Markdown")

# --- ENVÍO Y EVALUACIÓN ---
async def enviar_pregunta(user_id, context: ContextTypes.DEFAULT_TYPE, forzar=False):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    ahora = datetime.now()

    filtro_origen = context.user_data.get("filtro_origen") if hasattr(context, "user_data") else None

    query = "SELECT id, pregunta, opciones, origen, area FROM preguntas WHERE user_id = ?"
    params = [user_id]

    if not forzar:
        query += " AND proximo_envio <= ?"
        params.append(ahora)

    if filtro_origen and filtro_origen != "Todos":
        query += " AND origen = ?"
        params.append(filtro_origen)

    query += " ORDER BY proximo_envio ASC LIMIT 1"

    cur.execute(query, tuple(params))
    fila = cur.fetchone()

    if fila:
        p_id, texto_pregunta, str_opciones, origen, area = fila
        lista_opciones = str_opciones.split("|")

        botones = [
            [InlineKeyboardButton(op, callback_data=f"ans:{p_id}:{idx}")]
            for idx, op in enumerate(lista_opciones)
        ]
        teclado = InlineKeyboardMarkup(botones)

        # Posponer 20 min si no contesta de inmediato
        cur.execute("UPDATE preguntas SET proximo_envio = ? WHERE id = ?", (ahora + timedelta(minutes=20), p_id))
        conn.commit()
        conn.close()

        encabezado = f"🏷️ *[{origen} | {area}]*\n"
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{encabezado}\n{texto_pregunta}",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
    else:
        conn.close()
        if forzar:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 ¡Al día! No tienes preguntas pendientes para repasar ahora."
            )

async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("set_modo:"):
        modo = data.split(":")[1]
        context.user_data["filtro_origen"] = modo
        await query.edit_message_text(f"✅ Filtro establecido: **{modo}**", parse_mode="Markdown")
        return

    if data.startswith("ans:"):
        _, p_id_str, opcion_str = data.split(":")
        p_id = int(p_id_str)
        opcion_elegida = int(opcion_str)

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT correcta, justificacion, nivel FROM preguntas WHERE id = ?", (p_id,))
        fila = cur.fetchone()

        if not fila:
            await query.edit_message_text("Pregunta no disponible.")
            conn.close()
            return

        correcta, justificacion, nivel = fila

        if opcion_elegida == correcta:
            nuevo_nivel = min(nivel + 1, 4)
            delta = INTERVALOS[nuevo_nivel]
            cur.execute("""
                UPDATE preguntas 
                SET nivel = ?, aciertos = aciertos + 1, proximo_envio = ? 
                WHERE id = ?
            """, (nuevo_nivel, datetime.now() + delta, p_id))
            veredicto = f"✅ **¡CORRECTO!** (Avanza a Nivel {nuevo_nivel}/4 — Repaso en {delta})"
        else:
            nuevo_nivel = 0
            delta = INTERVALOS[0]
            cur.execute("""
                UPDATE preguntas 
                SET nivel = 0, fallos = fallos + 1, proximo_envio = ? 
                WHERE id = ?
            """, (datetime.now() + delta, p_id))
            veredicto = f"❌ **INCORRECTO** (Nivel 0 — Repaso prioritario en 10 min)"

        conn.commit()
        conn.close()

        resultado_texto = (
            f"{query.message.text}\n\n"
            f"{veredicto}\n\n"
            f"💡 **Fundamento Oficial:**\n{justificacion}"
        )
        await query.edit_message_text(resultado_texto, parse_mode="Markdown")

# --- PLANIFICADOR EN SEGUNDO PLANO ---
async def despachador_automatico(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT user_id FROM preguntas WHERE user_id IS NOT NULL")
    usuarios = [r[0] for r in cur.fetchall()]
    conn.close()

    for uid in usuarios:
        await enviar_pregunta(uid, context, forzar=False)

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    inicializar_sistema()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("repasar", cmd_repasar))
    app.add_handler(CommandHandler("modo", cmd_modo))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(manejar_callback))

    # Revisa cada 60 segundos si hay repasos pendientes
    app.job_queue.run_repeating(despachador_automatico, interval=60, first=10)

    print("=== Bot Médico Activo en la Nube ===")
    app.run_polling()
