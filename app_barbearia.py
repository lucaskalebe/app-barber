

import streamlit as st
import sqlite3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse

# ================= CONFIGURAÇÃO DE PÁGINA =================
st.set_page_config(page_title="Barber Manager", layout="wide", page_icon="✂️")

# Estilização CSS: Cards e Botões
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .wa-button { 
        background-color: #25D366; 
        color: black !important; 
        padding: 10px; 
        text-decoration: none; border-radius: 5px; font-weight: bold;
        display: block; text-align: center; margin-bottom: 10px;
        font-family: sans-serif;
    }
    .metric-card {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #6c63ff;
        text-align: center;
    }
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

def delete_record(table, record_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    st.rerun()

init_db()

# ================= MÓDULOS =================

def dashboard():
    st.markdown("## 🚀 Visão Geral")
    conn = sqlite3.connect(DB_PATH)
    
    # Métricas
    total_clientes = pd.read_sql_query("SELECT count(*) as total FROM clientes", conn).iloc[0]['total']
    df_caixa = pd.read_sql_query("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa['tipo'] == 'Entrada']['valor'].sum()
    saidas = df_caixa[df_caixa['tipo'] == 'Saída']['valor'].sum()
    hoje = str(datetime.now().date())
    pendentes = pd.read_sql_query(f"SELECT count(*) as total FROM agenda WHERE data='{hoje}' AND status='Pendente'", conn).iloc[0]['total']

    # Layout de Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'>👥 Clientes<br><h2>{total_clientes}</h2></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card' style='border-left-color: #25D366'>💰 Faturamento<br><h2>R$ {entradas:,.2f}</h2></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card' style='border-left-color: #ff4b4b'>📉 Saldo Líquido<br><h2>R$ {(entradas-saidas):,.2f}</h2></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card' style='border-left-color: #ffa500'>📅 Pendentes Hoje<br><h2>{pendentes}</h2></div>", unsafe_allow_html=True)

    st.divider()
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.subheader("📅 Fluxo de Agendamentos")
        df_g = pd.read_sql_query("SELECT data, count(id) as total FROM agenda GROUP BY data ORDER BY data DESC LIMIT 7", conn)
        if not df_g.empty:
            df_g['data'] = pd.to_datetime(df_g['data']).dt.strftime('%d/%m')
            st.area_chart(df_g.set_index('data'))

    with col_dir:
        st.subheader("⚙️ Ações Rápidas")
        if st.button("➕ Novo Agendamento"): st.session_state.page = "Agenda"; st.rerun()
        if st.button("👤 Cadastrar Cliente"): st.session_state.page = "Clientes"; st.rerun()
        if st.button("💸 Registrar Despesa"): st.session_state.page = "Caixa"; st.rerun()
    conn.close()

def agenda():
    st.header("📅 Agenda")
    conn = sqlite3.connect(DB_PATH)
    clientes = pd.read_sql_query("SELECT id, nome, telefone FROM clientes", conn)
    servicos = pd.read_sql_query("SELECT id, nome, preco FROM servicos", conn)

    with st.expander("➕ Novo Agendamento"):
        with st.form("f_agenda"):
            c_nome = st.selectbox("Cliente", clientes['nome'].tolist()) if not clientes.empty else None
            s_nome = st.selectbox("Serviço", servicos['nome'].tolist()) if not servicos.empty else None
            data = st.date_input("Data")
            hora = st.time_input("Hora")
            if st.form_submit_button("Confirmar") and c_nome and s_nome:
                c_id = clientes[clientes['nome'] == c_nome]['id'].values[0]
                s_id = servicos[servicos['nome'] == s_nome]['id'].values[0]
                conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?,'Pendente')",
                             (int(c_id), int(s_id), str(data), str(hora)))
                conn.commit(); st.rerun()

    st.subheader("Compromissos Pendentes")
    df_p = pd.read_sql_query("""
        SELECT a.id, c.nome as Cliente, c.telefone, s.nome as Servico, s.preco, a.data, a.hora 
        FROM agenda a JOIN clientes c ON a.cliente_id = c.id 
        JOIN servicos s ON a.servico_id = s.id WHERE a.status = 'Pendente'
    """, conn)

    if not df_p.empty:
        for idx, row in df_p.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 1, 0.5])
                d_f = datetime.strptime(row['data'], '%Y-%m-%d').strftime('%d/%m/%Y')
                col1.write(f"**{row['Cliente']}**")
                col2.write(f"{row['Servico']} (R$ {row['preco']:.2f})")
                col3.write(f"📅 {d_f} às {row['hora'][:5]}")
                
                msg = urllib.parse.quote(f"Olá {row['Cliente']}, confirmo seu horário para {row['Servico']} às {row['hora'][:5]}!")
                link = f"https://wa.me/55{row['telefone']}?text={msg}"
                col4.markdown(f'<a href="{link}" target="_blank" class="wa-button">💬 WhatsApp</a>', unsafe_allow_html=True)
                
                btn_col1, btn_col2 = col5.columns(2)
                if btn_col1.button("✅", key=f"fin_{row['id']}"):
                    conn.execute("UPDATE agenda SET status = 'Concluído' WHERE id = ?", (row['id'],))
                    conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?, ?, 'Entrada', ?)",
                                 (f"Atendimento: {row['Cliente']}", row['preco'], str(datetime.now().date())))
                    conn.commit(); st.rerun()
                if btn_col2.button("🗑️", key=f"del_ag_{row['id']}"):
                    delete_record("agenda", row['id'])
                st.divider()
    conn.close()

