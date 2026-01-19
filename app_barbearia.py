import streamlit as st
import sqlite3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import matplotlib.pyplot as plt

# ================= CONFIGURAÇÃO DE PÁGINA =================
st.set_page_config(page_title="Barber Manager PRO", layout="wide", page_icon="✂️")

# CSS para customização
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 5px; }
    .wa-button { 
        background-color: #25D366; color: white !important; 
        padding: 8px; text-decoration: none; border-radius: 5px; 
        font-weight: bold; display: block; text-align: center; font-size: 14px;
    }
    .main-card {
        background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "barbearia.db"

# ================= FUNÇÕES DE BANCO DE DADOS =================
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, servico_id INTEGER, data TEXT, hora TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    conn.commit()
    conn.close()

init_db()

# ================= LOGICA DE NEGÓCIO =================
def concluir_atendimento(id_agenda, cliente, servico, valor, data):
    conn = get_connection()
    # Atualiza status
    conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (id_agenda,))
    # Lança no caixa
    desc = f"Serviço: {servico} - {cliente}"
    conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)",
                 (desc, valor, "Entrada", data))
    conn.commit()
    conn.close()
    st.success(f"Atendimento de {cliente} concluído e lançado no caixa!")
    st.rerun()

# ================= TELAS =================
def dashboard():
    st.title("🚀 Dashboard")
    conn = get_connection()
    
    # Métricas
    df_caixa = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa.tipo=="Entrada"]["valor"].sum() if not df_caixa.empty else 0
    saidas = df_caixa[df_caixa.tipo=="Saída"]["valor"].sum() if not df_caixa.empty else 0
    total_clientes = pd.read_sql("SELECT COUNT(*) FROM clientes", conn).iloc[0,0]
    hoje = datetime.now().strftime("%Y-%m-%d")
    pendentes = pd.read_sql("SELECT COUNT(*) FROM agenda WHERE data=? AND status='Pendente'", conn, params=(hoje,)).iloc[0,0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Total Clientes", total_clientes)
    c2.metric("💰 Faturamento", f"R$ {entradas:,.2f}")
    c3.metric("📉 Saldo Líquido", f"R$ {(entradas-saidas):,.2f}", delta_color="normal")
    c4.metric("📅 Agenda Hoje", pendentes)

    st.divider()
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📅 Movimentação nos últimos 7 dias")
        df_grafico = pd.read_sql("""
            SELECT data, COUNT(*) as atendimentos FROM agenda 
            WHERE status='Concluído' GROUP BY data ORDER BY data DESC LIMIT 7
        """, conn)
        if not df_grafico.empty:
            st.line_chart(df_grafico.set_index("data"))
        else:
            st.info("Aguardando dados de atendimentos concluídos.")

    with col2:
        st.subheader("📊 Mix de Serviços")
        df_servicos = pd.read_sql("""
            SELECT s.nome, COUNT(a.id) as qtd 
            FROM agenda a JOIN servicos s ON a.servico_id = s.id 
            GROUP BY s.nome
        """, conn)
        if not df_servicos.empty:
            fig, ax = plt.subplots()
            ax.pie(df_servicos['qtd'], labels=df_servicos['nome'], autopct='%1.1f%%')
            st.pyplot(fig)
    conn.close()

def agenda():
    st.header("📅 Agenda de Atendimentos")
    conn = get_connection()
    
    clientes_df = pd.read_sql("SELECT id, nome, telefone FROM clientes", conn)
    servicos_df = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)

    with st.expander("➕ Novo Agendamento"):
        if clientes_df.empty or servicos_df.empty:
            st.warning("Cadastre clientes e serviços antes de agendar.")
        else:
            with st.form("f_agenda", clear_on_submit=True):
                c_selecionado = st.selectbox("Cliente", clientes_df["nome"].tolist())
                s_selecionado = st.selectbox("Serviço", servicos_df["nome"].tolist())
                data = st.date_input("Data")
                hora = st.time_input("Hora")
                
                if st.form_submit_button("Agendar"):
                    c_id = clientes_df[clientes_df.nome == c_selecionado].id.values[0]
                    s_id = servicos_df[servicos_df.nome == s_selecionado].id.values[0]
                    conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?,?)",
                                 (int(c_id), int(s_id), str(data), str(hora), "Pendente"))
                    conn.commit()
                    st.rerun()

    st.subheader("Próximos Clientes")
    df_agenda = pd.read_sql("""
        SELECT a.id, c.nome as Cliente, c.telefone, s.nome as Servico, s.preco, a.data, a.hora
        FROM agenda a
        JOIN clientes c ON c.id=a.cliente_id
        JOIN servicos s ON s.id=a.servico_id
        WHERE a.status='Pendente' ORDER BY a.data, a.hora
    """, conn)

    for _, r in df_agenda.iterrows():
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
            data_formatada = datetime.strptime(r.data, "%Y-%m-%d").strftime("%d/%m")
            
            col1.write(f"**{r.Cliente}**")
            col2.write(f"{r.Servico} (R$ {r.preco:.2f})")
            col3.write(f"📅 {data_formatada} às {r.hora[:5]}")
            
            # Botão WhatsApp
            msg = urllib.parse.quote(f"Olá {r.Cliente}, confirmo seu horário na barbearia no dia {data_formatada} às {r.hora[:5]}!")
            col4.markdown(f"<a class='wa-button' href='https://wa.me/55{r.telefone}?text={msg}'>WhatsApp</a>", unsafe_allow_html=True)
            
            # Botão Concluir
            if col5.button("✅", key=f"btn_{r.id}", help="Finalizar e lançar no caixa"):
                concluir_atendimento(r.id, r.Cliente, r.Servico, r.preco, r.data)
    conn.close()

