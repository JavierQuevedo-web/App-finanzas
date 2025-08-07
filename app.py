import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os
import hashlib
import re

# --------- FUNCIONES ---------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(user, password):
    if not os.path.exists("users.csv"):
        return False
    df_users = pd.read_csv("users.csv")
    user_row = df_users[df_users["user"] == user]
    if user_row.empty:
        return False
    return user_row["password_hash"].values[0] == hash_password(password)

def register_user(user, password):
    if not os.path.exists("users.csv"):
        df_users = pd.DataFrame(columns=["user", "password_hash"])
    else:
        df_users = pd.read_csv("users.csv")
    if user in df_users["user"].values:
        return False
    new_user = pd.DataFrame({"user": [user], "password_hash": [hash_password(password)]})
    df_users = pd.concat([df_users, new_user], ignore_index=True)
    df_users.to_csv("users.csv", index=False)
    return True

def load_user_data(user):
    fn = f"data_{user}.csv"
    if not os.path.exists(fn):
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Monto", "Categoría", "Comentario"])
        df.to_csv(fn, index=False)
    else:
        df = pd.read_csv(fn)
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df

def save_user_data(user, df):
    fn = f"data_{user}.csv"
    df.to_csv(fn, index=False)

def chatbot_response(query, df):
    q = query.lower()

    # Fechas importantes
    hoy = pd.Timestamp(datetime.date.today())
    hace_7 = hoy - pd.Timedelta(days=7)
    hace_14 = hoy - pd.Timedelta(days=14)
    primer_dia_mes = hoy.replace(day=1)

    ingresos = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
    gastos = df[df["Tipo"] == "Gasto"]["Monto"].sum()
    ahorros = df[df["Tipo"] == "Ahorro"]["Monto"].sum()
    balance = ingresos - gastos - ahorros

    # Gastos últimos periodos
    gastos_7d = df[(df["Tipo"] == "Gasto") & (df["Fecha"] >= hace_7)]["Monto"].sum()
    gastos_14d = df[(df["Tipo"] == "Gasto") & (df["Fecha"] >= hace_14)]["Monto"].sum()
    gastos_ultimo_mes = df[(df["Tipo"] == "Gasto") & (df["Fecha"] >= primer_dia_mes)]["Monto"].sum()

    # Regex para entender la pregunta (puedes agregar más)
    if re.search(r"cuánto he gastado|gasto total|total gastado", q):
        return f"Tu gasto total registrado es ${gastos:,.2f}."
    if re.search(r"cuál es mi ingreso|ingresos totales|total ingresado", q):
        return f"Tu ingreso total registrado es ${ingresos:,.2f}."
    if re.search(r"cuánto he ahorrado|ahorro total|total ahorrado", q):
        return f"Tu ahorro total registrado es ${ahorros:,.2f}."
    if re.search(r"cuál es mi balance|saldo|balance actual", q):
        return f"Tu balance actual (ingresos - gastos - ahorros) es ${balance:,.2f}."
    if re.search(r"gasto últimos 7 días|gastado en los últimos 7 días|gastos últimos 7 días", q):
        return f"Has gastado ${gastos_7d:,.2f} en los últimos 7 días."
    if re.search(r"gasto últimas 2 semanas|gastado en las últimas 2 semanas|gastos últimas dos semanas", q):
        return f"Has gastado ${gastos_14d:,.2f} en las últimas dos semanas."
    if re.search(r"gasto último mes|gastado en el último mes|gastos último mes", q):
        return f"Has gastado ${gastos_ultimo_mes:,.2f} en el último mes."

    return "Lo siento, no entiendo la pregunta. Prueba con preguntas como: '¿Cuánto he gastado?', '¿Cuál es mi ingreso?', '¿Cuánto he ahorrado?', '¿Cuál es mi balance?', '¿Cuánto gasté en los últimos 7 días?'"

# --------- INICIO DE LA APP ---------

st.set_page_config(page_title="App Financiera con Chatbot Mejorado", layout="wide")

# Mantener sesión usuario
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if not st.session_state.logged_in:
    st.title("🔐 Login / Registro")

    tab1, tab2 = st.tabs(["Login", "Registro"])

    with tab1:
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if check_password(user, password):
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success(f"Bienvenido {user}")
            else:
                st.error("Usuario o contraseña incorrectos")

    with tab2:
        new_user = st.text_input("Nuevo usuario")
        new_password = st.text_input("Nueva contraseña", type="password")
        new_password2 = st.text_input("Confirmar contraseña", type="password")
        if st.button("Registrarse"):
            if new_password != new_password2:
                st.error("Las contraseñas no coinciden")
            elif len(new_password) < 4:
                st.error("La contraseña debe tener al menos 4 caracteres")
            elif register_user(new_user, new_password):
                st.success("Usuario creado, ya puedes iniciar sesión")
            else:
                st.error("El usuario ya existe")

