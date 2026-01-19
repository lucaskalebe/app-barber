

import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import io

# ================= 1. CONFIGURAÇÃO E BANCO =================
st.set_page_config(page_title="BarberPRO Manager", layout="wide", page_icon="💈")

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

# ================= 2. UI/UX PREMIUM (VISUAL SUAVE) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    
    .stApp { background-color: #0F1113; font-family: 'Plus Jakarta Sans', sans-serif; }

    /* Estilo dos Cards Apple-like */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        padding: 25px;
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 15px;
    }
    
    .metric-label { color: #8E8E93; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #FFFFFF; font-size: 32px; font-weight: 700; margin-top: 8px; }

    /* Botões e Inputs Customizados */
    .stButton>button {
        border-radius: 12px;
        background: linear-gradient(135deg, #6366F1 0%, #4338CA 100%);
        color: white; border: none; padding: 10px 24px; font-weight: 600;
    }
    
    .wa-link {
        background-color: #25D366; color: white !important;
        padding: 6px 14px; border-radius: 8px; text-decoration: none;
        font-size: 12px; font-weight: bold; display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

def style_metric_card(label, value, accent_color):
    st.markdown(f"""
        <div class="metric-card">
            <div style="width: 40px; height: 4px; background: {accent_color}; border-radius: 2px; margin-bottom: 15px;"></div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# ================= 3. LOGICA DE NEGOCIO =================

def dashboard():
    st.markdown("# 🚀 Gestão de Performance")
    conn = sqlite3.connect(DB_PATH)
    
    # Queries robustas
    total_clis = pd.read_sql("SELECT COUNT(*) FROM clientes", conn).iloc[0,0]
    df_c = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    ent = df_c[df_c.tipo=="Entrada"]["valor"].sum() if not df_c.empty else 0
    sai = df_c[df_c.tipo=="Saída"]["valor"].sum() if not df_c.empty else 0
    
    c1, c2, c3 = st.columns(3)
    with c1: style_metric_card("Clientes Ativos", total_clis, "#6366F1")
    with c2: style_metric_card("Faturamento (Fev)", f"R$ {ent:,.2f}", "#10B981")
    with c3: style_metric_card("Saldo em Caixa", f"R$ {(ent-sai):,.2f}", "#F59E0B")
    
    st.markdown("### 📈 Tendência Semanal")
    df_trend = pd.read_sql("SELECT data, SUM(valor) as total FROM caixa WHERE tipo='Entrada' GROUP BY data ORDER BY data DESC LIMIT 7", conn)
    if not df_trend.empty:
        st.area_chart(df_trend.set_index("data"), color="#6366F1")
    conn.close()

def agenda():
    st.markdown("# 📅 Agenda de Hoje")
    conn = sqlite3.connect(DB_PATH)
    t1, t2 = st.tabs(["📋 Lista de Espera", "➕ Novo Agendamento"])
    
    with t2:
        with st.form("new_app"):
            clis = pd.read_sql("SELECT id, nome FROM clientes", conn)
            svs = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)
            
            col_a, col_b = st.columns(2)
            c_sel = col_a.selectbox("Cliente", clis["nome"].tolist()) if not clis.empty else None
            s_sel = col_b.selectbox("Serviço", svs["nome"].tolist()) if not svs.empty else None
            
            d_input = st.date_input("Data")
            h_input = st.time_input("Horário")
            
            if st.form_submit_button("Confirmar Horário"):
                if c_sel and s_sel:
                    c_id = clis[clis.nome == c_sel].id.values[0]
                    s_id = svs[svs.nome == s_sel].id.values[0]
                    conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?, 'Pendente')", (int(c_id), int(s_id), str(d_input), str(h_input)))
                    conn.commit()
                    st.success("✅ Agendado!")
                    st.rerun()

    with t1:
        df = pd.read_sql("""
            SELECT a.id, c.nome, c.telefone, s.nome as serv, s.preco, a.hora 
            FROM agenda a JOIN clientes c ON c.id=a.cliente_id 
            JOIN servicos s ON s.id=a.servico_id WHERE a.status='Pendente'
            ORDER BY a.hora ASC
        """, conn)
        
        if df.empty:
            st.info("Nenhum cliente agendado para hoje.")
        else:
            for _, r in df.iterrows():
                with st.container():
                    col_t, col_w, col_f = st.columns([3, 1, 1])
                    col_t.markdown(f"**{r.hora[:5]}** — {r.nome} <br><small style='color:#8E8E93'>{r.serv}</small>", unsafe_allow_html=True)
                    
                    # Botão WhatsApp
                    msg = urllib.parse.quote(f"Olá {r.nome}, confirmamos seu horário às {r.hora[:5]}!")
                    col_w.markdown(f'<a href="https://wa.me/55{r.telefone}?text={msg}" class="wa-link">WhatsApp</a>', unsafe_allow_html=True)
                    
                    if col_f.button("Concluir", key=f"fin_{r.id}"):
                        conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r.id,))
                        conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", (f"Serviço: {r.nome}", r.preco, "Entrada", str(datetime.now().date())))
                        conn.commit()
                        st.rerun()
                st.markdown("---")
    conn.close()

# ... (Funções Clientes, Serviços e Caixa seguem o padrão de formulários limpos)

def clientes():
    st.markdown("# 👥 Cadastro de Clientes")
    with st.form("c_cli"):
        n = st.text_input("Nome Completo")
        t = st.text_input("WhatsApp (ex: 11999999999)")
        if st.form_submit_button("Salvar Cliente"):
            if n and t:
                sqlite3.connect(DB_PATH).execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t)).connection.commit()
                st.success("Cadastrado com sucesso!")

def servicos():
    st.markdown("# ✂️ Tabela de Serviços")
    with st.form("c_ser"):
        n = st.text_input("Nome do Serviço")
        p = st.number_input("Valor R$", min_value=0.0)
        if st.form_submit_button("Atualizar Tabela"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n, p)).connection.commit()
            st.success("Tabela atualizada!")

def relatorios():
    st.markdown("# 📊 Exportação de Dados")
    df = pd.read_sql("SELECT * FROM caixa", sqlite3.connect(DB_PATH))
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='xlsxwriter')
        st.download_button("📥 Baixar Relatório Mensal (Excel)", buffer.getvalue(), "relatorio_fev.xlsx")
    else:
        st.warning("Sem dados financeiros para exportar.")

# ================= 4. ORQUESTRAÇÃO =================

def main():
    if "auth" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("<h2 style='text-align:center; color:white;'>BarberPRO 1.0</h2>", unsafe_allow_html=True)
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Entrar no Sistema", use_container_width=True):
                if u == "admin" and p == "admin":
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Acesso Negado")
    else:
        st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2600/2600021.png", width=80)
        st.sidebar.markdown("### Navegação")
        menu = ["Dashboard", "Agenda", "Clientes", "Serviços", "Relatórios"]
        choice = st.sidebar.radio("", menu)
        
        if st.sidebar.button("Sair"):
            del st.session_state.auth
            st.rerun()

        if choice == "Dashboard": dashboard()
        elif choice == "Agenda": agenda()
        elif choice == "Clientes": clientes()
        elif choice == "Serviços": servicos()
        elif choice == "Relatórios": relatorios()

if __name__ == "__main__":
    main()
