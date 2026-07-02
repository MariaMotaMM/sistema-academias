import streamlit as st
import pandas as pd
from datetime import datetime, date
from PIL import Image
import io
import base64
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# Inicializa o estado para mensagens de sucesso (GARANTA QUE ISSO ESTÁ AQUI)
if "msg_sucesso" not in st.session_state:
    st.session_state.msg_sucesso = None

# Exibe a mensagem se ela existir, e depois limpa para não repetir ao recarregar
if st.session_state.msg_sucesso:
    st.success(st.session_state.msg_sucesso)
    st.session_state.msg_sucesso = None
# Configuração da página
st.set_page_config(page_title="Sistema de Verificação - Academias", layout="wide")

# ID da Planilha
ID_PLANILHA_GOOGLE = "1JrUGFV8cwRR7niP3y95UMg8Q5nbj9adGjrkvnDzJon4"
bairros = ['Feira X', 'Fraga Maia', 'Muchila', 'Vila Olimpia', 'Artemia', 'Sobradinho', 'Noide', 'Cidade Nova', 'Adenil', 'Presidente', 'Jardim Europa']

@st.cache_resource
def conectar_google():
    creds_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key(ID_PLANILHA_GOOGLE).sheet1

sheet = conectar_google()

def obter_data_hoje():
    return date.today().strftime("%Y-%m-%d")

