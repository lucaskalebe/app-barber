import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import hashlib

# ================= CONFIGURAÇÃO VISUAL =================
st.set_page_config(page_title="Barber Manager PRO", layout="wide", page_icon="✂️")

# CSS para os cards ficarem bonitos (fundo leve e bordas arredondadas)
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 10px;
    }
    .stMetric {
        background-color: #0E1117;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = Path(__file__).parent / "barbearia.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# ================= BANCO DE DADOS =================
def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS agenda 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, servico_id INTEGER, 
                 usuario_id INTEGER, data TEXT, hora TEXT, status TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, cargo TEXT)')
    
    c.execute("SELECT * FROM usuarios WHERE usuario='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES (?,?,?)", 
                  ('admin', make_hashes('admin123'), 'Dono'))
    conn.commit()
    conn.close()

init_db()

# ================= DASHBOARD COM CARDS =================
def dashboard():
    st.title("🚀 Visão Geral")
    conn = get_connection()
    
    # Busca de dados para os cards
    df_caixa = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa.tipo=="Entrada"]["valor"].sum() if not df_caixa.empty else 0
    saidas = df_caixa[df_caixa.tipo=="Saída"]["valor"].sum() if not df_caixa.empty else 0
    total_clientes = pd.read_sql("SELECT COUNT(*) as total FROM clientes", conn).iloc[0,0]
    hoje = datetime.now().strftime("%Y-%m-%d")
    pendentes = pd.read_sql("SELECT COUNT(*) as total FROM agenda WHERE data=? AND status='Pendente'", conn, params=(hoje,)).iloc[0,0]

    # Layout de Cards em Colunas
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("👥 Total Clientes", total_clientes)
    with c2:
        st.metric("💰 Faturamento", f"R$ {entradas:,.2f}")
    with c3:
        saldo = entradas - saidas
        st.metric("📉 Saldo Líquido", f"R$ {saldo:,.2f}", delta=f"R$ {saldo}", delta_color="normal")
    with c4:
        st.metric("📅 Agenda Hoje", pendentes)

    st.divider()
    
    # Gráficos em baixo
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📅 Atendimentos (Últimos 7 dias)")
        df_atend = pd.read_sql("SELECT data, COUNT(*) as qtd FROM agenda WHERE status='Concluído' GROUP BY data LIMIT 7", conn)
        if not df_atend.empty:
            st.area_chart(df_atend.set_index("data"))
        else:
            st.info("Sem atendimentos concluídos para exibir no gráfico.")

    conn.close()

# ================= GESTÃO DE EQUIPE =================
def gerenciar_equipe():
    st.header("👥 Gestão da Equipe")
    with st.expander("➕ Cadastrar Novo Barbeiro"):
        with st.form("novo_barbeiro"):
            new_user = st.text_input("Nome de Usuário")
            new_pass = st.text_input("Senha", type="password")
            cargo = st.selectbox("Cargo", ["Barbeiro", "Dono"])
            if st.form_submit_button("Salvar"):
                try:
                    conn = get_connection()
                    conn.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES (?,?,?)",
                                 (new_user, make_hashes(new_pass), cargo))
                    conn.commit()
                    st.success("Barbeiro cadastrado!")
                    st.rerun()
                except:
                    st.error("Usuário já existe.")
    
    st.subheader("Profissionais")
    df_users = pd.read_sql("SELECT usuario as Nome, cargo as Cargo FROM usuarios", get_connection())
    st.dataframe(df_users, use_container_width=True)

# ================= LOGIN E MAIN =================
def main():
    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        # Tela de Login (conforme sua imagem)
        st.markdown("<h1 style='text-align: center;'>🔐 Login</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                conn = get_connection()
                c = conn.cursor()
                c.execute('SELECT senha, cargo, id FROM usuarios WHERE usuario = ?', (u,))
                data = c.fetchone()
                if data and check_hashes(p, data[0]):
                    st.session_state.auth = True
                    st.session_state.username = u
                    st.session_state.cargo = data[1]
                    st.rerun()
                else:
                    st.error("Credenciais inválidas")
    else:
        # Menu Lateral
        st.sidebar.title(f"Olá, {st.session_state.username}")
        if st.session_state.cargo == "Dono":
            menu = ["Dashboard", "Agenda", "Clientes", "Financeiro", "Equipe"]
        else:
            menu = ["Dashboard", "Agenda", "Clientes"]
            
        page = st.sidebar.radio("Navegar", menu)
        
        if st.sidebar.button("Sair"):
            st.session_state.auth = False
            st.rerun()

        if page == "Dashboard": dashboard()
        elif page == "Equipe": gerenciar_equipe()
        # Aqui você adiciona as outras funções (Agenda, Clientes, etc.) que já tínhamos nos passos anteriores
        else:
            st.write(f"Tela de {page} em desenvolvimento...")

if __name__ == "__main__":
    main()