def gerenciar_clientes():
    st.header("👥 Gestão de Clientes")
    with st.form("cad_cli", clear_on_submit=True):
        n = st.text_input("Nome Completo")
        t = st.text_input("Telefone (DDD + Número)")
        if st.form_submit_button("Cadastrar Cliente"):
            if n and t:
                conn = get_connection()
                conn.execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t))
                conn.commit()
                conn.close()
                st.success("Cliente cadastrado!")
                st.rerun()

    df = pd.read_sql("SELECT nome, telefone FROM clientes", get_connection())
    st.table(df)

def gerenciar_servicos():
    st.header("✂️ Tabela de Preços")
    with st.form("cad_ser", clear_on_submit=True):
        n = st.text_input("Nome do Serviço")
        p = st.number_input("Preço (R$)", min_value=0.0, step=5.0)
        if st.form_submit_button("Salvar Serviço"):
            conn = get_connection()
            conn.execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n, p))
            conn.commit()
            conn.close()
            st.rerun()
    
    df = pd.read_sql("SELECT nome, preco FROM servicos", get_connection())
    st.dataframe(df, use_container_width=True)

def financeiro():
    st.header("💰 Controle de Caixa")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        with st.form("cad_caixa", clear_on_submit=True):
            st.subheader("Novo Lançamento Manual")
            d = st.text_input("Descrição")
            v = st.number_input("Valor", min_value=0.0)
            t = st.selectbox("Tipo", ["Saída", "Entrada"])
            if st.form_submit_button("Registrar"):
                conn = get_connection()
                conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)",
                             (d, v, t, str(datetime.now().date())))
                conn.commit()
                conn.close()
                st.rerun()

    with c2:
        st.subheader("Histórico Recente")
        df = pd.read_sql("SELECT data, descricao, valor, tipo FROM caixa ORDER BY id DESC", get_connection())
        st.dataframe(df, use_container_width=True)

# ================= MAIN =================
def main():
    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            st.title("🔐 Login")
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                if u == "admin" and p == "123": # Altere aqui
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Credenciais inválidas")
    else:
        st.sidebar.title("Barber Manager")
        menu = ["Dashboard", "Agenda", "Clientes", "Serviços", "Financeiro"]
        page = st.sidebar.radio("Navegação", menu)
        
        if st.sidebar.button("Sair"):
            st.session_state.auth = False
            st.rerun()

        if page == "Dashboard": dashboard()
        elif page == "Agenda": agenda()
        elif page == "Clientes": gerenciar_clientes()
        elif page == "Serviços": gerenciar_servicos()
        elif page == "Financeiro": financeiro()

if __name__ == "__main__":
    main()