def foto_para_base64(foto_file):
    img = Image.open(foto_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((300, 300))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def obter_dados_sheet():
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        df["_idx"] = df.index + 2 
    return df

# Exibe mensagem de sucesso se houver algo no estado
if st.session_state.msg_sucesso:
    st.success(st.session_state.msg_sucesso)
    st.session_state.msg_sucesso = None

# --- ESTRUTURA DAS ABAS ---
st.title("🏋️‍♂️ Verificação de Academias")
aba_registrar, aba_visualizar, aba_modificar, aba_prints, aba_dash = st.tabs([
    "📝 Registrar", "📊 Histórico", "✏️ Modificar", "🖼️ Ver Prints", "📈 Dashboard"
])

with aba_registrar:
    with st.form("form_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            acad = st.selectbox("Academia", bairros)
            erro = st.radio("Apresentou erro?", ["Não", "Sim"])
        with col2:
            desc = st.text_area("Descrição", value="Tudo OK")
            sol = st.text_area("Solução", value="Tudo OK")
        fotos = st.file_uploader("Fotos", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        if st.form_submit_button("Salvar"):
            fotos_b64 = [foto_para_base64(f) for f in fotos]
            sheet.append_row([obter_data_hoje(), acad, erro, desc, sol, "|".join(fotos_b64)])
            st.session_state.msg_sucesso = "Salvo com sucesso!"
            st.rerun()

with aba_visualizar:
    st.subheader("🔍 Filtros de Pesquisa")
    df = obter_dados_sheet()
    if not df.empty:
        c1, c2 = st.columns(2)
        filtro_acad = c1.selectbox("Filtrar por Academia:", ["Todas"] + list(df["Academia"].unique()))
        filtro_data = c2.selectbox("Filtrar por Data:", ["Todas"] + list(df["Data"].unique()))
        df_f = df.copy()
        if filtro_acad != "Todas": df_f = df_f[df_f["Academia"] == filtro_acad]
        if filtro_data != "Todas": df_f = df_f[df_f["Data"] == filtro_data]
        st.divider()
        if not df_f.empty:
            for data in sorted(df_f["Data"].unique(), reverse=True):
                st.header(f"📅 {data}")
                st.dataframe(df_f[df_f["Data"] == data].drop(columns=["Fotos", "_idx"]), use_container_width=True)
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("O histórico está vazio.")

with aba_modificar:
    st.subheader("✏️ Filtrar para Modificar")
    df = obter_dados_sheet()
    
    if not df.empty:
        # Filtros para localizar o registro
        c1, c2 = st.columns(2)
        filtro_acad = c1.selectbox("Filtrar Academia:", ["Todas"] + list(df["Academia"].unique()), key="m_acad")
        filtro_data = c2.selectbox("Filtrar Data:", ["Todas"] + list(df["Data"].unique()), key="m_data")
        
        # Aplica o filtro
        df_f = df.copy()
        if filtro_acad != "Todas": df_f = df_f[df_f["Academia"] == filtro_acad]
        if filtro_data != "Todas": df_f = df_f[df_f["Data"] == filtro_data]
        
        if not df_f.empty:
            # Seletor com ID único para garantir precisão
            opcoes = df_f.apply(lambda x: f"{x['Data']} - {x['Academia']} (ID:{x['_idx']})", axis=1)
            selecao = st.selectbox("Selecione o registro para editar/excluir:", opcoes)
            
            # Extrai o ID
            idx = int(selecao.split("(ID:")[1].replace(")", ""))
            d = df.loc[df["_idx"] == idx].iloc[0]
            
            with st.form("edit"):
                e_a = st.selectbox("Academia", bairros, index=bairros.index(d['Academia']))
                e_e = st.radio("Erro?", ["Não", "Sim"], index=0 if d['Teve Erro?']=="Não" else 1)
                e_d = st.text_area("Descrição", value=d['Descricao Erro'])
                e_s = st.text_area("Solução", value=d['Solucao'])
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("Atualizar"):
                    sheet.update(f"A{idx}:E{idx}", [[obter_data_hoje(), e_a, e_e, e_d, e_s]])
                    st.session_state.msg_sucesso = "✅ Atualizado com sucesso!"
                    st.rerun()
                    
                if col_btn2.form_submit_button("🚨 Excluir"):
                    sheet.delete_rows(idx)
                    st.session_state.msg_sucesso = "🗑️ Excluído com sucesso!"
                    st.rerun()
        else:
            st.warning("Nenhum registro encontrado com esses filtros.")
    else:
        st.info("O histórico está vazio.")

with aba_prints:
    st.subheader("🖼️ Filtros para Visualizar Prints")
    df = obter_dados_sheet()
    if not df.empty and "Fotos" in df.columns:
        df_fotos = df[df["Fotos"] != ""]
        if not df_fotos.empty:
            col1, col2 = st.columns(2)
            filtro_acad = col1.selectbox("Filtrar Academia (Prints):", ["Todas"] + list(df_fotos["Academia"].unique()), key="f_acad_prints")
            filtro_data = col2.selectbox("Filtrar Data (Prints):", ["Todas"] + list(df_fotos["Data"].unique()), key="f_data_prints")
            df_f = df_fotos.copy()
            if filtro_acad != "Todas": df_f = df_f[df_f["Academia"] == filtro_acad]
            if filtro_data != "Todas": df_f = df_f[df_f["Data"] == filtro_data]
            st.divider()
            if not df_f.empty:
                opcoes_registros = df_f["Data"] + " - " + df_f["Academia"] + " (ID:" + df_f["_idx"].astype(str) + ")"
                reg_selecionado = st.selectbox("Selecione o registro para ver as fotos:", opcoes_registros)
                idx_sel = int(reg_selecionado.split("(ID:")[1].replace(")", ""))
                fotos_str = df_f.loc[df_f["_idx"] == idx_sel, "Fotos"].values[0]
                if fotos_str:
                    for b64 in fotos_str.split("|"):
                        st.image(base64.b64decode(b64))
        else:
            st.info("Nenhum registro com fotos foi encontrado.")
    else:
        st.info("O histórico está vazio ou ainda não existem registros com fotos.")

with aba_dash:
    st.subheader("📈 Análise de Dados das Academias")
    df = obter_dados_sheet()
    if not df.empty:
        col_grafico1, col_grafico2 = st.columns(2)
        with col_grafico1:
            st.markdown("### 📊 Participação (%) por Academia")
            fig_pizza = px.pie(df, names='Academia', hole=0.4)
            st.plotly_chart(fig_pizza, use_container_width=True)
        with col_grafico2:
            st.markdown("### 🚨 Academias com Mais Erros")
            df_erros = df[df['Teve Erro?'] == 'Sim']
            if not df_erros.empty:
                contagem_erros = df_erros['Academia'].value_counts().reset_index()
                contagem_erros.columns = ['Academia', 'Total de Erros']
                fig_barras = px.bar(contagem_erros, x='Academia', y='Total de Erros', color='Total de Erros', color_continuous_scale='Reds', text_auto=True)
                st.plotly_chart(fig_barras, use_container_width=True)
            else:
                st.info("🎉 Parabéns! Nenhum erro foi registrado até o momento.")
    else:
        st.info("O sistema ainda não possui dados suficientes para gerar os gráficos.")
