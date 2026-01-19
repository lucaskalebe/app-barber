

import streamlit as st
import json
import sqlite3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse

# ================= CONFIGURAÇÃO DE PÁGINA =================
st.set_page_config(page_title="Barber Manager", layout="wide", page_icon="✂️")

# Estilização CSS: Botões padronizados e WhatsApp com letra preta
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
    .wa-button:hover {
        background-color: #128C7E;
        color: white !important;
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

init_db()

# ================= MÓDULOS =================

def dashboard():
    st.markdown("## 🚀 Visão Geral")
    conn = sqlite3.connect(DB_PATH)
    
    # Métricas principais
    res_cli = pd.read_sql_query("SELECT count(*) as total FROM clientes", conn)
    total_clientes = res_cli.iloc[0]['total'] if not res_cli.empty else 0
    
    df_caixa = pd.read_sql_query("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa['tipo'] == 'Entrada']['valor'].sum() if not df_caixa.empty else 0
    saidas = df_caixa[df_caixa['tipo'] == 'Saída']['valor'].sum() if not df_caixa.empty else 0
    
    hoje = str(datetime.now().date())
    res_ag = pd.read_sql_query(f"SELECT count(*) as total FROM agenda WHERE data='{hoje}' AND status='Pendente'", conn)
    agenda_hoje = res_ag.iloc[0]['total'] if not res_ag.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Clientes", total_clientes)
    c2.metric("💰 Faturamento", f"R$ {entradas:,.2f}")
    c3.metric("📉 Saldo Líquido", f"R$ {(entradas - saidas):,.2f}")
    c4.metric("📅 Pendentes Hoje", agenda_hoje)

    st.divider()
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.subheader("📅 Fluxo de Agendamentos")
        df_g = pd.read_sql_query("SELECT data, count(id) as total FROM agenda GROUP BY data ORDER BY data DESC LIMIT 7", conn)
        if not df_g.empty:
            df_g['data'] = pd.to_datetime(df_g['data']).dt.strftime('%d/%m')
            st.area_chart(df_g.set_index('data'))
        
        st.subheader("📝 Últimas Movimentações Financeiras")
        df_mov = pd.read_sql_query("SELECT descricao, valor, tipo, data FROM caixa ORDER BY id DESC LIMIT 5", conn)
        st.table(df_mov)

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
                conn.commit()
                st.rerun()

    st.subheader("Compromissos Pendentes")
    df_p = pd.read_sql_query("""
        SELECT a.id, c.nome as Cliente, c.telefone, s.nome as Servico, s.preco, a.data, a.hora 
        FROM agenda a JOIN clientes c ON a.cliente_id = c.id 
        JOIN servicos s ON a.servico_id = s.id WHERE a.status = 'Pendente'
    """, conn)

    if not df_p.empty:
        for idx, row in df_p.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1])
                d_f = datetime.strptime(row['data'], '%Y-%m-%d').strftime('%d/%m/%Y')
                col1.write(f"**{row['Cliente']}**")
                col2.write(f"{row['Servico']} (R$ {row['preco']:.2f})")
                col3.write(f"📅 {d_f} às {row['hora'][:5]}")
                
                msg = urllib.parse.quote(f"Olá {row['Cliente']}, confirmo seu horário para {row['Servico']} no dia {d_f} às {row['hora'][:5]}. Até logo!")
                link = f"https://wa.me/55{row['telefone']}?text={msg}"
                
                col4.markdown(f'<a href="{link}" target="_blank" class="wa-button">💬 WhatsApp</a>', unsafe_allow_html=True)
                
                if col4.button("✅ Finalizar", key=f"btn_{row['id']}"):
                    conn.execute("UPDATE agenda SET status = 'Concluído' WHERE id = ?", (row['id'],))
                    conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?, ?, 'Entrada', ?)",
                                 (f"Atendimento: {row['Cliente']}", row['preco'], str(datetime.now().date())))
                    conn.commit()
                    st.rerun()
                st.divider()
    else:
        st.info("Nenhum agendamento pendente.")
    conn.close()

def clientes():
    st.header("👥 Clientes")
    with st.form("f_cli"):
        n = st.text_input("Nome")
        t = st.text_input("Telefone (com DDD)")
        if st.form_submit_button("Salvar") and n:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t))
            conn.commit(); conn.close()
            st.success("Cadastrado!"); st.rerun()
    conn = sqlite3.connect(DB_PATH)
    st.dataframe(pd.read_sql_query("SELECT id, nome, telefone FROM clientes", conn), use_container_width=True)
    conn.close()

def servicos():
    st.header("✂️ Serviços")
    with st.form("f_ser"):
        n = st.text_input("Nome do Serviço")
        p = st.number_input("Preço", min_value=0.0)
        if st.form_submit_button("Salvar") and n:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n, p))
            conn.commit(); conn.close()
            st.rerun()
    conn = sqlite3.connect(DB_PATH)
    st.dataframe(pd.read_sql_query("SELECT id, nome, preco FROM servicos", conn), use_container_width=True)
    conn.close()

def caixa():
    st.header("💰 Caixa")
    with st.form("f_caixa"):
        d = st.text_input("Descrição (Ex: Aluguel, Compra de Produtos)")
        v = st.number_input("Valor", min_value=0.0)
        t = st.selectbox("Tipo", ["Entrada", "Saída"])
        if st.form_submit_button("Registrar"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", 
                         (d, v, t, str(datetime.now().date())))
            conn.commit(); conn.close()
            st.rerun()
    conn = sqlite3.connect(DB_PATH)
    st.dataframe(pd.read_sql_query("SELECT * FROM caixa ORDER BY id DESC", conn), use_container_width=True)
    conn.close()

# ================= NAVEGAÇÃO =================
def main():
    if "auth" not in st.session_state:
        st.title("✂️ Barber Manager")
        u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
        if st.button("Entrar") and u == "admin" and p == "admin": 
            st.session_state.auth = True; st.rerun()
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
