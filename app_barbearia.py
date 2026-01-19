import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import io

# 1. CONFIGURAÇÃO E BANCO 
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

# ================= 2. UI/UX PREMIUM =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    .stApp { background-color: #0F1113; font-family: 'Plus Jakarta Sans', sans-serif; }
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
    .stButton>button {
        border-radius: 12px;
        background: linear-gradient(135deg, #6366F1 0%, #4338CA 100%);
        color: white; border: none; padding: 10px 24px; font-weight: 600; width: 100%;
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

# ================= 3. FUNÇÕES DE INTERFACE =================

def dashboard():
    st.markdown("# 🚀 Painel de Gestão")
    conn = sqlite3.connect(DB_PATH)
    
    total_clis = pd.read_sql("SELECT COUNT(*) FROM clientes", conn).iloc[0,0]
    df_c = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    ent = df_c[df_c.tipo=="Entrada"]["valor"].sum() if not df_c.empty else 0
    sai = df_c[df_c.tipo=="Saída"]["valor"].sum() if not df_c.empty else 0

    import datetime
    hoje = datetime.date.today()
    inicio_semana = hoje - datetime.timedelta(days=hoje.weekday()) 
    fim_semana = inicio_semana + datetime.timedelta(days=6)
    
    query_semana = f"SELECT COUNT(*) FROM agenda WHERE data BETWEEN '{inicio_semana}' AND '{fim_semana}'"
    agendados_semana = pd.read_sql(query_semana, conn).iloc[0,0]

    c1, c2, c3, c4 = st.columns(4)
    with c1: style_metric_card("Clientes Ativos", total_clis, "#6366F1")
    with c2: style_metric_card("Faturamento Total", f"R$ {ent:,.2f}", "#10B981")
    with c3: style_metric_card("Saldo em Caixa", f"R$ {(ent-sai):,.2f}", "#F59E0B")
    with c4: style_metric_card("Agenda da Semana", agendados_semana, "#A855F7")
    
    st.markdown("### 📈 Fluxo de Entradas (Últimos 7 dias)")
    df_trend = pd.read_sql("SELECT data, SUM(valor) as total FROM caixa WHERE tipo='Entrada' GROUP BY data ORDER BY data DESC LIMIT 7", conn)
    if not df_trend.empty:
        st.area_chart(df_trend.set_index("data"), color="#6366F1")
    conn.close()

def agenda():
    st.markdown("# 📅 Agenda de Atendimentos")
    conn = sqlite3.connect(DB_PATH)
    t1, t2 = st.tabs(["📋 Lista de Espera", "➕ Novo Agendamento"])
    
    with t2:
        with st.form("new_app"):
            clis = pd.read_sql("SELECT id, nome FROM clientes", conn)
            svs = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)
            col_a, col_b = st.columns(2)
            c_sel = col_a.selectbox("Cliente", clis["nome"].tolist()) if not clis.empty else None
            s_sel = col_b.selectbox("Serviço", svs["nome"].tolist()) if not svs.empty else None
            
            col_c, col_d = st.columns(2)
            # O date_input do Streamlit já abre um calendário visual
            d_input = col_c.date_input("Data")
            h_input = col_d.time_input("Horário")
            
            if st.form_submit_button("Confirmar Horário"):
                if c_sel and s_sel:
                    c_id = clis[clis.nome == c_sel].id.values[0]
                    s_id = svs[svs.nome == s_sel].id.values[0]
                    # Salvamos no banco no formato ISO para cálculos, mas exibiremos em BR
                    conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?, 'Pendente')", 
                                 (int(c_id), int(s_id), str(d_input), str(h_input)))
                    conn.commit()
                    st.success("✅ Agendado!")
                    st.rerun()

    with t1:
        # SQL com conversão de data para o padrão Brasileiro (DD/MM/YYYY)
        query = """
            SELECT a.id, c.nome as Cliente, c.telefone, s.nome as Serviço, s.preco, 
                   a.data, a.hora as Horário 
            FROM agenda a 
            JOIN clientes c ON c.id=a.cliente_id 
            JOIN servicos s ON s.id=a.servico_id 
            WHERE a.status='Pendente' 
            ORDER BY a.data ASC, a.hora ASC
        """
        df = pd.read_sql(query, conn)
        
        if df.empty:
            st.info("Nenhum cliente agendado.")
        else:
            # --- AJUSTE PARA FORMATO BRASILEIRO ---
            # Converte a data de YYYY-MM-DD para DD/MM/YYYY
            df['Data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
            # Formata o horário para exibir apenas HH:MM
            df['Horário'] = df['Horário'].str[:5]
            
            # Exibição da Tabela Organizada
            st.dataframe(
                df[["Cliente", "Serviço", "Data", "Horário"]], 
                use_container_width=True, 
                hide_index=True
            )
            
            st.markdown("---")
            st.subheader("⚡ Ações da Fila")
            
            # Lista de cards para ações rápidas (WhatsApp e Concluir)
            for _, r in df.iterrows():
                with st.expander(f"📌 {r.Horário} - {r.Cliente}"):
                    c_zap, c_fin = st.columns(2)
                    
                    # Mensagem personalizada em Português
                    msg = urllib.parse.quote(f"Olá {r.Cliente}, confirmamos seu horário hoje ({r.Data}) às {r.Horário}. Até logo!")
                    c_zap.markdown(f'<a href="https://wa.me/55{r.telefone}?text={msg}" class="wa-link" style="text-align:center; display:block;">Chamar no Zap</a>', unsafe_allow_html=True)
                    
                    if c_fin.button(f"Finalizar {r.Cliente}", key=f"btn_{r.id}"):
                        conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r.id,))
                        conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", 
                                     (f"Corte: {r.Cliente}", r.preco, "Entrada", str(datetime.now().date())))
                        conn.commit()
                        st.rerun()
    conn.close()


