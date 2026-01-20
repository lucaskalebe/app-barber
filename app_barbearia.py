

import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse
import os

# ================= 1. CONTROLE DE ACESSOS =================
CLIENTES_CONFIG = {
    "barber_nunes": {"db": "nunes.db", "nome_exibicao": "Barbearia do Nunes", "senha": "123", "ativo": True},
    "navalha_gold": {"db": "navalha.db", "nome_exibicao": "Navalha Gold", "senha": "456", "ativo": True},
    "lucas":        {"db": "lucas.db", "nome_exibicao": "Teste BarberHub", "senha": "123", "ativo": True},
    "teste":         {"db": "teste.db", "nome_exibicao": "teste Apresentação", "senha": "teste", "ativo": True}
    
}

# ================= 2. CONFIGURAÇÃO DE DIRETÓRIOS E DB =================
BASE_DIR = Path(__file__).parent
DBS_DIR = BASE_DIR / "dbs"
DBS_DIR.mkdir(exist_ok=True)

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, servico_id INTEGER, data TEXT, hora TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    conn.commit()
    conn.close()

def get_metrics(db_path):
    conn = sqlite3.connect(db_path)
    total_clis = pd.read_sql("SELECT COUNT(*) FROM clientes", conn).iloc[0,0]
    df_c = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    ent = df_c[df_c.tipo=="Entrada"]["valor"].sum() if not df_c.empty else 0
    sai = df_c[df_c.tipo=="Saída"]["valor"].sum() if not df_c.empty else 0
    hoje = str(datetime.now().date())
    query_agenda = f"SELECT COUNT(*) FROM agenda WHERE data = '{hoje}' AND status='Pendente'"
    hoje_total = pd.read_sql(query_agenda, conn).iloc[0,0]
    conn.close()
    return total_clis, ent, (ent-sai), hoje_total

