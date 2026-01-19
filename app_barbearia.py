import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import urllib.parse

# 1. CONFIGURAÇÃO E BANCO 
st.set_page_config(page_title="BarberHub", layout="wide", page_icon="💈")

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
        padding: 20px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .metric-label { color: #8E8E93; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #FFFFFF; font-size: 28px; font-weight: 700; margin-top: 5px; }
    .stButton>button {
        border-radius: 10px;
        background: linear-gradient(135deg, #6366F1 0%, #4338CA 100%);
        color: white; border: none; font-weight: 600; width: 100%;
    }
    .wa-link {
        background-color: #25D366; color: white !important;
        padding: 8px 12px; border-radius: 8px; text-decoration: none;
        font-size: 12px; font-weight: bold; display: block; text-align: center;
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

def get_metrics():
    conn = sqlite3.connect(DB_PATH)
    total_clis = pd.read_sql("SELECT COUNT(*) FROM clientes", conn).iloc[0,0]
    df_c = pd.read_sql("SELECT valor, tipo FROM caixa", conn)
    ent = df_c[df_c.tipo=="Entrada"]["valor"].sum() if not df_c.empty else 0
    sai = df_c[df_c.tipo=="Saída"]["valor"].sum() if not df_c.empty else 0
    hoje = datetime.now().date()
    query_agenda = f"SELECT COUNT(*) FROM agenda WHERE data = '{hoje}' AND status='Pendente'"
    hoje_total = pd.read_sql(query_agenda, conn).iloc[0,0]
    conn.close()
    return total_clis, ent, (ent-sai), hoje_total

def main():
    if "auth" not in st.session_state:
        st.markdown("<br><br><div style='text-align:center;'><h2>💈 BarberHub</h2></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar Painel"):
                if u == "admin" and p == "admin":
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Incorreto")
    else:
        # --- HEADER ---
        c_head1, c_head2 = st.columns([4, 1])
        c_head1.title("💈 BarberHub")
        if c_head2.button("Sair"):
            del st.session_state.auth
            st.rerun()

        # --- 1. DASHBOARD ---
        clis, fat, saldo, agenda_hoje = get_metrics()
        m1, m2, m3, m4 = st.columns(4)
        with m1: style_metric_card("Clientes Ativos", clis, "#6366F1")
        with m2: style_metric_card("Faturamento Total", f"R$ {fat:,.2f}", "#10B981")
        with m3: style_metric_card("Saldo em Caixa", f"R$ {saldo:,.2f}", "#F59E0B")
        with m4: style_metric_card("Agenda Hoje", agenda_hoje, "#A855F7")

        st.markdown("---")

        # --- 2. OPERAÇÃO ---
        col_oper, col_lista = st.columns([1.2, 2])
        conn = sqlite3.connect(DB_PATH)

        with col_oper:
            st.subheader("⚡ Cadastro & Agendamento")
            tab_agenda, tab_cli, tab_serv = st.tabs(["Agendar", "Cliente", "Serviço"])
            
            with tab_agenda:
                clis_df = pd.read_sql("SELECT id, nome FROM clientes", conn)
                svs_df = pd.read_sql("SELECT id, nome, preco FROM servicos", conn)
                with st.form("form_ag"):
                    c_sel = st.selectbox("Cliente", clis_df["nome"].tolist()) if not clis_df.empty else None
                    s_sel = st.selectbox("Serviço", svs_df["nome"].tolist()) if not svs_df.empty else None
                    d_in = st.date_input("Data", format="DD/MM/YYYY")
                    h_in = st.time_input("Hora")
                    if st.form_submit_button("Confirmar"):
                        if c_sel and s_sel:
                            c_id = clis_df[clis_df.nome == c_sel].id.values[0]
                            s_id = svs_df[svs_df.nome == s_sel].id.values[0]
                            conn.execute("INSERT INTO agenda (cliente_id, servico_id, data, hora, status) VALUES (?,?,?,?, 'Pendente')", 
                                         (int(c_id), int(s_id), str(d_in), str(h_in)))
                            conn.commit()
                            st.rerun()

            with tab_cli:
                with st.form("f_cli"):
                    n = st.text_input("Nome")
                    t = st.text_input("Whats (DDD+Número)")
                    if st.form_submit_button("Salvar Cliente"):
                        if n and t:
                            conn.execute("INSERT INTO clientes (nome, telefone) VALUES (?,?)", (n, t))
                            conn.commit()
                            st.rerun()

            with tab_serv:
                with st.form("f_ser"):
                    ns = st.text_input("Serviço (Corte, Barba...)")
                    ps = st.number_input("Preço R$", min_value=0.0)
                    if st.form_submit_button("Salvar Serviço"):
                        if ns:
                            conn.execute("INSERT INTO servicos (nome, preco) VALUES (?,?)", (ns, ps))
                            conn.commit()
                            st.rerun()

        with col_lista:
            st.subheader("📋 Lista de Espera")
            df_agenda = pd.read_sql("""
                SELECT a.id, c.nome, c.telefone, s.nome as serv, s.preco, a.data, a.hora 
                FROM agenda a JOIN clientes c ON c.id=a.cliente_id 
                JOIN servicos s ON s.id=a.servico_id WHERE a.status='Pendente' 
                ORDER BY a.data ASC, a.hora ASC
            """, conn)
            
            if df_agenda.empty: st.info("Sem agendamentos.")
            else:
                for _, r in df_agenda.iterrows():
                    with st.expander(f"📌 {datetime.strptime(r.data, '%Y-%m-%d').strftime('%d/%m')} - {r.hora[:5]} | {r.nome}"):
                        c1, c2, c3 = st.columns([1, 1, 1])
                        
                        # LIMPEZA DO NÚMERO: Garante que só tenha números e o 55 na frente
                        num_limpo = ''.join(filter(str.isdigit, r.telefone))
                        if not num_limpo.startswith('55'):
                            num_limpo = f"55{num_limpo}"
                        
                        msg = urllib.parse.quote(f"Olá {r.nome}, seu horário está confirmado para hoje às {r.hora[:5]}! 💈")
                        link_wa = f"https://wa.me/{num_limpo}?text={msg}"
                        
                        # Botão visualmente melhorado que abre em nova aba
                        c1.markdown(f'''
                            <a href="{link_wa}" target="_blank" style="text-decoration: none;">
                                <div style="background-color: #25D366; color: white; padding: 8px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 14px;">
                                    📱 WhatsApp
                                </div>
                            </a>
                        ''', unsafe_allow_html=True)

                        if c2.button("✅ Concluir", key=f"f_{r.id}"):
                            conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r.id,))
                            conn.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", 
                                         (f"Serviço: {r.nome}", r.preco, "Entrada", str(datetime.now().date())))
                            conn.commit()
                            st.rerun()
                        if c3.button("🗑️ Cancelar", key=f"d_{r.id}"):
                            conn.execute("DELETE FROM agenda WHERE id=?", (r.id,))
                            conn.commit()
                            st.rerun()
        # Fecha conexão da seção 2
        conn.close()

        st.markdown("---")

        # --- 3. FINANCEIRO ---
        st.subheader("💰 Fluxo de Caixa")
        f1, f2 = st.columns([1.2, 2])
        
        with f1:
            with st.form("novo_cx"):
                desc = st.text_input("Descrição")
                val = st.number_input("Valor R$", min_value=0.0)
                tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    conn_cx = sqlite3.connect(DB_PATH)
                    conn_cx.execute("INSERT INTO caixa (descricao, valor, tipo, data) VALUES (?,?,?,?)", 
                                 (desc, val, tipo, str(datetime.now().date())))
                    conn_cx.commit()
                    conn_cx.close()
                    st.rerun()
        
        with f2:
            conn_rel = sqlite3.connect(DB_PATH)
            df_total = pd.read_sql("SELECT data, descricao, valor, tipo FROM caixa ORDER BY id DESC", conn_rel)
            st.markdown(f"**Últimos Lançamentos**")
            df_resumo = df_total.head(3)
            
            if df_resumo.empty:
                st.info("Nenhuma movimentação.")
            else:
                for _, r in df_resumo.iterrows():
                    cf1, cf2, cf3 = st.columns([0.8, 2.5, 1.2])
                    dt = datetime.strptime(r.data, '%Y-%m-%d').strftime('%d/%m')
                    cf1.write(f"**{dt}**")
                    cf2.write(r.descricao)
                    cor = "#10B981" if r.tipo == "Entrada" else "#EF4444"
                    cf3.markdown(f"<span style='color:{cor}; font-weight:bold;'>{' + ' if r.tipo=='Entrada' else ' - '} R$ {r.valor:,.2f}</span>", unsafe_allow_html=True)

                st.markdown("---")
                csv = df_total.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Relatório (CSV)", data=csv, file_name=f'caixa_{datetime.now().strftime("%d_%m")}.csv', mime='text/csv')
            conn_rel.close()

        # --- 4. GESTÃO DE DADOS ---
        st.markdown("---")
        with st.expander("⚙️ Gerenciar Clientes e Serviços"):
            conn_gestao = sqlite3.connect(DB_PATH)
            g1, g2 = st.columns(2)
            with g1:
                st.write("**Clientes**")
                df_c = pd.read_sql("SELECT id, nome, telefone FROM clientes", conn_gestao)
                edited_c = st.data_editor(df_c, hide_index=True, key="ed_c")
                if st.button("Atualizar Clientes"):
                    for _, row in edited_c.iterrows():
                        conn_gestao.execute("UPDATE clientes SET nome=?, telefone=? WHERE id=?", (row['nome'], row['telefone'], row['id']))
                    conn_gestao.commit()
                    st.success("Clientes atualizados!")
                    st.rerun()
            with g2:
                st.write("**Serviços**")
                df_s = pd.read_sql("SELECT id, nome, preco FROM servicos", conn_gestao)
                edited_s = st.data_editor(df_s, hide_index=True, key="ed_s")
                if st.button("Atualizar Serviços"):
                    for _, row in edited_s.iterrows():
                        conn_gestao.execute("UPDATE servicos SET nome=?, preco=? WHERE id=?", (row['nome'], row['preco'], row['id']))
                    conn_gestao.commit()
                    st.success("Serviços atualizados!")
                    st.rerun()
            conn_gestao.close()

if __name__ == "__main__":
    main()



