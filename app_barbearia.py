

import streamlit as st
import sqlite3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import matplotlib.pyplot as plt
import io  # IMPORTANTE: Adicionado para exportação

# ================= CONFIGURAÇÃO DE PÁGINA =================
st.set_page_config(page_title="BarberPRO Manager", layout="wide", page_icon="💈")

# ================= CSS PERSONALIZADO (UI/UX) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .metric-card {
        background-color: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007BFF; margin-bottom: 10px;
    }
    .metric-value { font-size: 24px; font-weight: bold; color: #1E1E1E; }
    .metric-label { font-size: 14px; color: #6c757d; text-transform: uppercase; letter-spacing: 1px; }
    .wa-button { 
        background-color: #25D366; color: white !important; padding: 8px 15px; 
        text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block; text-align: center; font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ================= DATABASE =================
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "barbearia.db"

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

# ================= HELPERS =================
def style_metric_card(label, value, color="#007BFF"):
    st.markdown(f"""
        <div class="metric-card" style="border-left-color: {color}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# ================= DASHBOARD =================
def dashboard():
    st.title("🚀 Painel de Controle")
    conn = sqlite3.connect(DB_PATH)
    total_clientes = pd.read_sql("SELECT COUNT(*) total FROM clientes", conn).iloc[0,0]
    df_caixa = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa.tipo=="Entrada"]["valor"].sum() if not df_caixa.empty else 0
    saidas = df_caixa[df_caixa.tipo=="Saída"]["valor"].sum() if not df_caixa.empty else 0
    hoje = str(datetime.now().date())
    pendentes = pd.read_sql(f"SELECT COUNT(*) total FROM agenda WHERE data='{hoje}' AND status='Pendente'", conn).iloc[0,0]

    col1, col2, col3, col4 = st.columns(4)
    with col1: style_metric_card("Clientes Ativos", total_clientes, "#4e73df")
    with col2: style_metric_card("Faturamento Total", f"R$ {entradas:,.2f}", "#1cc88a")
    with col3: style_metric_card("Saldo Líquido", f"R$ {(entradas-saidas):,.2f}", "#36b9cc")
    with col4: style_metric_card("Pendentes Hoje", pendentes, "#f6c23e")
    conn.close()

# ================= AGENDA =================
def agenda():
    st.title("📅 Agenda de Atendimentos")
    conn = sqlite3.connect(DB_PATH)
    tab1, tab2 = st.tabs(["Próximos Horários", "Novo Agendamento"])
    
    with tab2:
        with st.form("novo_agendamento"):
            clientes = pd.read_sql("SELECT id, nome FROM clientes", conn)
            servicos = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)
            c1, c2 = st.columns(2)
            cliente_sel = c1.selectbox("Selecione o Cliente", clientes["nome"].tolist()) if not clientes.empty else c1.write("Cadastre clientes primeiro")
            servico_sel = c2.selectbox("Serviço", servicos["nome"].tolist()) if not servicos.empty else c2.write("Cadastre serviços")
            d1, d2 = st.columns(2)
            data, hora = d1.date_input("Data"), d2.time_input("Hora")
            if st.form_submit_button("Agendar Horário"):
                c_id = clientes[clientes.nome == cliente_sel].id.values[0]
                s_id = servicos[servicos.nome == servico_sel].id.values[0]
                conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?, 'Pendente')", (int(c_id), int(s_id), str(data), str(hora)))
                conn.commit()
                st.success("Agendado!"); st.rerun()

    with tab1:
        df = pd.read_sql("SELECT a.id, c.nome as Cliente, c.telefone, s.nome as Servico, s.preco, a.data, a.hora FROM agenda a JOIN clientes c ON c.id=a.cliente_id JOIN servicos s ON s.id=a.servico_id WHERE a.status='Pendente' ORDER BY a.data, a.hora", conn)
        for _, r in df.iterrows():
            with st.container():
                col_info, col_btn = st.columns([3, 1])
                col_info.markdown(f"**{r.hora[:5]} - {r.Cliente}** | {r.Servico}")
                if col_btn.button("✅", key=f"f_{r.id}"):
                    conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r.id,))
                    conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", (f"Atendimento: {r.Cliente}", r.preco, "Entrada", str(datetime.now().date())))
                    conn.commit(); st.rerun()
    conn.close()

# ================= OUTRAS FUNÇÕES =================
def clientes():
    st.title("👥 Gestão de Clientes")
    with st.form("cad_cliente"):
        n, t = st.text_input("Nome"), st.text_input("WhatsApp")
        if st.form_submit_button("Salvar"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t)).connection.commit()
            st.success("Salvo!"); st.rerun()

def servicos():
    st.title("✂️ Serviços")
    with st.form("cad_serv"):
        n, p = st.text_input("Serviço"), st.number_input("Preço", 0.0)
        if st.form_submit_button("Salvar"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n, p)).connection.commit()
            st.success("Salvo!"); st.rerun()

def caixa():
    st.title("💰 Caixa")
    with st.form("f_caixa"):
        d, v, t = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
        if st.form_submit_button("Registrar"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO caixa VALUES(NULL,?,?,?,?)",(d,v,t,str(datetime.now().date()))).connection.commit()
            st.rerun()

def relatorios():
    st.markdown("""
        <div style="background-color: #1a1a1a; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 20px; border: 1px solid #d4af37;">
            <h1 style="color: #d4af37; margin: 0; letter-spacing: 3px;">PAINEL DE GESTÃO</h1>
            <p style="color: #888; font-size: 12px;">RELATÓRIOS EXECUTIVOS</p>
        </div>
    """, unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM caixa", conn)
    conn.close()
    if not df.empty:
        c1, c2, _ = st.columns([0.5, 0.5, 3])
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        c1.download_button("📄 Excel", buffer.getvalue(), "relatorio.xlsx")
        c2.download_button("📕 PDF", df.to_csv().encode('utf-8'), "relatorio.pdf") # CSV simulando PDF para demo rápida
        st.divider()
        st.dataframe(df, use_container_width=True)

# ================= MAIN =================
def main():
    if "auth" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 BarberPRO Admin</h2>", unsafe_allow_html=True)
        u, p = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.button("Acessar"):
            if u=="admin" and p=="admin": st.session_state.auth=True; st.rerun()
    else:
        menu = ["Dashboard", "Agenda", "Clientes", "Serviços", "Caixa", "Relatórios"]
        page = st.sidebar.radio("Navegação", menu)
        if page == "Dashboard": dashboard()
        elif page == "Agenda": agenda()
        elif page == "Clientes": clientes()
        elif page == "Serviços": servicos()
        elif page == "Caixa": caixa()
        elif page == "Relatórios": relatorios()
        if st.sidebar.button("Sair"): del st.session_state.auth; st.rerun()

if __name__ == "__main__":
    main()
