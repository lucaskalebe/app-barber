import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import hashlib

# ================= CONFIGURAÇÃO VISUAL =================
st.set_page_config(page_title="Barber Manager PRO", layout="wide", page_icon="✂️")

st.markdown("""
<style>
    .stMetric {
        background-color: #0E1117;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .wa-button { 
        background-color: #25D366; color: white !important; 
        padding: 8px; text-decoration: none; border-radius: 5px; 
        font-weight: bold; display: block; text-align: center; font-size: 14px;
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

# ================= TELAS =================

def dashboard():
    st.title("🚀 Visão Geral")
    conn = get_connection()
    df_caixa = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa.tipo=="Entrada"]["valor"].sum() if not df_caixa.empty else 0
    saidas = df_caixa[df_caixa.tipo=="Saída"]["valor"].sum() if not df_caixa.empty else 0
    total_clientes = pd.read_sql("SELECT COUNT(*) as total FROM clientes", conn).iloc[0,0]
    hoje = datetime.now().strftime("%Y-%m-%d")
    pendentes = pd.read_sql("SELECT COUNT(*) as total FROM agenda WHERE data=? AND status='Pendente'", conn, params=(hoje,)).iloc[0,0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Total Clientes", total_clientes)
    c2.metric("💰 Faturamento", f"R$ {entradas:,.2f}")
    c3.metric("📉 Saldo Líquido", f"R$ {(entradas-saidas):,.2f}")
    c4.metric("📅 Agenda Hoje", pendentes)
    conn.close()

def gerenciar_agenda():
    st.header("📅 Agenda de Atendimentos")
    conn = get_connection()
    
    clientes_df = pd.read_sql("SELECT id, nome, telefone FROM clientes", conn)
    servicos_df = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)

    with st.expander("➕ Novo Agendamento"):
        with st.form("f_agenda", clear_on_submit=True):
            c_sel = st.selectbox("Cliente", clientes_df["nome"].tolist())
            s_sel = st.selectbox("Serviço", servicos_df["nome"].tolist())
            data = st.date_input("Data")
            hora = st.time_input("Hora")
            if st.form_submit_button("Agendar"):
                c_id = clientes_df[clientes_df.nome == c_sel].id.values[0]
                s_id = servicos_df[servicos_df.nome == s_sel].id.values[0]
                conn.execute("INSERT INTO agenda (cliente_id, servico_id, usuario_id, data, hora, status) VALUES (?,?,?,?,?,?)",
                             (int(c_id), int(s_id), st.session_state.user_id, str(data), str(hora), "Pendente"))
                conn.commit()
                st.rerun()

    st.subheader("Meus Próximos Atendimentos")
    # Filtra a agenda pelo usuário logado
    query = """
        SELECT a.id, c.nome as Cliente, c.telefone, s.nome as Servico, s.preco, a.data, a.hora
        FROM agenda a JOIN clientes c ON c.id=a.cliente_id JOIN servicos s ON s.id=a.servico_id
        WHERE a.status='Pendente' AND a.usuario_id=? ORDER BY a.data, a.hora
    """
    df_agenda = pd.read_sql(query, conn, params=(st.session_state.user_id,))

    for _, r in df_agenda.iterrows():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        col1.write(f"**{r.Cliente}**")
        col2.write(f"{r.Servico} (R$ {r.preco:.2f})")
        col3.write(f"📅 {r.data} às {r.hora[:5]}")
        msg = urllib.parse.quote(f"Olá {r.Cliente}, confirmo seu horário!")
        col4.markdown(f"<a class='wa-button' href='https://wa.me/55{r.telefone}?text={msg}'>WhatsApp</a>", unsafe_allow_html=True)
    conn.close()

def gerenciar_clientes():
    st.header("👥 Clientes")
    with st.form("c_cli", clear_on_submit=True):
        n = st.text_input("Nome")
        t = st.text_input("Telefone")
        if st.form_submit_button("Salvar"):
            conn = get_connection()
            conn.execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t))
            conn.commit()
            conn.close()
            st.success("Cadastrado!")

def gerenciar_equipe():
    st.header("👥 Equipe")
    with st.form("n_barb"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        c = st.selectbox("Cargo", ["Barbeiro", "Dono"])
        if st.form_submit_button("Cadastrar"):
            conn = get_connection()
            conn.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES (?,?,?)", (u, make_hashes(p), c))
            conn.commit()
            conn.close()
            st.rerun()

# ================= MAIN =================
def main():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "cargo" not in st.session_state:
        st.session_state.cargo = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if not st.session_state.auth:
        st.markdown("<h1 style='text-align: center;'>🔐 Login</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                conn = get_connection()
                c = conn.cursor()
                c.execute('SELECT senha, cargo, id FROM usuarios WHERE usuario = ?', (u,))
                data = c.fetchone()
                conn.close()
                if data and check_hashes(p, data[0]):
                    st.session_state.auth = True
                    st.session_state.username = u
                    st.session_state.cargo = data[1]
                    st.session_state.user_id = data[2]
                    st.rerun()
                else:
                    st.error("Credenciais inválidas")
    else:
        st.sidebar.title(f"Olá, {st.session_state.username}")
        menu = ["Dashboard", "Agenda", "Clientes"]
        if st.session_state.cargo == "Dono":
            menu += ["Financeiro", "Equipe"]
            
        page = st.sidebar.radio("Navegar", menu)
        if st.sidebar.button("Sair"):
            st.session_state.auth = False
            st.rerun()

        if page == "Dashboard": dashboard()
        elif page == "Agenda": gerenciar_agenda()
        elif page == "Clientes": gerenciar_clientes()
        elif page == "Equipe": gerenciar_equipe()

if __name__ == "__main__":
    main()