# ================= 3. UI/UX E ESTILO =================
st.set_page_config(page_title="BarberHub Pro", layout="wide", page_icon="💈")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    .stApp { background-color: #0F1113; font-family: 'Plus Jakarta Sans', sans-serif; }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .metric-label { color: #8E8E93; font-size: 12px; font-weight: 600; text-transform: uppercase; }
    .metric-value { color: #FFFFFF; font-size: 28px; font-weight: 700; }
    .wa-btn {
        background-color: #25D366; color: white !important; padding: 10px; 
        border-radius: 10px; text-align: center; font-weight: bold; 
        text-decoration: none; display: block; margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

def style_metric_card(label, value, accent_color):
    st.markdown(f"""
        <div class="metric-card">
            <div style="width: 30px; height: 3px; background: {accent_color}; border-radius: 2px; margin-bottom: 10px;"></div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def format_br_currency(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ================= 4. APP PRINCIPAL =================
def main():
    if "auth" not in st.session_state:
        st.markdown("<br><br><div style='text-align:center;'><h1>💈 BarberHub</h1></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            u = st.text_input("ID do Estabelecimento", key="login_u")
            p = st.text_input("Senha", type="password", key="login_p")
            if st.button("Acessar Painel", key="login_btn"):
                if u in CLIENTES_CONFIG and CLIENTES_CONFIG[u]["senha"] == p:
                    st.session_state.auth = True
                    st.session_state.cliente_id = u
                    st.session_state.db_path = DBS_DIR / CLIENTES_CONFIG[u]['db']
                    init_db(st.session_state.db_path)
                    st.rerun()
                else: st.error("ID ou senha incorretos.")
    else:
        db_path = st.session_state.db_path
        info = CLIENTES_CONFIG[st.session_state.cliente_id]

        c_h1, c_h2 = st.columns([4, 1])
        c_h1.title(f"💈 {info['nome_exibicao']}")
        if c_h2.button("Sair", key="logout_btn"):
            st.session_state.clear()
            st.rerun()

        # MÉTRICAS
        clis, fat, saldo, agenda_hoje = get_metrics(db_path)
        m1, m2, m3, m4 = st.columns(4)
        with m1: style_metric_card("Clientes Ativos", clis, "#6366F1")
        with m2: style_metric_card("Faturamento Total", format_br_currency(fat), "#10B981")
        with m3: style_metric_card("Saldo em Caixa", format_br_currency(saldo), "#F59E0B")
        with m4: style_metric_card("Agenda Hoje", agenda_hoje, "#A855F7")

        st.markdown("---")

        col_oper, col_lista = st.columns([1.2, 2])
        conn = sqlite3.connect(db_path)

        with col_oper:
            st.subheader("⚡ Cadastro & Agendamento")
            t1, t2, t3 = st.tabs(["Agendar", "Cliente", "Serviço"])
            with t1:
                clis_df = pd.read_sql("SELECT id, nome FROM clientes", conn)
                svs_df = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)
                with st.form("ag_form"):
                    c_sel = st.selectbox("Cliente", clis_df["nome"].tolist()) if not clis_df.empty else None
                    s_sel = st.selectbox("Serviço", svs_df["nome"].tolist()) if not svs_df.empty else None
                    d_in = st.date_input("Data", format="DD/MM/YYYY")
                    h_in = st.time_input("Hora")
                    if st.form_submit_button("Confirmar Agendamento"):
                        if c_sel and s_sel:
                            c_id = clis_df[clis_df.nome == c_sel].id.values[0]
                            s_id = svs_df[svs_df.nome == s_sel].id.values[0]
                            conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?, 'Pendente')", (int(c_id), int(s_id), str(d_in), str(h_in)))
                            conn.commit(); st.rerun()
            with t2:
                with st.form("f_cli"):
                    n = st.text_input("Nome"); t = st.text_input("Whats (DDD+Número)")
                    if st.form_submit_button("Salvar Cliente"):
                        conn.execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t))
                        conn.commit(); st.rerun()
            with t3:
                with st.form("f_ser"):
                    ns = st.text_input("Serviço"); ps = st.number_input("Preço R$", min_value=0.0)
                    if st.form_submit_button("Salvar Serviço"):
                        conn.execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (ns, ps))
                        conn.commit(); st.rerun()

        with col_lista:
            st.subheader("📋 Lista de Espera")
            df_agenda = pd.read_sql("SELECT a.id, c.nome, c.telefone, s.nome as serv, s.preco, a.data, a.hora FROM agenda a JOIN clientes c ON c.id=a.cliente_id JOIN servicos s ON s.id=a.servico_id WHERE a.status='Pendente' ORDER BY a.data ASC, a.hora ASC", conn)
            if df_agenda.empty: st.info("Sem agendamentos.")
            for _, r in df_agenda.iterrows():
                data_br = datetime.strptime(r.data, '%Y-%m-%d').strftime('%d/%m/%Y')
                with st.expander(f"📌 {data_br} - {r.hora[:5]} | {r.nome}"):
                    num_limpo = ''.join(filter(str.isdigit, str(r.telefone)))
                    if not num_limpo.startswith('55'): num_limpo = f"55{num_limpo}"
                    msg = urllib.parse.quote(f"Olá {r.nome}, seu horário na {info['nome_exibicao']} está confirmado para {data_br} às {r.hora[:5]}! 💈")
                    st.markdown(f'<a href="https://wa.me/{num_limpo}?text={msg}" target="_blank" class="wa-btn">📱 WhatsApp</a>', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Concluir", key=f"v_{r.id}"):
                        conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r.id,))
                        conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", (f"Serviço: {r.nome}", r.preco, "Entrada", str(datetime.now().date())))
                        conn.commit(); st.rerun()
                    if c2.button("🗑️ Cancelar", key=f"x_{r.id}"):
                        conn.execute("DELETE FROM agenda WHERE id=?", (r.id,))
                        conn.commit(); st.rerun()

        # --- FINANCEIRO (AJUSTADO PARA OS ÚLTIMOS 3 LANÇAMENTOS) ---
        st.markdown("---")
        st.subheader("💰 Fluxo de Caixa")
        f1, f2 = st.columns([1.2, 2])
        with f1:
            with st.form("novo_cx"):
                desc = st.text_input("Descrição"); val = st.number_input("Valor R$", min_value=0.0); tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    conn_cx = sqlite3.connect(db_path)
                    conn_cx.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", (desc, val, tipo, str(datetime.now().date())))
                    conn_cx.commit(); conn_cx.close(); st.rerun()
        with f2:
            conn_rel = sqlite3.connect(db_path)
            df_total = pd.read_sql("SELECT data, descricao, valor, tipo FROM caixa ORDER BY id DESC", conn_rel)
            if not df_total.empty:
                df_total_display = df_total.copy()
                df_total_display['data'] = pd.to_datetime(df_total_display['data']).dt.strftime('%d/%m/%Y')
                
                # Exibe apenas os últimos 3 lançamentos
                for _, r in df_total_display.head(3).iterrows():
                    cf1, cf2, cf3 = st.columns([0.8, 2.5, 1.2])
                    cf1.write(f"**{r.data}**")
                    cf2.write(r.descricao)
                    cor = "#10B981" if r.tipo == "Entrada" else "#EF4444"
                    cf3.markdown(f"<span style='color:{cor}; font-weight:bold;'>{r.tipo}: {format_br_currency(r.valor)}</span>", unsafe_allow_html=True)
                
                st.download_button("📥 Baixar CSV Completo", df_total.to_csv(index=False).encode('utf-8-sig'), "caixa.csv", "text/csv", key="dl_csv")
            conn_rel.close()

        # --- GESTÃO DE DADOS (CONFIGURAÇÕES) ---
        with st.expander("⚙️ Gerenciar Clientes e Serviços"):
            conn_gestao = sqlite3.connect(db_path)
            g1, g2 = st.columns(2)
            with g1:
                st.write("**Clientes**")
                df_c = pd.read_sql("SELECT id, nome, telefone FROM clientes", conn_gestao)
                edit_c = st.data_editor(df_c, key="ed_c_v2")
                if st.button("Atualizar Clientes", key="up_cli"):
                    for _, row in edit_c.iterrows():
                        conn_gestao.execute("UPDATE clientes SET nome=?, telefone=? WHERE id=?", (row['nome'], row['telefone'], row['id']))
                    conn_gestao.commit(); st.rerun()
            with g2:
                st.write("**Serviços**")
                df_s = pd.read_sql("SELECT id, nome, preco FROM servicos", conn_gestao)
                edit_s = st.data_editor(df_s, key="ed_s_v2")
                if st.button("Atualizar Serviços", key="up_ser"):
                    for _, row in edit_s.iterrows():
                        conn_gestao.execute("UPDATE servicos SET nome=?, preco=? WHERE id=?", (row['nome'], row['preco'], row['id']))
                    conn_gestao.commit(); st.rerun()
            conn_gestao.close()

if __name__ == "__main__":
    main()