else:
    st.sidebar.title(f"Usuario: {st.session_state.user}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.experimental_rerun()

    df = load_user_data(st.session_state.user)

    st.title(f"💸 Bienvenido, {st.session_state.user}")

    # FORMULARIO NUEVO MOVIMIENTO
    st.header("➕ Registrar nuevo movimiento")
    with st.form("form_movimiento"):
        fecha = st.date_input("Fecha", datetime.date.today())
        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Ahorro"])
        monto = st.number_input("Monto", min_value=0.0, format="%.2f")
        categorias = [
            "Alimentación", "Transporte", "Arriendo", "Salud", "Educación",
            "Entretenimiento", "Servicios básicos - Luz", "Servicios básicos - Agua",
            "Servicios básicos - Gas", "Internet", "Gastos hormiga", "Gastos Santi",
            "Salidas a comer", "Otros", "Ahorro Banco", "Ahorro Inversiones"
        ]
        categoria = st.selectbox("Categoría", categorias)
        comentario = st.text_input("Comentario")
        enviar = st.form_submit_button("Registrar")

        if enviar and monto > 0:
            nuevo = pd.DataFrame({
                "Fecha": [fecha],
                "Tipo": [tipo],
                "Monto": [monto],
                "Categoría": [categoria],
                "Comentario": [comentario]
            })
            df = pd.concat([df, nuevo], ignore_index=True)
            save_user_data(st.session_state.user, df)
            st.success("Movimiento registrado")

    # Mostrar y editar movimientos
    st.header("📋 Tus movimientos")
    edit_df = df.copy()
    edit_df["Fecha"] = edit_df["Fecha"].dt.date
    edited = st.data_editor(edit_df, use_container_width=True, num_rows="dynamic")

    if st.button("Guardar cambios"):
        edited["Fecha"] = pd.to_datetime(edited["Fecha"], errors="coerce")
        save_user_data(st.session_state.user, edited)
        st.success("Cambios guardados")
        df = edited

    # Resumen financiero
    st.header("📊 Resumen financiero")
    ingresos = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
    gastos = df[df["Tipo"] == "Gasto"]["Monto"].sum()
    ahorros = df[df["Tipo"] == "Ahorro"]["Monto"].sum()
    balance = ingresos - gastos - ahorros

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Ingresos", f"${ingresos:,.2f}")
    col2.metric("Total Gastos", f"${gastos:,.2f}")
    col3.metric("Total Ahorros", f"${ahorros:,.2f}")
    col4.metric("Balance", f"${balance:,.2f}")

    # Gráficos interactivos
    st.header("📈 Evolución Mensual")
    df["AñoMes"] = df["Fecha"].dt.to_period("M").astype(str)
    df_grouped = df.groupby(["AñoMes", "Tipo"])["Monto"].sum().reset_index()

    fig_bar = px.bar(df_grouped, x="AñoMes", y="Monto", color="Tipo", barmode="group", title="Ingresos, Gastos y Ahorros por mes")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.header("📊 Distribución de Gastos por Categoría")
    gastos_cat = df[df["Tipo"] == "Gasto"].groupby("Categoría")["Monto"].sum()
    if not gastos_cat.empty:
        fig_pie = px.pie(names=gastos_cat.index, values=gastos_cat.values, title="Gastos por Categoría")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No hay gastos registrados para mostrar.")

    st.header("📊 Distribución de Ingresos por Categoría")
    ingresos_cat = df[df["Tipo"] == "Ingreso"].groupby("Categoría")["Monto"].sum()
    if not ingresos_cat.empty:
        fig_pie_ing = px.pie(names=ingresos_cat.index, values=ingresos_cat.values, title="Ingresos por Categoría")
        st.plotly_chart(fig_pie_ing, use_container_width=True)
    else:
        st.info("No hay ingresos registrados para mostrar.")

    # Chatbot financiero
    st.header("🤖 Chatbot de Finanzas")
    pregunta = st.text_input("Hazme una pregunta sobre tus finanzas (ej: ¿Cuánto he gastado?)")

    if pregunta:
        respuesta = chatbot_response(pregunta, df)
        st.info(respuesta)
