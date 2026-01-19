import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import io

# ================= 1. CONFIGURAÇÃO E BANCO (RESOLVE NAMEERROR) =================
st.set_page_config(page_title="BarberPRO Manager", layout="wide", page_icon="💈")

# Definir caminhos globalmente no topo do arquivo
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

# ================= 2. CSS PERSONALIZADO (VISUAL SUAVE) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Fundo grafite azulado suave */
    .stApp { background-color: #121417; }

    /* Cards Brancos com bordas muito arredondadas */
    .metric-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin-bottom: 15px;
        transition: transform 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-5px); }

    .metric-value { font-size: 28px; font-weight: 700; color: #2D3436; margin-top: 5px; }
    .metric-label { 
        font-size: 12px; 
        color: #636E72; 
        text-transform: uppercase; 
        letter-spacing: 1px; 
        font-weight: 600;
    }

    /* Botão WhatsApp Suave */
    .wa-button { 
        background-color: #25D366; color: white !important; padding: 8px 12px; 
        text-decoration: none; border-radius: 10px; font-weight: 600; 
        display: inline-block; font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Helper para renderizar os cards
def style_metric_card(label, value, color):
    st.markdown(f"""
        <div class="metric-card" style="border-top: 5px solid {color}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# ================= 3. FUNÇÕES DE INTERFACE =================

def dashboard():
    st.title("🚀 Painel de Controle")
    conn = sqlite3.connect(DB_PATH)
    
    # Cálculos
    total_clientes = pd.read_sql("SELECT COUNT(*) total FROM clientes", conn).iloc[0,0]
    df_caixa = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa.tipo=="Entrada"]["valor"].sum() if not df_caixa.empty else 0
    saidas = df_caixa[df_caixa.tipo=="Saída"]["valor"].sum() if not df_caixa.empty else 0
    hoje = str(datetime.now().date())
    pendentes = pd.read_sql(f"SELECT COUNT(*) total FROM agenda WHERE data='{hoje}' AND status='Pendente'", conn).iloc[0,0]

    # Render Cards com cores pastéis
    c1, c2, c3, c4 = st.columns(4)
    with c1: style_metric_card("Clientes Ativos", total_clientes, "#A2D2FF")
    with c2: style_metric_card("Faturamento Total", f"R$ {entradas:,.2f}", "#B9FBC0")
    with c3: style_metric_card("Saldo Líquido", f"R$ {(entradas-saidas):,.2f}", "#FFCFD2")
    with col4 if 'col4' in locals() else c4: style_metric_card("Pendentes Hoje", pendentes, "#FBF8CC")

    st.markdown("---")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("📈 Agendamentos")
        df_g = pd.read_sql("SELECT data, COUNT(*) total FROM agenda GROUP BY data ORDER BY data DESC LIMIT 7", conn)
        if not df_g.empty: st.line_chart(df_g.set_index("data"))
    conn.close()

def agenda():
    st.title("📅 Agenda")
    conn = sqlite3.connect(DB_PATH)
    t1, t2 = st.tabs(["Próximos Horários", "Novo Agendamento"])
    
    with t2:
        with st.form("add_agenda"):
            clis = pd.read_sql("SELECT id, nome FROM clientes", conn)
            servs = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)
            c1, c2 = st.columns(2)
            cli = c1.selectbox("Cliente", clis["nome"].tolist()) if not clis.empty else None
            ser = c2.selectbox("Serviço", servs["nome"].tolist()) if not servs.empty else None
            d = st.date_input("Data")
            h = st.time_input("Hora")
            if st.form_submit_button("Agendar"):
                c_id = clis[clis.nome == cli].id.values[0]
                s_id = servs[servs.nome == ser].id.values[0]
                conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?, 'Pendente')", (int(c_id), int(s_id), str(d), str(h)))
                conn.commit(); st.rerun()

    with t1:
        df = pd.read_sql("SELECT a.id, c.nome, c.telefone, s.nome as serv, s.preco, a.data, a.hora FROM agenda a JOIN clientes c ON c.id=a.cliente_id JOIN servicos s ON s.id=a.servico_id WHERE a.status='Pendente'", conn)
        for _, r in df.iterrows():
            col_info, col_btn = st.columns([3, 1])
            col_info.write(f"**{r.hora[:5]} - {r.nome}** ({r.serv})")
            if col_btn.button("✅", key=f"btn_{r.id}"):
                conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r.id,))
                conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", (f"Corte: {r.nome}", r.preco, "Entrada", str(datetime.now().date())))
                conn.commit(); st.rerun()
    conn.close()

def clientes():
    st.title("👥 Gestão de Clientes")
    with st.form("cad_cli"):
        n, t = st.text_input("Nome"), st.text_input("WhatsApp")
        if st.form_submit_button("Cadastrar"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t)).connection.commit()
            st.success("Cliente salvo!")

def servicos():
    st.title("✂️ Serviços")
    with st.form("cad_ser"):
        n, p = st.text_input("Nome do Serviço"), st.number_input("Preço", 0.0)
        if st.form_submit_button("Salvar"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n, p)).connection.commit()
            st.success("Serviço salvo!")

def caixa():
    st.title("💰 Caixa")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("add_caixa"):
            d, v, t = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
            if st.form_submit_button("Registrar"):
                sqlite3.connect(DB_PATH).execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", (d, v, t, str(datetime.now().date()))).connection.commit()
                st.rerun()
    with c2:
        df = pd.read_sql("SELECT * FROM caixa ORDER BY id DESC LIMIT 10", sqlite3.connect(DB_PATH))
        st.dataframe(df, use_container_width=True)

def relatorios():
    st.markdown("""
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 15px; text-align: center; border: 1px solid #e9ecef;">
            <h2 style="color: #495057; margin: 0;">PAINEL DE GESTÃO</h2>
            <p style="color: #adb5bd;">EXPORTAR DADOS DO SISTEMA</p>
        </div>
    """, unsafe_allow_html=True)
    df = pd.read_sql("SELECT * FROM caixa", sqlite3.connect(DB_PATH))
    if not df.empty:
        st.write("###")
        c1, c2, _ = st.columns([0.5, 0.5, 3])
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        c1.download_button("📄 Excel", buffer.getvalue(), "caixa.xlsx")
        c2.download_button("📕 PDF", df.to_csv().encode('utf-8'), "caixa.pdf")
        st.dataframe(df, use_container_width=True)

# ================= 4. MAIN =================

def main():
    if "auth" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: white;'>🔐 BarberPRO Admin</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Entrar", use_container_width=True):
                if u=="admin" and p=="admin":
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Erro!")
    else:
        st.sidebar.title("💈 BarberPRO")
        menu = ["Dashboard", "Agenda", "Clientes", "Serviços", "Caixa", "Relatórios"]
        page = st.sidebar.radio("Navegação", menu)
        
        if st.sidebar.button("Sair"):
            del st.session_state.auth
            st.rerun()

        if page == "Dashboard": dashboard()
        elif page == "Agenda": agenda()
        elif page == "Clientes": clientes()
        elif page == "Serviços": servicos()
        elif page == "Caixa": caixa()
        elif page == "Relatórios": relatorios()

if __name__ == "__main__":
    main()
