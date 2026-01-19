import streamlit as st
import sqlite3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import matplotlib.pyplot as plt

# ================= CONFIGURAÇÃO DE PÁGINA =================
st.set_page_config(page_title="Barber Manager", layout="wide", page_icon="✂️")

# ================= CSS =================
st.markdown("""
<style>
.stButton>button { width: 100%; border-radius: 5px; height: 3em; }
.wa-button { 
    background-color: #25D366; 
    color: black !important; 
    padding: 10px; 
    text-decoration: none; border-radius: 5px; font-weight: bold;
    display: block; text-align: center; margin-bottom: 10px;
}
.wa-button:hover { background-color: #128C7E; color: white !important; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "barbearia.db"
if not DB_DIR.exists(): os.makedirs(DB_DIR)

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, servico_id INTEGER, data TEXT, hora TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    conn.commit()
    conn.close()

init_db()

# ================= DASHBOARD =================
def dashboard():
    st.markdown("## 🚀 Visão Geral")
    conn = sqlite3.connect(DB_PATH)

    total_clientes = pd.read_sql("SELECT COUNT(*) total FROM clientes", conn).iloc[0,0]

    df_caixa = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa.tipo=="Entrada"]["valor"].sum() if not df_caixa.empty else 0
    saidas = df_caixa[df_caixa.tipo=="Saída"]["valor"].sum() if not df_caixa.empty else 0

    hoje = str(datetime.now().date())
    pendentes = pd.read_sql(f"SELECT COUNT(*) total FROM agenda WHERE data='{hoje}' AND status='Pendente'", conn).iloc[0,0]

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("👥 Clientes", total_clientes)
    c2.metric("💰 Faturamento", f"R$ {entradas:,.2f}")
    c3.metric("📉 Saldo Líquido", f"R$ {(entradas-saidas):,.2f}")
    c4.metric("📅 Pendentes Hoje", pendentes)

    st.divider()
    col1, col2 = st.columns([2,1])

    with col1:
        st.subheader("📅 Agendamentos (7 dias)")
        df = pd.read_sql("""
            SELECT data, COUNT(*) total 
            FROM agenda GROUP BY data ORDER BY data DESC LIMIT 7
        """, conn)
        if not df.empty:
            df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m")
            st.area_chart(df.set_index("data"))

    with col2:
        st.subheader("📊 Atendimentos por Dia da Semana")

        df_pizza = pd.read_sql("""
            SELECT data FROM agenda WHERE status='Concluído'
        """, conn)

        if not df_pizza.empty:
            df_pizza["dia"] = pd.to_datetime(df_pizza["data"]).dt.dayofweek
            mapa = {0:"Seg",1:"Ter",2:"Qua",3:"Qui",4:"Sex",5:"Sáb",6:"Dom"}
            df_pizza["dia"] = df_pizza["dia"].map(mapa)
            pizza = df_pizza["dia"].value_counts().sort_index()

            fig, ax = plt.subplots()
            ax.pie(pizza.values, labels=pizza.index, autopct="%1.0f%%", startangle=90)
            ax.axis("equal")
            st.pyplot(fig)
        else:
            st.info("Sem atendimentos concluídos.")

    conn.close()

# ================= AGENDA =================
def agenda():
    st.header("📅 Agenda")
    conn = sqlite3.connect(DB_PATH)
    clientes = pd.read_sql("SELECT id, nome, telefone FROM clientes", conn)
    servicos = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)

    with st.expander("➕ Novo Agendamento"):
        with st.form("f_agenda"):
            c_nome = st.selectbox("Cliente", clientes["nome"].tolist())
            s_nome = st.selectbox("Serviço", servicos["nome"].tolist())
            data = st.date_input("Data")
            hora = st.time_input("Hora")
            if st.form_submit_button("Confirmar"):
                c_id = clientes[clientes.nome==c_nome].id.values[0]
                s_id = servicos[servicos.nome==s_nome].id.values[0]
                conn.execute("INSERT INTO agenda VALUES (NULL,?,?,?,?, 'Pendente')",
                             (c_id,s_id,str(data),str(hora)))
                conn.commit()
                st.rerun()

    df = pd.read_sql("""
        SELECT a.id, c.nome Cliente, c.telefone, s.nome Servico, s.preco, a.data, a.hora
        FROM agenda a
        JOIN clientes c ON c.id=a.cliente_id
        JOIN servicos s ON s.id=a.servico_id
        WHERE a.status='Pendente'
    """, conn)

    for _,r in df.iterrows():
        d = datetime.strptime(r.data,"%Y-%m-%d").strftime("%d/%m/%Y")
        c1,c2,c3,c4 = st.columns([2,2,2,1])
        c1.write(r.Cliente)
        c2.write(f"{r.Servico} (R$ {r.preco:.2f})")
        c3.write(f"{d} às {r.hora[:5]}")
        msg = urllib.parse.quote(f"Olá {r.Cliente}, confirmo seu horário!")
        c4.markdown(f"<a class='wa-button' href='https://wa.me/55{r.telefone}?text={msg}'>WhatsApp</a>", unsafe_allow_html=True)

    conn.close()

# ================= OUTROS =================
def clientes():
    st.header("👥 Clientes")
    with st.form("cli"):
        n = st.text_input("Nome")
        t = st.text_input("Telefone")
        if st.form_submit_button("Salvar"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO clientes VALUES(NULL,?,?)",(n,t)).connection.commit()
            st.rerun()

def servicos():
    st.header("✂️ Serviços")
    with st.form("ser"):
        n = st.text_input("Nome")
        p = st.number_input("Preço",0.0)
        if st.form_submit_button("Salvar"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO servicos VALUES(NULL,?,?)",(n,p)).connection.commit()
            st.rerun()

def caixa():
    st.header("💰 Caixa")
    with st.form("cx"):
        d = st.text_input("Descrição")
        v = st.number_input("Valor",0.0)
        t = st.selectbox("Tipo",["Entrada","Saída"])
        if st.form_submit_button("Registrar"):
            sqlite3.connect(DB_PATH).execute(
                "INSERT INTO caixa VALUES(NULL,?,?,?,?)",
                (d,v,t,str(datetime.now().date()))
            ).connection.commit()
            st.rerun()

def relatorios():
    st.header("📊 Relatórios")
    df = pd.read_sql("SELECT * FROM caixa", sqlite3.connect(DB_PATH))
    if not df.empty:
        st.bar_chart(df.groupby("data")["valor"].sum())

# ================= MAIN =================
def main():
    if "auth" not in st.session_state:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar") and u=="admin" and p=="admin":
            st.session_state.auth=True; st.rerun()
    else:
        menu=["Dashboard","Clientes","Serviços","Agenda","Caixa","Relatórios"]
        page=st.sidebar.radio("Menu",menu)
        if page=="Dashboard": dashboard()
        if page=="Clientes": clientes()
        if page=="Serviços": servicos()
        if page=="Agenda": agenda()
        if page=="Caixa": caixa()
        if page=="Relatórios": relatorios()

main()