def caixa():
    st.markdown("# 💰 Gestão de Caixa")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Novo Lançamento")
        with st.form("f_caixa"):
            desc = st.text_input("Descrição (Ex: Fornecedor)")
            val = st.number_input("Valor R$", min_value=0.0)
            tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
            if st.form_submit_button("Registrar no Fluxo"):
                if desc and val > 0:
                    sqlite3.connect(DB_PATH).execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", (desc, val, tipo, str(datetime.now().date()))).connection.commit()
                    st.success("Registrado!"); st.rerun()
    with c2:
        st.subheader("Últimas Movimentações")
        df = pd.read_sql("SELECT data, descricao, valor, tipo FROM caixa ORDER BY id DESC LIMIT 15", sqlite3.connect(DB_PATH))
        st.dataframe(df, use_container_width=True)

def relatorios():
    st.markdown("# 📊 Exportação de Dados")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT data, descricao, valor, tipo FROM caixa ORDER BY data DESC", conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Financeiro')
        st.download_button(
            label="📥 Baixar Planilha de Controle",
            data=buffer.getvalue(),
            file_name=f"relatorio_financeiro_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else: st.warning("Sem dados para exportar.")

# ... (restante das funções clientes, servicos e main permanecem iguais)

def clientes():
    st.markdown("# 👥 Cadastro de Clientes")
    with st.form("c_cli"):
        n, t = st.text_input("Nome Completo"), st.text_input("WhatsApp (ex: 11999999999)")
        if st.form_submit_button("Salvar Cliente"):
            if n and t:
                sqlite3.connect(DB_PATH).execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t)).connection.commit()
                st.success("Cadastrado!")

def servicos():
    st.markdown("# ✂️ Tabela de Serviços")
    with st.form("c_ser"):
        n, p = st.text_input("Nome do Serviço"), st.number_input("Valor R$", min_value=0.0)
        if st.form_submit_button("Atualizar Tabela"):
            sqlite3.connect(DB_PATH).execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (n, p)).connection.commit()
            st.success("Tabela atualizada!")

def main():
    if "auth" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("<h2 style='text-align:center; color:white;'>BarberPRO 1.0</h2>", unsafe_allow_html=True)
            u, p = st.text_input("Usuário"), st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                if u == "admin" and p == "admin": st.session_state.auth = True; st.rerun()
                else: st.error("Acesso Negado")
    else:
        st.sidebar.markdown("### 💈 Menu Principal")
        menu = ["Dashboard", "Agenda", "Clientes", "Serviços", "Caixa", "Relatórios"]
        choice = st.sidebar.radio("", menu)
        if st.sidebar.button("Sair"): del st.session_state.auth; st.rerun()
        if choice == "Dashboard": dashboard()
        elif choice == "Agenda": agenda()
        elif choice == "Clientes": clientes()
        elif choice == "Serviços": servicos()
        elif choice == "Caixa": caixa()
        elif choice == "Relatórios": relatorios()

if __name__ == "__main__":
    main()