def clientes():
    st.header("👥 Clientes")
    with st.form("f_cli"):
        n = st.text_input("Nome"); t = st.text_input("Telefone")
        if st.form_submit_button("Salvar") and n:
            conn = sqlite3.connect(DB_PATH); conn.execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t)); conn.commit(); conn.close(); st.rerun()
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM clientes", conn)
    for idx, row in df.iterrows():
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(row['nome']); c2.write(row['telefone'])
        if c3.button("Excluir", key=f"del_cli_{row['id']}"): delete_record("clientes", row['id'])
    conn.close()

def servicos():
    st.header("✂️ Serviços")
    with st.form("f_ser"):
        n = st.text_input("Nome"); p = st.number_input("Preço", min_value=0.0)
        if st.form_submit_button("Salvar") and n:
            conn = sqlite3.connect(DB_PATH); conn.execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n, p)); conn.commit(); conn.close(); st.rerun()
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM servicos", conn)
    for idx, row in df.iterrows():
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(row['nome']); c2.write(f"R$ {row['preco']:.2f}")
        if c3.button("Excluir", key=f"del_ser_{row['id']}"): delete_record("servicos", row['id'])
    conn.close()

def caixa():
    st.header("💰 Caixa")
    with st.form("f_caixa"):
        d = st.text_input("Descrição"); v = st.number_input("Valor"); t = st.selectbox("Tipo", ["Entrada", "Saída"])
        if st.form_submit_button("Registrar"):
            conn = sqlite3.connect(DB_PATH); conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", (d, v, t, str(datetime.now().date()))); conn.commit(); conn.close(); st.rerun()
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM caixa ORDER BY id DESC", conn)
    for idx, row in df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
        c1.write(row['descricao']); c2.write(f"R$ {row['valor']:.2f}"); c3.write(row['tipo']); c4.write(row['data'])
        if c5.button("Excluir", key=f"del_cai_{row['id']}"): delete_record("caixa", row['id'])
    conn.close()

def main():
    if "auth" not in st.session_state:
        st.title("✂️ Login")
        u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
        if st.button("Entrar") and u == "admin" and p == "admin": st.session_state.auth = True; st.rerun()
    else:
        if "page" not in st.session_state: st.session_state.page = "Dashboard"
        st.sidebar.title("🪒 Barbearia Pro")
        menu = ["Dashboard", "Clientes", "Serviços", "Agenda", "Caixa"]
        choice = st.sidebar.radio("Menu", menu, index=menu.index(st.session_state.page))
        st.session_state.page = choice
        if st.sidebar.button("Sair"): del st.session_state.auth; st.rerun()

        if st.session_state.page == "Dashboard": dashboard()
        elif st.session_state.page == "Clientes": clientes()
        elif st.session_state.page == "Serviços": servicos()
        elif st.session_state.page == "Agenda": agenda()
        elif st.session_state.page == "Caixa": caixa()

if __name__ == "__main__":
    main()
