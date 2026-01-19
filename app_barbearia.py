import streamlit as st
import sqlite3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import locale

# ================= CONFIGURAÇÃO PT-BR =================
locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')

# ================= CONFIGURAÇÃO DE PÁGINA =================
st.set_page_config(page_title="Barber Pro", layout="wide", page_icon="✂️")

# ================= CSS =================
st.markdown("""
<style>
.main { background-color: #0e1117; }
.wa-button {
    background-color: #25D366;
    color: #000000 !important;
    padding: 10px;
    border-radius: 8px;
    display: block;
    text-align: center;
    font-weight: bold;
}
.card {
    background: rgba(255,255,255,0.05);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ================= PATHS =================
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "barbearia.db"
DB_DIR.mkdir(exist_ok=True)

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, servico_id INTEGER, data TEXT, hora TEXT, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)")
    conn.commit()
    conn.close()

def delete_record(table, record_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    st.rerun()

init_db()

# ================= DASHBOARD =================
def dashboard():
    st.markdown("## 🚀 Painel de Gestão")
    conn = sqlite3.connect(DB_PATH)

    total_clientes = pd.read_sql("SELECT COUNT(*) total FROM clientes", conn).iloc[0]['total']
    df_caixa = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa['tipo'] == 'Entrada']['valor'].sum()
    saidas = df_caixa[df_caixa['tipo'] == 'Saída']['valor'].sum()

    hoje = str(datetime.now().date())
    pendentes = pd.read_sql(f"SELECT COUNT(*) total FROM agenda WHERE data='{hoje}' AND status='Pendente'", conn).iloc[0]['total']

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='card'><h3>Clientes</h3><h1>{total_clientes}</h1></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h3>Entradas</h3><h1>R$ {entradas:.2f}</h1></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><h3>Saldo</h3><h1>R$ {(entradas-saidas):.2f}</h1></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'><h3>Hoje</h3><h1>{pendentes}</h1></div>", unsafe_allow_html=True)

    st.divider()
    col_graf, col_atalhos = st.columns([2,1])

    with col_graf:
        st.subheader("📅 Agendamentos (7 dias)")
        df_g = pd.read_sql("""
            SELECT data, COUNT(id) total 
            FROM agenda GROUP BY data ORDER BY data DESC LIMIT 7
        """, conn)

        if not df_g.empty:
            df_g['data'] = pd.to_datetime(df_g['data']).dt.strftime('%d/%m')
            st.area_chart(df_g.set_index('data'))

        st.subheader("📊 Atendimentos por Dia da Semana")
        df_sem = pd.read_sql("SELECT data FROM agenda", conn)

        if not df_sem.empty:
            df_sem['data'] = pd.to_datetime(df_sem['data'])
            df_sem['dia'] = df_sem['data'].dt.dayofweek
            mapa = {0:"Seg",1:"Ter",2:"Qua",3:"Qui",4:"Sex",5:"Sáb",6:"Dom"}
            df_sem['dia'] = df_sem['dia'].map(mapa)
            pizza = df_sem['dia'].value_counts()

            st.pyplot(
                pizza.plot.pie(autopct='%1.0f%%', ylabel="", figsize=(4,4)).figure
            )

    with col_atalhos:
        if st.button("➕ Novo Agendamento"):
            st.session_state.page = "Agenda"
            st.rerun()

    conn.close()

# ================= AGENDA =================
def agenda():
    st.header("📅 Agenda")
    conn = sqlite3.connect(DB_PATH)

    clientes_df = pd.read_sql("SELECT * FROM clientes", conn)
    servicos_df = pd.read_sql("SELECT * FROM servicos", conn)

    with st.expander("➕ Novo Agendamento"):
        with st.form("form_agenda"):
            busca = st.text_input("Cliente (digite para buscar)", value="")
            filtrados = clientes_df[clientes_df['nome'].str.contains(busca, case=False, na=False)] if busca else clientes_df

            cliente = st.selectbox("Selecionar Cliente", filtrados['nome'].tolist()) if not filtrados.empty else None
            servico = st.selectbox("Serviço", servicos_df['nome'].tolist()) if not servicos_df.empty else None
            data = st.date_input("Data")
            hora = st.time_input("Hora")

            if st.form_submit_button("Confirmar") and cliente and servico:
                cid = clientes_df[clientes_df['nome']==cliente]['id'].values[0]
                sid = servicos_df[servicos_df['nome']==servico]['id'].values[0]
                conn.execute(
                    "INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?, 'Pendente')",
                    (cid, sid, str(data), str(hora))
                )
                conn.commit()
                st.rerun()

    st.subheader("📌 Pendentes")
    df = pd.read_sql("""
        SELECT a.id, c.nome Cliente, c.telefone, s.nome Servico, s.preco, a.data, a.hora
        FROM agenda a
        JOIN clientes c ON a.cliente_id=c.id
        JOIN servicos s ON a.servico_id=s.id
        WHERE a.status='Pendente'
    """, conn)

    for _, r in df.iterrows():
        d = datetime.strptime(r['data'], '%Y-%m-%d').strftime('%d/%m/%Y')
        col1,col2,col3,col4,col5 = st.columns([2,2,2,2,1])
        col1.write(r['Cliente'])
        col2.write(f"{r['Servico']} - R$ {r['preco']:.2f}")
        col3.write(f"{d} às {r['hora'][:5]}")

        msg = urllib.parse.quote(f"Olá {r['Cliente']}, confirmamos seu horário!")
        col4.markdown(f"<a class='wa-button' href='https://wa.me/55{r['telefone']}?text={msg}'>WhatsApp</a>", unsafe_allow_html=True)

        if col5.button("✅", key=f"ok{r['id']}"):
            conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
            conn.execute(
                "INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?, 'Entrada',?)",
                (f"Atendimento {r['Cliente']}", r['preco'], str(datetime.now().date()))
            )
            conn.commit()
            st.rerun()

    conn.close()

# ================= CLIENTES =================
def clientes():
    st.header("👥 Clientes")
    with st.form("f_cli"):
        n = st.text_input("Nome")
        t = st.text_input("Telefone")
        if st.form_submit_button("Cadastrar"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n,t))
            conn.commit()
            conn.close()
            st.rerun()

# ================= SERVIÇOS =================
def servicos():
    st.header("✂️ Serviços")
    with st.form("f_ser"):
        n = st.text_input("Serviço")
        p = st.number_input("Preço", min_value=0.0)
        if st.form_submit_button("Adicionar"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n,p))
            conn.commit()
            conn.close()
            st.rerun()

# ================= CAIXA =================
def caixa():
    st.header("💰 Caixa")
    with st.form("f_caixa"):
        d = st.text_input("Descrição")
        v = st.number_input("Valor", min_value=0.0)
        t = st.selectbox("Tipo", ["Entrada","Saída"])
        if st.form_submit_button("Lançar"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO caixa VALUES (NULL,?,?,?,?)", (d,v,t,str(datetime.now().date())))
            conn.commit()
            conn.close()
            st.rerun()

# ================= MAIN =================
def main():
    if "auth" not in st.session_state:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar") and u=="admin" and p=="admin":
            st.session_state.auth = True
            st.rerun()
    else:
        if "page" not in st.session_state:
            st.session_state.page = "Dashboard"

        menu = ["Dashboard","Clientes","Serviços","Agenda","Caixa"]
        escolha = st.sidebar.radio("Menu", menu, index=menu.index(st.session_state.page))
        st.session_state.page = escolha

        if escolha=="Dashboard": dashboard()
        if escolha=="Clientes": clientes()
        if escolha=="Serviços": servicos()
        if escolha=="Agenda": agenda()
        if escolha=="Caixa": caixa()

        if st.sidebar.button("Sair"):
            del st.session_state.auth
            st.rerun()

if __name__ == "__main__":
    main()

