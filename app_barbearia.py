import streamlit as st
import sqlite3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import matplotlib.pyplot as plt

# ================= CONFIGURAÇÃO DE PÁGINA =================
st.set_page_config(page_title="BarberPRO Manager", layout="wide", page_icon="💈")

# ================= CSS PERSONALIZADO (UI/UX) =================
st.markdown("""
<style>
    /* Importando fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Estilização dos Cards */
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #007BFF;
        margin-bottom: 10px;
    }
    .metric-value { font-size: 24px; font-weight: bold; color: #1E1E1E; }
    .metric-label { font-size: 14px; color: #6c757d; text-transform: uppercase; letter-spacing: 1px; }

    /* Botão WhatsApp */
    .wa-button { 
        background-color: #25D366; 
        color: white !important; 
        padding: 8px 15px; 
        text-decoration: none; border-radius: 8px; font-weight: 600;
        display: inline-block; text-align: center; font-size: 13px;
    }
    
    /* Status Badge */
    .status-badge {
        padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;
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
    
    # Cálculos
    total_clientes = pd.read_sql("SELECT COUNT(*) total FROM clientes", conn).iloc[0,0]
    df_caixa = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    entradas = df_caixa[df_caixa.tipo=="Entrada"]["valor"].sum() if not df_caixa.empty else 0
    saidas = df_caixa[df_caixa.tipo=="Saída"]["valor"].sum() if not df_caixa.empty else 0
    hoje = str(datetime.now().date())
    pendentes = pd.read_sql(f"SELECT COUNT(*) total FROM agenda WHERE data='{hoje}' AND status='Pendente'", conn).iloc[0,0]

    # Render Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1: style_metric_card("Clientes Ativos", total_clientes, "#4e73df")
    with col2: style_metric_card("Faturamento Total", f"R$ {entradas:,.2f}", "#1cc88a")
    with col3: style_metric_card("Saldo Líquido", f"R$ {(entradas-saidas):,.2f}", "#36b9cc")
    with col4: style_metric_card("Pendentes Hoje", pendentes, "#f6c23e")

    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("📈 Movimentação de Agendamentos")
        df_grafico = pd.read_sql("SELECT data, COUNT(*) total FROM agenda GROUP BY data ORDER BY data DESC LIMIT 10", conn)
        if not df_grafico.empty:
            st.line_chart(df_grafico.set_index("data"))
            
    with col_right:
        st.subheader("🎯 Meta Diária")
        # Exemplo de UX: Barra de progresso para metas
        progresso = min(int((entradas/5000) * 100), 100) # Meta fictícia de 5000
        st.write(f"Meta de R$ 5.000,00")
        st.progress(progresso)
        st.caption(f"{progresso}% da meta mensal atingida")

    conn.close()

# ================= AGENDA (COM FINALIZAÇÃO) =================
def agenda():
    st.title("📅 Agenda de Atendimentos")
    conn = sqlite3.connect(DB_PATH)
    
    tab1, tab2 = st.tabs(["Próximos Horários", "Novo Agendamento"])
    
    with tab2:
        with st.form("novo_agendamento"):
            clientes = pd.read_sql("SELECT id, nome FROM clientes", conn)
            servicos = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)
            
            c1, c2 = st.columns(2)
            cliente_sel = c1.selectbox("Selecione o Cliente", clientes["nome"].tolist())
            servico_sel = c2.selectbox("Serviço", servicos["nome"].tolist())
            
            d1, d2 = st.columns(2)
            data = d1.date_input("Data")
            hora = d2.time_input("Hora")
            
            if st.form_submit_button("Agendar Horário"):
                c_id = clientes[clientes.nome == cliente_sel].id.values[0]
                s_id = servicos[servicos.nome == servico_sel].id.values[0]
                conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?, 'Pendente')",
                             (int(c_id), int(s_id), str(data), str(hora)))
                conn.commit()
                st.success("Agendado com sucesso!")
                st.rerun()

    with tab1:
        df = pd.read_sql("""
            SELECT a.id, c.nome as Cliente, c.telefone, s.nome as Servico, s.preco, a.data, a.hora
            FROM agenda a
            JOIN clientes c ON c.id=a.cliente_id
            JOIN servicos s ON s.id=a.servico_id
            WHERE a.status='Pendente' ORDER BY a.data, a.hora
        """, conn)

        if df.empty:
            st.info("Não há agendamentos pendentes.")
        else:
            for _, r in df.iterrows():
                with st.container():
                    # Card de agendamento estilizado
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**{r.hora[:5]} - {r.Cliente}** | {r.Servico} (R$ {r.preco:.2f})")
                        st.caption(f"📅 {datetime.strptime(r.data, '%Y-%m-%d').strftime('%d/%m')}")
                    
                    with col_btn:
                        btn_col1, btn_col2 = st.columns(2)
                        # Link WhatsApp
                        msg = urllib.parse.quote(f"Olá {r.Cliente}, confirmamos seu horário na barbearia às {r.hora[:5]}!")
                        btn_col1.markdown(f'<a href="https://wa.me/55{r.telefone}?text={msg}" class="wa-button">Zap</a>', unsafe_allow_html=True)
                        
                        # Botão Finalizar (UX: Alimenta o financeiro automaticamente)
                        if btn_col2.button("✅", key=f"fin_{r.id}", help="Finalizar e lançar no caixa"):
                            # Atualiza status
                            conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r.id,))
                            # Lança no caixa
                            conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)",
                                         (f"Atendimento: {r.Cliente}", r.preco, "Entrada", str(datetime.now().date())))
                            conn.commit()
                            st.rerun()
                st.divider()
    conn.close()

# ================= OUTRAS FUNÇÕES (SIMPLIFICADAS PARA EXEMPLO) =================
def clientes():
    st.title("👥 Gestão de Clientes")
    with st.form("cad_cliente"):
        n = st.text_input("Nome Completo")
        t = st.text_input("WhatsApp (com DDD)")
        if st.form_submit_button("Cadastrar Cliente"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t))
            conn.commit()
            st.success("Cliente cadastrado!")

def servicos():
    st.title("✂️ Tabela de Preços")
    with st.form("cad_serv"):
        n = st.text_input("Nome do Serviço")
        p = st.number_input("Preço (R$)", min_value=0.0, step=5.0)
        if st.form_submit_button("Salvar Serviço"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n, p))
            conn.commit()
            st.success("Serviço atualizado!")

def caixa():
    st.title("💰 Movimentação Financeira")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Novo Lançamento")
        with st.form("f_caixa"):
            d = st.text_input("Descrição")
            v = st.number_input("Valor", 0.0)
            t = st.selectbox("Tipo", ["Entrada", "Saída"])
            if st.form_submit_button("Registrar"):
                sqlite3.connect(DB_PATH).execute("INSERT INTO caixa VALUES(NULL,?,?,?,?)",(d,v,t,str(datetime.now().date()))).connection.commit()
                st.rerun()
    with col2:
        st.subheader("Histórico Recente")
        df = pd.read_sql("SELECT data, descricao, valor, tipo FROM caixa ORDER BY id DESC LIMIT 10", sqlite3.connect(DB_PATH))
        st.dataframe(df, use_container_width=True)

# ================= MAIN =================
def main():
    if "auth" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 BarberPRO Admin</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                if u=="admin" and p=="admin":
                    st.session_state.auth=True
                    st.rerun()
                else: st.error("Credenciais inválidas")
    else:
        st.sidebar.markdown("### 💈 BarberPRO v1.0")
        menu = ["Dashboard", "Agenda", "Clientes", "Serviços", "Caixa"]
        page = st.sidebar.radio("Navegação", menu)
        
        if st.sidebar.button("Sair"):
            del st.session_state.auth
            st.rerun()

        if page == "Dashboard": dashboard()
        elif page == "Agenda": agenda()
        elif page == "Clientes": clientes()
        elif page == "Serviços": servicos()
        elif page == "Caixa": caixa()

if __name__ == "__main__":
    main()
